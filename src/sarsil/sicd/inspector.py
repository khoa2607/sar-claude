"""Read-only SICD inspector (milestone M2).

Reports the metadata needed to use a vendor SICD as a *reference* for future image comparison, with the same
measured / derived / assumed / unavailable provenance as the CPHD inspector. Pixel data are never read here.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path
from typing import Any

import sarkit.sicd as ss
from sarkit.verification import SicdConsistency

from sarsil.cphd.errors import MalformedFileError
from sarsil.provenance import Param, derived, measured, unavailable
from sarsil.xmlparam import params_to_dict as _d, param as _param, q as _q, text as _text

SCHEMA = "sarsil.sicd_inspection/1"
REFERENCE_CAVEATS = [
    "A vendor SICD is the output of a specific, partly undocumented processing chain, not ground truth.",
    "Processing steps recorded in the SICD (for example RFI removal) may differ from what is applied to the CPHD.",
    "Weighting, calibration and phase conventions are only as documented in the SICD XML; absent fields are unavailable.",
]


def _vec(node, path: str, unit: str, src: str) -> Param:
    if node is None:
        return unavailable(src, "parent element absent")
    e = node.find(_q(path))
    if e is None:
        return unavailable(src, "element absent")
    try:
        return measured([float(e.findtext(_q(k))) for k in ("X", "Y", "Z")], unit, src)
    except (TypeError, ValueError):
        return unavailable(src, "could not parse X/Y/Z")


def _llh(node, path: str, src: str) -> Param:
    e = node.find(_q(path))
    if e is None:
        return unavailable(src, "element absent")
    try:
        return measured([float(e.findtext(_q(k))) for k in ("Lat", "Lon", "HAE")], "deg, deg, m", src)
    except (TypeError, ValueError):
        return unavailable(src, "could not parse Lat/Lon/HAE")


def _precheck(path: Path) -> int:
    if not path.exists():
        raise MalformedFileError(f"file does not exist: {path}")
    if not path.is_file():
        raise MalformedFileError(f"not a regular file: {path}")
    size = path.stat().st_size
    if size == 0:
        raise MalformedFileError(f"file is empty: {path}")
    with open(path, "rb") as f:
        head = f.read(9)
    if not head.startswith(b"NITF"):
        raise MalformedFileError(f"not a NITF file (SICD is carried in NITF): {path.name}")
    return size


def _consistency(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            c = SicdConsistency.from_file(file=f)
            c.check()
            allr, fails, skips = c.all(), c.failures(omit_passed_sub=True), c.skips()
            return {
                "ran": True, "total": len(allr), "failed": len(fails), "inapplicable": len(skips),
                "passed": len(allr) - len(fails) - len(skips),
                "partially_inapplicable": len(set(c.skips(include_partial=True)) - set(skips)),
                "failures": [{"check": k, "description": v.get("doc", ""),
                              "messages": [str(d["message"])[:300] for d in v["details"] if not d["passed"]][:5]}
                             for k, v in fails.items()],
                "inapplicable_checks": [{"check": k, "reason": v.get("doc") or "no applicable elements"}
                                        for k, v in skips.items()],
                "note": "Inapplicable checks pass vacuously. Zero failures does not prove scientific correctness.",
                "provenance": "derived",
                "source": f"sarkit.verification.SicdConsistency (SARkit {importlib.metadata.version('sarkit')})",
            }
    except Exception as e:
        return {"ran": False, "error": f"{type(e).__name__}: {str(e)[:300]}", "provenance": "unavailable",
                "source": "sarkit.verification.SicdConsistency"}


def inspect_sicd(path: str | Path, run_consistency: bool = True, compute_hash: bool = False) -> dict:
    """Inspect a SICD NITF file read-only. Raises MalformedFileError on unusable input."""
    path = Path(path)
    size = _precheck(path)
    try:
        with open(path, "rb") as fh:
            xml = ss.NitfReader(fh).metadata.xmltree
    except Exception as e:
        raise MalformedFileError(f"cannot read SICD content: {type(e).__name__}: {str(e)[:300]}") from e
    root = xml.getroot()
    ns = root.tag.split("}")[0][1:] if root.tag.startswith("{") else ""
    g = lambda p: root.find(_q(p))  # noqa: E731
    rep: dict[str, Any] = {
        "schema": SCHEMA,
        "source": {"path": str(path.resolve()), "name": path.name, "size_bytes": size, "read_only": True},
        "format": {"sicd_version": measured(ns.rsplit(":", 1)[-1], None, "XML namespace").to_dict(),
                   "reader": f"SARkit {importlib.metadata.version('sarkit')}"},
        "collection": _d({"collector_name": _param(root, "CollectionInfo/CollectorName"),
                          "core_name": _param(root, "CollectionInfo/CoreName"),
                          "collect_type": _param(root, "CollectionInfo/CollectType"),
                          "radar_mode": _param(root, "CollectionInfo/RadarMode/ModeType")}),
        "image": _d({"num_rows": _param(root, "ImageData/NumRows", int), "num_cols": _param(root, "ImageData/NumCols", int),
                     "pixel_type": _param(root, "ImageData/PixelType"),
                     "first_row": _param(root, "ImageData/FirstRow", int), "first_col": _param(root, "ImageData/FirstCol", int),
                     "scp_pixel_row": _param(root, "ImageData/SCPPixel/Row", int),
                     "scp_pixel_col": _param(root, "ImageData/SCPPixel/Col", int)}),
        "grid": _d({
            "image_plane": _param(root, "Grid/ImagePlane"), "type": _param(root, "Grid/Type"),
            "row_ss_m": _param(root, "Grid/Row/SS", float, "m"), "col_ss_m": _param(root, "Grid/Col/SS", float, "m"),
            "row_imp_resp_wid_m": _param(root, "Grid/Row/ImpRespWid", float, "m"),
            "col_imp_resp_wid_m": _param(root, "Grid/Col/ImpRespWid", float, "m"),
            "row_imp_resp_bw": _param(root, "Grid/Row/ImpRespBW", float, "cycles/m"),
            "col_imp_resp_bw": _param(root, "Grid/Col/ImpRespBW", float, "cycles/m"),
            "row_kctr": _param(root, "Grid/Row/KCtr", float, "cycles/m"), "col_kctr": _param(root, "Grid/Col/KCtr", float, "cycles/m"),
            "row_sgn": _param(root, "Grid/Row/Sgn", int), "col_sgn": _param(root, "Grid/Col/Sgn", int),
            "row_weighting": _param(root, "Grid/Row/WgtType/WindowName"), "col_weighting": _param(root, "Grid/Col/WgtType/WindowName"),
            "time_coa_s": _param(root, "Grid/TimeCOAPoly/Coef", float, "s", "XML:Grid/TimeCOAPoly/Coef (constant polynomial)"),
        }),
        "formation": _d({
            "algorithm": _param(root, "ImageFormation/ImageFormAlgo"),
            "t_start_proc_s": _param(root, "ImageFormation/TStartProc", float, "s"),
            "t_end_proc_s": _param(root, "ImageFormation/TEndProc", float, "s"),
            "tx_freq_proc_min_hz": _param(root, "ImageFormation/TxFrequencyProc/MinProc", float, "Hz"),
            "tx_freq_proc_max_hz": _param(root, "ImageFormation/TxFrequencyProc/MaxProc", float, "Hz"),
            "st_beam_comp": _param(root, "ImageFormation/STBeamComp"), "image_beam_comp": _param(root, "ImageFormation/ImageBeamComp"),
            "az_autofocus": _param(root, "ImageFormation/AzAutofocus"), "rg_autofocus": _param(root, "ImageFormation/RgAutofocus"),
            "polar_ang_ref_time_s": _param(root, "PFA/PolarAngRefTime", float, "s"),
        }),
        "frequency": _d({"tx_min_hz": _param(root, "RadarCollection/TxFrequency/Min", float, "Hz"),
                         "tx_max_hz": _param(root, "RadarCollection/TxFrequency/Max", float, "Hz")}),
        "timeline": _d({"collect_start": _param(root, "Timeline/CollectStart"),
                        "collect_duration_s": _param(root, "Timeline/CollectDuration", float, "s"),
                        "ipp_start": _param(root, "Timeline/IPP/Set/IPPStart", int), "ipp_end": _param(root, "Timeline/IPP/Set/IPPEnd", int),
                        "ipp_t_start_s": _param(root, "Timeline/IPP/Set/TStart", float, "s"),
                        "ipp_t_end_s": _param(root, "Timeline/IPP/Set/TEnd", float, "s")}),
        "scpcoa": _d({"scp_time_s": _param(root, "SCPCOA/SCPTime", float, "s"),
                      "arp_pos_ecf_m": _vec(g("SCPCOA"), "ARPPos", "m", "XML:SCPCOA/ARPPos"),
                      "arp_vel_ecf_mps": _vec(g("SCPCOA"), "ARPVel", "m/s", "XML:SCPCOA/ARPVel"),
                      "side_of_track": _param(root, "SCPCOA/SideOfTrack"),
                      "slant_range_m": _param(root, "SCPCOA/SlantRange", float, "m"),
                      "ground_range_m": _param(root, "SCPCOA/GroundRange", float, "m"),
                      "doppler_cone_deg": _param(root, "SCPCOA/DopplerConeAng", float, "deg"),
                      "graze_deg": _param(root, "SCPCOA/GrazeAng", float, "deg"),
                      "incidence_deg": _param(root, "SCPCOA/IncidenceAng", float, "deg"),
                      "azimuth_deg": _param(root, "SCPCOA/AzimAng", float, "deg")}),
        "waveform": _d({"tx_pulse_length_s": _param(root, "RadarCollection/Waveform/WFParameters/TxPulseLength", float, "s"),
                        "tx_rf_bandwidth_hz": _param(root, "RadarCollection/Waveform/WFParameters/TxRFBandwidth", float, "Hz"),
                        "tx_fm_rate_hz_per_s": _param(root, "RadarCollection/Waveform/WFParameters/TxFMRate", float, "Hz/s"),
                        "adc_sample_rate_hz": _param(root, "RadarCollection/Waveform/WFParameters/ADCSampleRate", float, "Hz"),
                        "rcv_window_length_s": _param(root, "RadarCollection/Waveform/WFParameters/RcvWindowLength", float, "s"),
                        "tx_polarization": _param(root, "RadarCollection/TxPolarization"),
                        "rcv_polarization": _param(root, "RadarCollection/RcvChannels/ChanParameters/TxRcvPolarization")}),
        "radiometric": _d({"present": measured(g("Radiometric") is not None, None, "XML:Radiometric")}),
        "reference_caveats": REFERENCE_CAVEATS,
    }
    # derived and list-valued items
    gd = g("GeoData")
    rep["geodata"] = _d({
        "earth_model": _param(root, "GeoData/EarthModel"),
        "scp_ecf_m": _vec(gd, "SCP/ECF", "m", "XML:GeoData/SCP/ECF") if gd is not None else unavailable("XML:GeoData"),
        "scp_llh": _llh(gd, "SCP/LLH", "XML:GeoData/SCP/LLH") if gd is not None else unavailable("XML:GeoData"),
    })
    rep["geodata"]["image_corners_lat_lon"] = measured(
        [[float(c.findtext(_q("Lat"))), float(c.findtext(_q("Lon")))] for c in root.findall(_q("GeoData/ImageCorners/ICP"))],
        "deg", "XML:GeoData/ImageCorners/ICP (order FRFC, FRLC, LRLC, LRFC)").to_dict()
    rep["geodata"]["area_corners_lat_lon"] = measured(
        [[float(c.findtext(_q("Lat"))), float(c.findtext(_q("Lon")))] for c in root.findall(_q("RadarCollection/Area/Corner/ACP"))],
        "deg", "XML:RadarCollection/Area/Corner/ACP").to_dict()
    rep["grid"]["row_uvect_ecf"] = _vec(g("Grid/Row"), "UVectECF", "unit", "XML:Grid/Row/UVectECF").to_dict()
    rep["grid"]["col_uvect_ecf"] = _vec(g("Grid/Col"), "UVectECF", "unit", "XML:Grid/Col/UVectECF").to_dict()
    rep["formation"]["processing_steps"] = [
        measured((p.findtext(_q("Type")) or "").strip(), None, "XML:ImageFormation/Processing/Type").to_dict()
        for p in root.findall(_q("ImageFormation/Processing"))]
    lo, hi = rep["frequency"]["tx_min_hz"]["value"], rep["frequency"]["tx_max_hz"]["value"]
    if lo is not None and hi is not None:
        rep["frequency"]["bandwidth_hz"] = derived(hi - lo, "Hz", "TxFrequency Max - Min").to_dict()
        rep["frequency"]["center_hz"] = derived((hi + lo) / 2, "Hz", "TxFrequency (Max + Min)/2").to_dict()
    rep["consistency"] = _consistency(path) if run_consistency else {"ran": False, "provenance": "unavailable", "source": "disabled"}
    if compute_hash:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1 << 24), b""):
                h.update(b)
        rep["source"]["sha256"] = measured(h.hexdigest(), None, "sha256 of file bytes").to_dict()
    return rep
