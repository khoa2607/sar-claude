"""Aperture characterization from per-vector parameters (no image formation).

Geometry conventions
--------------------
Positions are in the CPHD ECF frame (WGS 84, meters) as given by the PVPs. The
line-of-sight (LOS) unit vector at vector i is (platform_i - SRP_i) / norm, using
the per-vector SRPPos. Angular span is measured between LOS vectors:
  first_last_deg      angle between the first and last vector's LOS
  max_from_first_deg  largest angle between any vector's LOS and the first one
  cumulative_deg      sum of angles between consecutive vectors
These describe the collection geometry. They are not resolution, pixel spacing
or scene extent.
"""
from __future__ import annotations

import numpy as np

# A collection is flagged nonuniform when (dt_max - dt_min) / dt_median exceeds this.
NONUNIFORM_RTOL = 1e-3
# A dt above this multiple of the median is reported as a gap.
GAP_FACTOR = 1.5


def timing_stats(t: np.ndarray, nonuniform_rtol: float = NONUNIFORM_RTOL,
                 gap_factor: float = GAP_FACTOR) -> dict:
    t = np.asarray(t, dtype=np.float64)
    n = int(t.size)
    out = {"count": n, "t_first_s": float(t[0]) if n else None, "t_last_s": float(t[-1]) if n else None,
           "duration_s": float(t[-1] - t[0]) if n else 0.0, "dt_median_s": None, "dt_min_s": None,
           "dt_max_s": None, "dt_std_s": None, "nonuniform": False, "gap_indices": [],
           "non_monotonic_count": 0}
    if n < 2:
        return out
    dt = np.diff(t)
    med = float(np.median(dt))
    out.update(dt_median_s=med, dt_min_s=float(dt.min()), dt_max_s=float(dt.max()), dt_std_s=float(dt.std()),
               non_monotonic_count=int((dt <= 0).sum()))
    if med > 0:
        out["nonuniform"] = bool((dt.max() - dt.min()) / med > nonuniform_rtol)
        out["gap_indices"] = [int(i) + 1 for i in np.flatnonzero(dt > gap_factor * med)]
    return out


def trajectory_stats(pos: np.ndarray, vel: np.ndarray | None, t: np.ndarray | None = None) -> dict:
    """Path length, chord, straightness and speed. Speed uses the velocity PVP when given."""
    p = np.asarray(pos, dtype=np.float64)
    out = {"path_length_m": 0.0, "chord_length_m": 0.0, "max_deviation_from_chord_m": 0.0,
           "speed_mean_mps": None, "speed_min_mps": None, "speed_max_mps": None, "speed_source": None}
    if len(p) < 2:
        return out
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    chord = p[-1] - p[0]
    clen = float(np.linalg.norm(chord))
    out["path_length_m"] = float(seg.sum())
    out["chord_length_m"] = clen
    if clen > 0:
        u = chord / clen
        rel = p - p[0]
        perp = rel - np.outer(rel @ u, u)
        out["max_deviation_from_chord_m"] = float(np.linalg.norm(perp, axis=1).max())
    if vel is not None:
        sp = np.linalg.norm(np.asarray(vel, dtype=np.float64), axis=1)
        out["speed_source"] = "velocity_pvp"
    elif t is not None and len(t) == len(p):
        dt = np.diff(np.asarray(t, dtype=np.float64))
        ok = dt > 0
        sp = seg[ok] / dt[ok]
        out["speed_source"] = "finite_difference"
    else:
        return out
    if sp.size:
        out.update(speed_mean_mps=float(sp.mean()), speed_min_mps=float(sp.min()), speed_max_mps=float(sp.max()))
    return out


def _los(platform: np.ndarray, srp: np.ndarray):
    v = np.asarray(platform, dtype=np.float64) - np.asarray(srp, dtype=np.float64)
    n = np.linalg.norm(v, axis=1)
    ok = n > 0
    u = np.zeros_like(v)
    u[ok] = v[ok] / n[ok, None]
    return u, ok


def _angle_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Angle between unit-vector rows via atan2, accurate at small angles."""
    cross = np.linalg.norm(np.cross(a, b), axis=-1)
    dot = np.sum(a * b, axis=-1)
    return np.rad2deg(np.arctan2(cross, dot))


def angular_span(platform_pos: np.ndarray, srp_pos: np.ndarray) -> dict:
    u, ok = _los(platform_pos, srp_pos)
    out = {"first_last_deg": None, "max_from_first_deg": None, "cumulative_deg": None}
    if len(u) < 2 or not ok.all():
        return out
    out["first_last_deg"] = float(_angle_deg(u[0], u[-1]))
    out["max_from_first_deg"] = float(_angle_deg(u, u[0]).max())
    out["cumulative_deg"] = float(_angle_deg(u[:-1], u[1:]).sum())
    return out
