"""Compare a CPHD and its SICD (read-only). Writes outputs/comparison/<name>.json and prints a compact table.

    .venv\\Scripts\\python.exe scripts\\compare_cphd_sicd.py cphd\\<file>.cphd cphd\\<file>.nitf
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sarsil.cphd.errors import CphdError  # noqa: E402
from sarsil.compare.cphd_sicd import compare_cphd_sicd  # noqa: E402


def main(argv=None) -> int:
    a = sys.argv[1:] if argv is None else argv
    if len(a) != 2:
        print("usage: compare_cphd_sicd.py CPHD SICD", file=sys.stderr)
        return 2
    try:
        rep = compare_cphd_sicd(a[0], a[1])
    except (CphdError, OSError, ValueError, KeyError) as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    out = Path("outputs/comparison") / (Path(a[0]).stem + "__vs__" + Path(a[1]).stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    t = rep["tolerances"]
    print(f"tolerances: geometry {t['geometry_m']:.3f} m, angle {t['angle_deg']:.2e} deg, PRI {t['pri_s']:.3e} s")
    for r in rep["rows"]:
        d = "" if r["difference"] is None else f"{r['difference']:+.3e}"
        tl = "" if r["tolerance"] is None else f"{r['tolerance']:.3e}"
        print(f"{r['status'][:6]:6} {r['id']:<58} diff {d:>11} tol {tl:>10}")
    s = rep["summary"]
    print(f"summary: {s['within_tolerance']} within, {s['exceeds_tolerance']} exceed, {s['informational']} informational; report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
