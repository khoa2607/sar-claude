"""Command line: python -m sarsil.cphd <file.cphd> [options]. Read-only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .chunking import DEFAULT_CHUNK_BUDGET_BYTES
from .errors import CphdError
from .inspector import InspectOptions, inspect_cphd


def _v(p):
    return p.get("value") if isinstance(p, dict) else None


def summarize(r: dict) -> str:
    g, f = r["global"], r["format"]
    L = [f"{r['source']['name']}  ({r['source']['size_bytes']:,} bytes)",
         f"CPHD {_v(f['version'])}  reader {f['reader']}  collector {_v(g['collector_name'])}  "
         f"{_v(g['collect_type'])} {_v(g['radar_mode'])}",
         f"domain {_v(g['domain'])}  SGN {_v(g['sgn'])}  start {_v(g['collection_start'])}"]
    for c in r["channels"]:
        a = c["aperture"]
        L.append(f"channel {_v(c['identifier'])}: {_v(c['num_vectors'])} vectors x {_v(c['num_samples'])} samples, "
                 f"{_v(c['signal_dtype'])}, {len(c['pvp_fields'])} PVP fields")
        s = a["selection"]
        L.append(f"  aperture: {s['count']} of {a['vectors_total']} vectors selected (policy {s['policy']}), "
                 f"{_v(a['vectors_invalid'])} invalid")
        if "duration_s" in a.get("timing", {}):
            t, ang = a["timing"], a["angular_span"]
            spread = (t['dt_max_s'] - t['dt_min_s']) / t['dt_median_s'] * 100 if t['dt_median_s'] else float('nan')
            L.append(f"  timing: {t['duration_s']:.6f} s, median dt {t['dt_median_s']:.3e} s, dt spread {spread:.3f}% "
                     f"(flagged nonuniform: {t['nonuniform']}), gaps {len(t['gap_indices'])}")
            L.append(f"  angular span (bisector LOS): first-last {ang['first_last_deg']:.4f} deg, "
                     f"cumulative {ang['cumulative_deg']:.4f} deg")
        fr = c["frequency"]
        if "pvp_union_bandwidth" in fr and _v(fr["pvp_union_bandwidth"]) is not None:
            L.append(f"  PVP union bandwidth {_v(fr['pvp_union_bandwidth']) / 1e6:.3f} MHz "
                     f"(metadata RFBandwidth is a separate quantity)")
    w = r["tx_waveform"]
    L.append("TX waveform samples in file: unavailable (metadata description only)")
    cs = r["consistency"]
    if cs.get("ran"):
        L.append(f"consistency: {cs['total']} checks, {cs['passed']} passed, {cs['failed']} failed, "
                 f"{cs['inapplicable']} inapplicable to this file")
    else:
        L.append("consistency: not run" + (f" ({cs.get('error')})" if cs.get("error") else ""))
    if "signal_scan" in r:
        sc_ = r["signal_scan"]
        L.append(f"signal scan: {sc_['vectors_scanned']} vectors in {sc_['chunks']} chunks, "
                 f"non-finite {sc_['nonfinite_samples']}, max|x| {sc_['max_abs']:.4g}")
    caps = r.get("capabilities", [])
    if caps:
        by = {}
        for c_ in caps:
            by.setdefault(c_["status"], []).append(c_["capability"])
        L.append("capabilities: " + "; ".join(f"{k} {len(v)}" for k, v in sorted(by.items())))
    if "performance" in r:
        pf = r["performance"]
        L.append(f"performance: {pf['wall_seconds']:.2f} s, python heap peak {pf['python_heap_peak_bytes'] / 2**20:.1f} MiB, "
                 f"process peak working set {(pf['process_peak_working_set_bytes'] or 0) / 2**20:.0f} MiB")
    for w_ in r.get("warnings", []):
        L.append(f"WARNING: {w_}")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sarsil.cphd", description="Read-only CPHD inspector (M1)")
    ap.add_argument("file")
    ap.add_argument("--json", metavar="PATH", help="write the full report here (default outputs/inspection/<name>.json)")
    ap.add_argument("--scan-signal", action="store_true", help="chunked read-only scan of the signal block")
    ap.add_argument("--no-consistency", action="store_true", help="skip the SARkit consistency checks")
    ap.add_argument("--thorough", action="store_true", help="thorough consistency checks (reads more of the file)")
    ap.add_argument("--hash", action="store_true", help="include SHA-256 of the file")
    ap.add_argument("--chunk-budget-mib", type=float, default=DEFAULT_CHUNK_BUDGET_BYTES / 2**20,
                    help="memory budget for chunked reads (default %(default).0f MiB)")
    ap.add_argument("--nonuniform-rtol", type=float, default=None,
                    help="flag timing as nonuniform when (dt_max-dt_min)/dt_median exceeds this (default 1e-3)")
    ap.add_argument("--perf", action="store_true", help="add wall time and peak memory (non-deterministic section)")
    ap.add_argument("--subaperture", nargs=2, type=int, metavar=("START", "STOP"),
                    help="explicit subaperture [START, STOP); default is the full aperture")
    a = ap.parse_args(argv)
    opts = InspectOptions(scan_signal=a.scan_signal, run_consistency=not a.no_consistency, thorough=a.thorough,
                          compute_hash=a.hash, chunk_budget_bytes=int(a.chunk_budget_mib * 2**20),
                          subaperture=tuple(a.subaperture) if a.subaperture else None,
                          measure_performance=a.perf,
                          **({} if a.nonuniform_rtol is None else {"nonuniform_rtol": a.nonuniform_rtol}))
    try:
        rep = inspect_cphd(a.file, opts)
    except CphdError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    out = Path(a.json) if a.json else Path("outputs/inspection") / (Path(a.file).stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    print(summarize(rep))
    print(f"full report: {out}")
    return 3 if rep["consistency"].get("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
