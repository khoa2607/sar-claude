"""Read-only CPHD inspector (milestone M1).

Reads a CPHD file with SARkit, never writes to it, and returns a JSON-serializable
report in which every metadata value carries a provenance category
(measured / derived / assumed / unavailable). No image formation happens here.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import sarkit.cphd as sc
from sarkit.verification import CphdConsistency

from sarsil.provenance import Param, assumed, derived, measured, unavailable
from . import aperture as ap
from .chunking import DEFAULT_CHUNK_BUDGET_BYTES, plan_chunks, select_vectors
from .errors import CphdError, MalformedFileError, UnsupportedFormatError

SUPPORTED_VERSIONS = ("1.0.1", "1.1.0")
SCHEMA = "sarsil.cphd_inspection/1"
# During the optional signal scan, working memory is about this many times the raw chunk size.
SCAN_WORKING_SET_FACTOR = 5

GEOMETRY_DEFINITION = (
    "Positions are PVP values in the CPHD ECF frame (WGS 84, meters). LOS_i = unit(platform_i - SRPPos_i). "
    "Bistatic bisector LOS = unit(LOS_tx + LOS_rcv). Angular span is the angle between LOS vectors: "
    "first_last_deg (first vs last selected vector), max_from_first_deg, cumulative_deg (sum over consecutive vectors)."
)
INTERPRETATION_NOTE = (
    "Duration and angular span describe collection geometry. They are not resolution, pixel spacing or scene "
    "extent, and vector count alone does not determine azimuth resolution."
)
UNAVAILABLE_BY_DESIGN = {
    "transmitted_waveform_samples": "CPHD stores phase history (FX or TOA domain); original TX waveform samples are not in the file. Metadata describes the waveform but does not reconstruct it.",
    "raw_adc_samples": "FX-domain samples are not time-domain ADC samples.",
    "image_resolution": "Not computed in M1; depends on processing and geometry.",
    "pixel_spacing": "Not computed in M1; set by the future image-formation grid.",
}


@dataclass
class InspectOptions:
    scan_signal: bool = False
    run_consistency: bool = True
    thorough: bool = False
    compute_hash: bool = False
    chunk_budget_bytes: int = DEFAULT_CHUNK_BUDGET_BYTES
    subaperture: tuple[int, int] | None = None
    nonuniform_rtol: float = ap.NONUNIFORM_RTOL   # flag when (dt_max - dt_min)/dt_median exceeds this
    measure_performance: bool = False             # adds a non-deterministic "performance" section


# ---------------------------------------------------------------- XML helpers
def _q(path: str) -> str:
    return "/".join("{*}" + s for s in path.split("/"))


def _text(node, path: str) -> str | None:
    e = node.find(_q(path))
    return None if e is None or e.text is None else e.text.strip()


def _param(node, path: str, conv=str, unit: str | None = None, src: str | None = None) -> Param:
    s = src or f"XML:{path}"
    t = _text(node, path)
    if t is None or t == "":
        return unavailable(s, "element absent or empty")
    try:
        return measured(conv(t), unit, s)
    except ValueError:
        return unavailable(s, f"could not parse {t!r}")


def _bool(t: str) -> bool:
    return t.strip().lower() in ("true", "1")


def _d(params: dict[str, Param]) -> dict:
    return {k: v.to_dict() for k, v in params.items()}


def _tag(d: dict, source: str, provenance: str = "derived") -> dict:
    return {**d, "provenance": provenance, "source": source}


# ---------------------------------------------------------------- file checks
def _precheck(path: Path) -> tuple[str, dict[str, int], int]:
    if not path.exists():
        raise MalformedFileError(f"file does not exist: {path}")
    if not path.is_file():
        raise MalformedFileError(f"not a regular file: {path}")
    size = path.stat().st_size
    if size == 0:
        raise MalformedFileError(f"file is empty: {path}")
    with open(path, "rb") as f:
        head = f.read(16)
    if not head.startswith(b"CPHD/"):
        raise MalformedFileError(f"not a CPHD file (missing 'CPHD/' signature): {path.name}")
    version = head.split(b"\n", 1)[0][5:].decode("ascii", "replace").strip()
    if version not in SUPPORTED_VERSIONS:
        raise UnsupportedFormatError(
            f"CPHD version {version!r} is not supported by SARkit {importlib.metadata.version('sarkit')} "
            f"(supported: {', '.join(SUPPORTED_VERSIONS)}). Legacy 0.3 files need a different reader.")
    try:
        with open(path, "rb") as f:
            _, kvp = sc.read_file_header(f)
        kvp = {k: (int(v) if str(v).lstrip('-').isdigit() else v) for k, v in kvp.items()}
    except Exception as e:  # SARkit raises several exception types on bad headers
        raise MalformedFileError(f"cannot parse CPHD file header: {e}") from e
    blocks = {}
    for name in ("XML", "SUPPORT", "PVP", "SIGNAL"):
        off, sz = kvp.get(f"{name}_BLOCK_BYTE_OFFSET"), kvp.get(f"{name}_BLOCK_SIZE")
        if name == "SUPPORT" and (off is None or sz is None):
            continue
        if off is None or sz is None:
            raise MalformedFileError(f"header lacks {name}_BLOCK_BYTE_OFFSET/SIZE")
        if off + sz > size:
            raise MalformedFileError(
                f"file is truncated or smaller than its header declares: {name} block ends at byte "
                f"{off + sz}, file has {size} bytes")
        blocks[name] = (off, sz)
    return version, kvp, size


# ---------------------------------------------------------------- PVP helpers
def _pvp_array(pvp: np.ndarray, name: str) -> np.ndarray | None:
    if name not in (pvp.dtype.names or ()):
        return None
    a = np.asarray(pvp[name], dtype=np.float64)
    if name.endswith("Time") and a.ndim == 2 and a.shape[1] == 2:  # integer + fractional seconds form
        a = a[:, 0] + a[:, 1]
    return a


def _frequency(pvp: np.ndarray, sel: np.ndarray, fx_fixed: Param, meta_fxc: Param, meta_fxbw: Param) -> dict:
    out: dict[str, Any] = {"fx_fixed_metadata": fx_fixed.to_dict(), "fxc_metadata": meta_fxc.to_dict(),
                           "fxbw_metadata": meta_fxbw.to_dict()}
    fx1, fx2 = _pvp_array(pvp, "FX1"), _pvp_array(pvp, "FX2")
    if fx1 is None or fx2 is None:
        out["pvp_union_bandwidth"] = unavailable("PVP:FX1,FX2", "FX1/FX2 not in this file (TOA-domain?)").to_dict()
        return out
    fx1, fx2 = fx1[sel], fx2[sel]
    src = "PVP:FX1,FX2 over selected vectors"
    out["fx1_min_hz"] = derived(float(fx1.min()), "Hz", src).to_dict()
    out["fx2_max_hz"] = derived(float(fx2.max()), "Hz", src).to_dict()
    out["pvp_union_bandwidth"] = derived(float(fx2.max() - fx1.min()), "Hz", src,
                                         "max(FX2) - min(FX1); a different quantity from RFBandwidth metadata").to_dict()
    out["pvp_center_frequency"] = derived(float((fx2.max() + fx1.min()) / 2), "Hz", src).to_dict()
    out["pvp_per_vector_bandwidth_median"] = derived(float(np.median(fx2 - fx1)), "Hz", src).to_dict()
    for n, unit in (("SC0", "Hz"), ("SCSS", "Hz"), ("TOA1", "s"), ("TOA2", "s")):
        a = _pvp_array(pvp, n)
        if a is not None:
            a = a[sel]
            out[f"{n.lower()}_range"] = derived([float(a.min()), float(a.max())], unit, f"PVP:{n} min,max").to_dict()
    return out


def _aperture(xml, pvp: np.ndarray, nvec: int, opts: InspectOptions, ch_params) -> dict:
    names = pvp.dtype.names or ()
    signal_status: dict[str, Any]
    if "SIGNAL" in names:
        sv = np.asarray(pvp["SIGNAL"])
        valid = sv != 0
        n0, n1 = int((sv == 0).sum()), int((sv == 1).sum())
        nother = int(len(sv) - n0 - n1)
        valid_param = measured(int(valid.sum()), "vectors", "PVP:SIGNAL != 0",
                               "SIGNAL == 0 marks a zero-filled vector (SARkit checker requires all-zero samples there); "
                               "SIGNAL == 1 is normal; other values are flagged abnormal but kept (meaning not confirmed)")
        declared = _text(ch_params, "SignalNormal") if ch_params is not None else None
        signal_status = _tag({
            "counts": {"0": n0, "1": n1, "other": nother},
            "other_values": sorted({int(v) for v in np.unique(sv) if v not in (0, 1)}),
            "all_normal": bool(n1 == len(sv)),
            "signal_normal_metadata": None if declared is None else _bool(declared),
            "signal_normal_consistent": None if declared is None else bool(_bool(declared) == (n1 == len(sv))),
            "status_note": "SIGNAL is a per-vector status indicator. 0 = no valid signal (zero fill), excluded from the "
                           "default aperture; 1 = normal; other values are included and counted here. The full meaning of "
                           "values above 1 was not confirmed from the standard text."}, "PVP:SIGNAL, XML:Channel/Parameters/SignalNormal", "measured")
    else:
        valid = np.ones(nvec, dtype=bool)
        valid_param = assumed(nvec, "vectors", "no SIGNAL PVP", "all vectors assumed valid")
        signal_status = unavailable("PVP:SIGNAL", "SIGNAL PVP not present; vector validity cannot be checked").to_dict()
    sel = select_vectors(valid, opts.subaperture)
    mask = np.zeros(nvec, dtype=bool)
    for a, b in sel.runs:
        mask[a:b] = True
    out: dict[str, Any] = {
        "vectors_total": nvec,
        "vectors_valid": valid_param.to_dict(),
        "signal_status": signal_status,
        "vectors_invalid": derived(int(nvec - valid.sum()), "vectors", "total - valid").to_dict(),
        "first_valid_index": derived(int(np.flatnonzero(valid)[0]) if valid.any() else None, None, "PVP:SIGNAL").to_dict(),
        "last_valid_index": derived(int(np.flatnonzero(valid)[-1]) if valid.any() else None, None, "PVP:SIGNAL").to_dict(),
        "selection": _tag(sel.to_dict(), "policy: default full valid aperture; subaperture only if explicitly requested"),
        "geometry_definition": GEOMETRY_DEFINITION,
        "interpretation_note": INTERPRETATION_NOTE,
    }
    tx_t = _pvp_array(pvp, "TxTime")
    tx_p, rc_p, srp = _pvp_array(pvp, "TxPos"), _pvp_array(pvp, "RcvPos"), _pvp_array(pvp, "SRPPos")
    if tx_t is None or tx_p is None or srp is None or not mask.any():
        out["timing"] = unavailable("PVP:TxTime/TxPos/SRPPos", "required PVPs missing or no valid vectors").to_dict()
        return out
    out["timing"] = _tag(ap.timing_stats(tx_t[mask], opts.nonuniform_rtol), "PVP:TxTime over selected vectors (seconds from collection start)")
    rc_t = _pvp_array(pvp, "RcvTime")
    if rc_t is not None:
        out["rcv_timing"] = _tag(ap.timing_stats(rc_t[mask], opts.nonuniform_rtol), "PVP:RcvTime over selected vectors")
    out["tx_trajectory"] = _tag(ap.trajectory_stats(tx_p[mask], _pvp_array(pvp, "TxVel") if _pvp_array(pvp, "TxVel") is None
                                                    else _pvp_array(pvp, "TxVel")[mask], tx_t[mask]),
                                "PVP:TxPos,TxVel (ECF, m)")
    if rc_p is not None:
        rv = _pvp_array(pvp, "RcvVel")
        out["rcv_trajectory"] = _tag(ap.trajectory_stats(rc_p[mask], None if rv is None else rv[mask],
                                                         None if rc_t is None else rc_t[mask]), "PVP:RcvPos,RcvVel (ECF, m)")
    u_tx, _ = ap._los(tx_p[mask], srp[mask])
    if rc_p is not None:
        u_rc, _ = ap._los(rc_p[mask], srp[mask])
        bis = u_tx + u_rc
        norm = np.linalg.norm(bis, axis=1, keepdims=True)
        bis = np.divide(bis, norm, out=np.zeros_like(bis), where=norm > 0)
    else:
        u_rc, bis = None, u_tx
    span = ap.angular_span(bis, np.zeros_like(bis))
    span["tx_los"] = ap.angular_span(tx_p[mask], srp[mask])
    if rc_p is not None:
        span["rcv_los"] = ap.angular_span(rc_p[mask], srp[mask])
    out["angular_span"] = _tag(span, "PVP:TxPos,RcvPos,SRPPos (degrees; see geometry_definition)")
    srp_m = srp[mask]
    out["srp_motion_m"] = derived(float(np.linalg.norm(srp_m.max(axis=0) - srp_m.min(axis=0))), "m",
                                  "PVP:SRPPos extent over selected vectors", "0 means a fixed SRP").to_dict()
    ia = (_text(ch_params, "ImageArea/X1Y1/X"), _text(ch_params, "ImageArea/X1Y1/Y"),
          _text(ch_params, "ImageArea/X2Y2/X"), _text(ch_params, "ImageArea/X2Y2/Y")) if ch_params is not None else (None,) * 4
    if None in ia:
        out["image_area_metadata"] = unavailable("XML:Channel/Parameters/ImageArea").to_dict()
    else:
        x1, y1, x2, y2 = (float(v) for v in ia)
        out["image_area_metadata"] = measured({"x1y1_m": [x1, y1], "x2y2_m": [x2, y2]}, "m",
                                              "XML:Channel/Parameters/ImageArea",
                                              "area the producer declared in image-area coordinates; not derived from vector count").to_dict()
    try:
        rg = sc.compute_reference_geometry(xml, pvp)
        mono = rg.find(_q("Monostatic"))
        if mono is not None:
            keys = ("SlantRange", "GroundRange", "GrazeAngle", "IncidenceAngle", "AzimuthAngle", "DopplerConeAngle", "SideOfTrack")
            vals = {k: (_text(mono, k) if k == "SideOfTrack" else float(_text(mono, k))) for k in keys if _text(mono, k) is not None}
            out["sarkit_reference_geometry"] = derived(vals, "m or degrees", "sarkit.cphd.compute_reference_geometry",
                                                       "computed by SARkit at the reference vector").to_dict()
    except Exception as e:
        out["sarkit_reference_geometry"] = unavailable("sarkit.cphd.compute_reference_geometry", str(e)[:200]).to_dict()
    decl = xml.getroot().find(_q("ReferenceGeometry/Monostatic"))
    if decl is None:
        out["reference_geometry_declared"] = unavailable("XML:ReferenceGeometry/Monostatic",
                                                         "not present (or bistatic, which M1 does not summarize)").to_dict()
    else:
        keys = ("SlantRange", "GroundRange", "GrazeAngle", "IncidenceAngle", "AzimuthAngle", "DopplerConeAngle")
        dv = {k: float(_text(decl, k)) for k in keys if _text(decl, k) is not None}
        out["reference_geometry_declared"] = measured(dv, "m or degrees", "XML:ReferenceGeometry/Monostatic").to_dict()
        comp = out.get("sarkit_reference_geometry", {}).get("value")
        if comp:
            out["reference_geometry_difference"] = derived(
                {k: dv[k] - comp[k] for k in dv if k in comp and isinstance(comp.get(k), float)}, "m or degrees",
                "declared - SARkit computed", "differences are not a pass/fail test; tolerances are not defined here").to_dict()
    return out


# ---------------------------------------------------------------- consistency + scan
def _consistency(path: Path, thorough: bool) -> dict:
    try:
        with open(path, "rb") as f:
            c = CphdConsistency.from_file(file=f, schema=None, thorough=thorough)
            c.check()
            allr, fails = c.all(), c.failures(omit_passed_sub=True)
            skips = c.skips()
            partial = set(c.skips(include_partial=True)) - set(skips)
            def first_line(v):
                for d in v["details"]:
                    if d["severity"] == "No-Op":
                        return str(d["message"]).splitlines()[0][:160]
                return ""
            return {
                "ran": True, "thorough": thorough, "total": len(allr), "failed": len(fails), "inapplicable": len(skips),
                "passed": len(allr) - len(fails) - len(skips),
                "partially_inapplicable": len(partial),
                "failures": [{"check": k, "description": v.get("doc", ""),
                              "messages": [str(d["message"])[:300] for d in v["details"] if not d["passed"]][:5]}
                             for k, v in fails.items()],
                "inapplicable_checks": [{"check": k, "reason": v.get("doc") or "no applicable elements",
                                         "detail": first_line(v)} for k, v in skips.items()],
                "note": "Inapplicable checks passed vacuously because the file lacks the feature they test. "
                        "A zero-failure result does not prove scientific correctness.",
                "provenance": "derived", "source": f"sarkit.verification.CphdConsistency (SARkit {importlib.metadata.version('sarkit')})",
            }
    except Exception as e:
        return {"ran": False, "error": f"{type(e).__name__}: {str(e)[:300]}", "provenance": "unavailable",
                "source": "sarkit.verification.CphdConsistency"}


def _scan_signal(path: Path, offset: int, dtype: np.dtype, nvec: int, nsamp: int, budget: int) -> dict:
    chunks = plan_chunks(nvec, nsamp * dtype.itemsize * SCAN_WORKING_SET_FACTOR, budget)
    mm = np.memmap(path, dtype=dtype, mode="r", offset=offset, shape=(nvec, nsamp))
    nonfinite = zero_vec = 0
    max_abs2 = power = 0.0
    n_finite = 0
    first64 = None
    try:
        for a, b in chunks:
            blk = np.asarray(mm[a:b])
            re, im = blk.real.astype(np.float64), blk.imag.astype(np.float64)
            fin = np.isfinite(re) & np.isfinite(im)
            nonfinite += int(fin.size - fin.sum())
            p = np.where(fin, re * re + im * im, 0.0)
            zero_vec += int((p.sum(axis=1) == 0).sum())
            max_abs2 = max(max_abs2, float(p.max()))
            power += float(p.sum())
            n_finite += int(fin.sum())
            if a < 64:
                k = min(64, b) - a
                first64 = (first64 or [0.0, 0])
                first64[0] += float(p[:k].sum())
                first64[1] += k * nsamp
    finally:
        del mm
    return {"vectors_scanned": int(sum(b - a for a, b in chunks)), "samples": nvec * nsamp, "chunks": len(chunks),
            "chunk_vectors_max": int(max(b - a for a, b in chunks)) if chunks else 0, "chunk_budget_bytes": budget,
            "working_set_factor": SCAN_WORKING_SET_FACTOR, "nonfinite_samples": nonfinite, "all_zero_vectors": zero_vec,
            "max_abs": max_abs2 ** 0.5, "mean_power": power / max(n_finite, 1),
            "first_64_vectors_mean_power": (first64[0] / first64[1]) if first64 and first64[1] else None,
            "provenance": "derived", "source": "memory-mapped read-only signal block, chunked; arrays are not stored in the report"}


# ---------------------------------------------------------------- extra metadata
CORE_PVPS = ("TxTime", "TxPos", "TxVel", "RcvTime", "RcvPos", "RcvVel", "SRPPos", "aFDOP", "aFRR1", "aFRR2",
             "FX1", "FX2", "TOA1", "TOA2", "TDTropoSRP", "SC0", "SCSS")


def _pvp_availability(names: list[str]) -> dict:
    return {"core_missing": [n for n in CORE_PVPS if n not in names],
            "optional_present": [n for n in names if n not in CORE_PVPS],
            "provenance": "measured", "source": "PVP dtype from XML",
            "note": "core = the PVPs M1 uses for timing, geometry and frequency; not the full list the standard requires"}


def _support_arrays(root) -> list[dict]:
    out = []
    for n in root.findall(_q("Data/SupportArray")):
        out.append(_d({"identifier": _param(n, "Identifier"), "num_rows": _param(n, "NumRows", int),
                       "num_cols": _param(n, "NumCols", int), "bytes_per_element": _param(n, "BytesPerElement", int, "bytes"),
                       "byte_offset": _param(n, "ArrayByteOffset", int, "bytes")}))
    return out


def _cap(name: str, status: str, reason: str) -> dict:
    assert status in ("supported", "unsupported", "uncertain", "not_evaluated")
    return {"capability": name, "status": status, "reason": reason}


def _capabilities(r: dict, opts: InspectOptions) -> list[dict]:
    g = r["global"]
    dom = g["domain"]["value"]
    ch = r["channels"]
    caps = [_cap("cphd_version", "supported", f"version {r['format']['version']['value']} is read by {r['format']['reader']}")]
    if dom == "FX":
        caps.append(_cap("fx_domain_inspection", "supported", "DomainType FX: PVP frequency parameters present and summarized"))
    elif dom == "TOA":
        caps.append(_cap("toa_domain_inspection", "uncertain", "DomainType TOA: metadata is read, but TOA-domain handling has not been tested on a real file"))
    else:
        caps.append(_cap("domain_inspection", "uncertain", f"DomainType {dom!r} not recognised"))
    caps.append(_cap("multi_channel_inspection", "supported" if len(ch) > 1 else "uncertain",
                     f"{len(ch)} channel(s) read independently; multi-channel behaviour is validated on synthetic fixtures only"))
    comp = any(c["compressed_signal_size"]["value"] is not None for c in ch)
    caps.append(_cap("signal_scan", "unsupported" if comp else ("supported" if "signal_scan" in r else "not_evaluated"),
                     "compressed signal arrays are not scanned" if comp else
                     ("chunked scan completed (first channel)" if "signal_scan" in r else "scan not requested (--scan-signal)")))
    ct = g["collect_type"]["value"]
    caps.append(_cap("monostatic_geometry", "supported" if ct == "MONOSTATIC" else "uncertain",
                     "collect type MONOSTATIC" if ct == "MONOSTATIC" else f"collect type {ct!r}: bistatic geometry is summarized through a bisector line of sight only"))
    caps.append(_cap("tx_waveform_reconstruction", "unsupported",
                     "waveform samples are not stored in CPHD; metadata gives only parameters"))
    caps.append(_cap("full_aperture_selection", "supported", "default selection is every non-zero-fill vector"))
    cs = r["consistency"]
    caps.append(_cap("sarkit_consistency_checks",
                     "not_evaluated" if not cs.get("ran") else ("uncertain" if cs["failed"] else "supported"),
                     cs.get("error") or ("not run (disabled)" if not cs.get("ran") else
                                         f"{cs['failed']} failed, {cs['inapplicable']} inapplicable of {cs['total']}")))
    other = any((c["aperture"].get("signal_status", {}).get("counts") or {}).get("other") for c in ch)
    caps.append(_cap("signal_status_semantics", "uncertain" if other else "supported",
                     "SIGNAL values other than 0 and 1 present; meaning not confirmed" if other else
                     "only SIGNAL 0/1 (or no SIGNAL PVP) present"))
    caps.append(_cap("multi_provider_compatibility", "not_evaluated",
                     "provider-independent design; one file cannot validate other providers"))
    caps.append(_cap("image_formation_readiness", "not_evaluated", "out of scope for M1"))
    return caps


# ---------------------------------------------------------------- performance
def _peak_working_set() -> int | None:
    try:
        import ctypes
        import ctypes.wintypes as wt

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        k32, ps = ctypes.windll.kernel32, ctypes.windll.psapi
        k32.GetCurrentProcess.restype = wt.HANDLE
        ps.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(PMC), wt.DWORD]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        if ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return int(pmc.PeakWorkingSetSize)
    except Exception:
        pass
    try:
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    except Exception:
        return None


# ---------------------------------------------------------------- main entry
def inspect_cphd(path: str | Path, opts: InspectOptions | None = None) -> dict:
    """Inspect a CPHD file read-only. Raises CphdError subclasses on unusable input.

    The report is deterministic for a given file and options, except for the optional
    "performance" section (opts.measure_performance), which holds timings and memory.
    """
    opts = opts or InspectOptions()
    if not opts.measure_performance:
        return _inspect(Path(path), opts)
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        rep = _inspect(Path(path), opts)
        wall = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    rep["performance"] = {"wall_seconds": wall, "python_heap_peak_bytes": peak,
                          "process_peak_working_set_bytes": _peak_working_set(),
                          "provenance": "measured", "source": "time.perf_counter, tracemalloc, OS process counters",
                          "note": "python_heap_peak excludes memory-mapped file pages; the working set covers the whole process "
                                  "including mapped pages. Values vary between runs and are not part of the deterministic report."}
    return rep


def _inspect(path: Path, opts: InspectOptions) -> dict:
    version, kvp, size = _precheck(path)
    try:
        with open(path, "rb") as fh:
            reader = sc.Reader(fh)
            xml = reader.metadata.xmltree
            root = xml.getroot()
            report = _build(path, reader, xml, root, version, kvp, size, opts)
    except CphdError:
        raise
    except Exception as e:
        raise MalformedFileError(f"cannot read CPHD content: {type(e).__name__}: {str(e)[:300]}") from e
    if opts.run_consistency:
        report["consistency"] = _consistency(path, opts.thorough)
    else:
        report["consistency"] = {"ran": False, "provenance": "unavailable", "source": "disabled by option"}
    report["capabilities"] = _capabilities(report, opts)
    if opts.compute_hash:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1 << 24), b""):
                h.update(b)
        report["source"]["sha256"] = measured(h.hexdigest(), None, "sha256 of file bytes").to_dict()
    return report


def _build(path, reader, xml, root, version, kvp, size, opts) -> dict:
    sarkit_v = importlib.metadata.version("sarkit")
    ns = root.tag.split("}")[0][1:] if root.tag.startswith("{") else ""
    fmt_str = _text(root, "Data/SignalArrayFormat")
    try:
        # SARkit returns the native-order dtype; CPHD stores signal samples big-endian (as Reader.read_signal does).
        dtype = sc.binary_format_string_to_dtype(fmt_str).newbyteorder(">")
    except Exception as e:
        raise UnsupportedFormatError(f"unsupported SignalArrayFormat {fmt_str!r}: {e}") from e
    layout = {k.lower(): v for k, v in kvp.items() if k.endswith(("OFFSET", "SIZE"))}
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "source": {"path": str(path.resolve()), "name": path.name, "size_bytes": size, "read_only": True},
        "format": {"version": measured(version, None, "file header line 1").to_dict(), "supported": True,
                   "supported_versions": list(SUPPORTED_VERSIONS), "xml_namespace": ns,
                   "reader": f"SARkit {sarkit_v}", "header_fields": kvp},
        "global": _d({
            "collector_name": _param(root, "CollectionID/CollectorName"),
            "core_name": _param(root, "CollectionID/CoreName"),
            "collect_type": _param(root, "CollectionID/CollectType"),
            "radar_mode": _param(root, "CollectionID/RadarMode/ModeType"),
            "classification": _param(root, "CollectionID/Classification"),
            "domain": _param(root, "Global/DomainType"),
            "sgn": _param(root, "Global/SGN", int),
            "collection_start": _param(root, "Global/Timeline/CollectionStart"),
            "tx_time1": _param(root, "Global/Timeline/TxTime1", float, "s"),
            "tx_time2": _param(root, "Global/Timeline/TxTime2", float, "s"),
            "signal_array_format": _param(root, "Data/SignalArrayFormat"),
            "num_bytes_pvp": _param(root, "Data/NumBytesPVP", int, "bytes"),
            "num_channels": _param(root, "Data/NumCPHDChannels", int),
        }),
        "unavailable_by_design": UNAVAILABLE_BY_DESIGN,
    }
    wf = root.find(_q("TxRcv/TxWFParameters"))
    rcv = root.find(_q("TxRcv/RcvParameters"))
    report["tx_waveform"] = {
        "samples_in_file": unavailable("CPHD content", UNAVAILABLE_BY_DESIGN["transmitted_waveform_samples"]).to_dict(),
        "count_in_metadata": len(root.findall(_q("TxRcv/TxWFParameters"))),
        **(_d({"identifier": _param(wf, "Identifier"), "pulse_length": _param(wf, "PulseLength", float, "s"),
               "rf_bandwidth_metadata": _param(wf, "RFBandwidth", float, "Hz"),
               "center_frequency": _param(wf, "FreqCenter", float, "Hz"),
               "lfm_rate": _param(wf, "LFMRate", float, "Hz/s")}) if wf is not None else {}),
        "receiver": _d({"sample_rate": _param(rcv, "SampleRate", float, "Hz"),
                        "window_length": _param(rcv, "WindowLength", float, "s")}) if rcv is not None else {},
        "note": "Metadata describes the waveform. It does not reconstruct it; do not equate these values with the PVP frequency span.",
    }
    # channels
    chans, signal_total = [], 0
    ch_nodes = root.findall(_q("Data/Channel"))
    if not ch_nodes:
        raise MalformedFileError("no Data/Channel elements in CPHD XML")
    params_by_id = {_text(p, "Identifier"): p for p in root.findall(_q("Channel/Parameters"))}
    sig_off = kvp["SIGNAL_BLOCK_BYTE_OFFSET"]
    for dn in ch_nodes:
        cid = _text(dn, "Identifier")
        nv, ns_ = int(_text(dn, "NumVectors")), int(_text(dn, "NumSamples"))
        pvp = reader.read_pvps(cid)
        pp = params_by_id.get(cid)
        names = list(pvp.dtype.names or ())
        sig_bytes = nv * ns_ * dtype.itemsize
        comp = _param(dn, "CompressedSignalSize", int, "bytes")
        signal_total += sig_bytes if comp.value is None else comp.value
        so = _param(dn, "SignalArrayByteOffset", int)
        if so.value is not None and comp.value is None and so.value + sig_bytes > kvp["SIGNAL_BLOCK_SIZE"]:
            raise MalformedFileError(f"channel {cid!r} signal array ends beyond the SIGNAL block "
                                     f"({so.value + sig_bytes} > {kvp['SIGNAL_BLOCK_SIZE']} bytes)")
        sel_mask_tmp = None
        aperture = _aperture(xml, pvp, nv, opts, pp)
        sel = np.zeros(nv, dtype=bool)
        for a, b in aperture["selection"]["runs"]:
            sel[a:b] = True
        ch = {
            "identifier": measured(cid, None, "XML:Data/Channel/Identifier").to_dict(),
            "num_vectors": measured(nv, "vectors", "XML:Data/Channel/NumVectors").to_dict(),
            "num_samples": measured(ns_, "samples/vector", "XML:Data/Channel/NumSamples").to_dict(),
            "signal_dtype": derived(dtype.str, None, "XML:Data/SignalArrayFormat via SARkit",
                                    "numpy dtype of one stored sample; big-endian per the CPHD standard (the file does not state byte order)").to_dict(),
            "signal_bytes": derived(sig_bytes, "bytes", "NumVectors*NumSamples*itemsize").to_dict(),
            "signal_byte_offset": _param(dn, "SignalArrayByteOffset", int, "bytes").to_dict(),
            "pvp_byte_offset": _param(dn, "PVPArrayByteOffset", int, "bytes").to_dict(),
            "compressed_signal_size": comp.to_dict(),
            "pvp_fields": names,
            "pvp_availability": _pvp_availability(names),
            "pvp_count": len(pvp),
            "parameters": _d({
                "ref_vector_index": _param(pp, "RefVectorIndex", int),
                "fx_fixed": _param(pp, "FXFixed", _bool), "toa_fixed": _param(pp, "TOAFixed", _bool),
                "srp_fixed": _param(pp, "SRPFixed", _bool), "signal_normal": _param(pp, "SignalNormal", _bool),
                "tx_pol": _param(pp, "Polarization/TxPol"), "rcv_pol": _param(pp, "Polarization/RcvPol"),
                "toa_saved": _param(pp, "TOASaved", float, "s"),
            }) if pp is not None else {"note": unavailable("XML:Channel/Parameters").to_dict()},
            "frequency": _frequency(pvp, sel, _param(pp, "FXFixed", _bool) if pp is not None else unavailable("XML"),
                                    _param(pp, "FxC", float, "Hz") if pp is not None else unavailable("XML"),
                                    _param(pp, "FxBW", float, "Hz") if pp is not None else unavailable("XML")),
            "aperture": aperture,
        }
        chans.append(ch)
    ids = [c["identifier"]["value"] for c in chans]
    if len(set(ids)) != len(ids):
        raise MalformedFileError(f"duplicate channel identifiers in Data/Channel: {ids}")
    report["channels"] = chans
    report["support_arrays"] = _support_arrays(root)
    xml_sz = kvp["XML_BLOCK_SIZE"]
    report["layout"] = {
        "header_blocks": layout,
        "xml_block_end": kvp["XML_BLOCK_BYTE_OFFSET"] + xml_sz,
        "signal_block_matches_dimensions": bool(signal_total == kvp["SIGNAL_BLOCK_SIZE"]),
        "provenance": "derived", "source": "header block sizes vs XML dimensions",
    }
    report["warnings"] = [] if report["layout"]["signal_block_matches_dimensions"] else [
        "SIGNAL_BLOCK_SIZE differs from the sum of channel signal sizes"]
    if opts.scan_signal:  # first channel only
        c0 = ch_nodes[0]
        off = sig_off + int(_text(c0, "SignalArrayByteOffset") or 0)
        report["signal_scan"] = _scan_signal(path, off, dtype, int(_text(c0, "NumVectors")),
                                             int(_text(c0, "NumSamples")), opts.chunk_budget_bytes)
        report["signal_scan"]["channel"] = _text(c0, "Identifier")
    return report
