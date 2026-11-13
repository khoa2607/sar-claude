import numpy as np
import pytest
from sarsil.cphd.aperture import timing_stats, trajectory_stats, angular_span


def test_uniform_timing():
    t = np.arange(1000) * 1e-4
    s = timing_stats(t)
    assert s["count"] == 1000
    assert s["duration_s"] == pytest.approx(0.0999)
    assert s["dt_median_s"] == pytest.approx(1e-4)
    assert s["nonuniform"] is False and s["gap_indices"] == [] and s["non_monotonic_count"] == 0


def test_gap_and_nonuniform_detected_using_actual_times_not_assumed_prf():
    t = np.arange(100) * 1e-3
    t[50:] += 5e-3  # 5 ms gap before index 50
    s = timing_stats(t)
    assert s["nonuniform"] is True and s["gap_indices"] == [50]


def test_non_monotonic_counted():
    t = np.array([0.0, 1.0, 0.5, 2.0])
    assert timing_stats(t)["non_monotonic_count"] == 1


def test_single_vector_timing_is_degenerate_not_crash():
    s = timing_stats(np.array([3.0]))
    assert s["count"] == 1 and s["duration_s"] == 0.0 and s["dt_median_s"] is None


def test_straight_line_trajectory():
    t = np.linspace(0, 10, 101)
    pos = np.stack([100.0 * t, np.zeros_like(t), np.zeros_like(t)], axis=1)
    vel = np.tile([100.0, 0, 0], (101, 1))
    s = trajectory_stats(pos, vel)
    assert s["path_length_m"] == pytest.approx(1000.0)
    assert s["chord_length_m"] == pytest.approx(1000.0)
    assert s["max_deviation_from_chord_m"] == pytest.approx(0.0, abs=1e-9)
    assert s["speed_mean_mps"] == pytest.approx(100.0)


def test_circular_arc_deviation_matches_sagitta():
    R, half = 1000.0, np.deg2rad(10)
    th = np.linspace(-half, half, 2001)
    pos = np.stack([R * np.sin(th), np.zeros_like(th), R * np.cos(th)], axis=1)
    s = trajectory_stats(pos, None)
    assert s["path_length_m"] == pytest.approx(R * 2 * half, rel=1e-6)
    assert s["max_deviation_from_chord_m"] == pytest.approx(R * (1 - np.cos(half)), rel=1e-4)
    assert s["speed_source"] == "finite_difference" or s["speed_mean_mps"] is None


def test_angular_span_circular_arc_around_scene():
    R, half = 5000.0, np.deg2rad(7.5)
    th = np.linspace(-half, half, 501)
    pos = np.stack([R * np.sin(th), np.zeros_like(th), R * np.cos(th)], axis=1)
    srp = np.zeros((501, 3))
    a = angular_span(pos, srp)
    assert a["first_last_deg"] == pytest.approx(15.0, abs=1e-6)
    assert a["max_from_first_deg"] == pytest.approx(15.0, abs=1e-6)
    assert a["cumulative_deg"] == pytest.approx(15.0, abs=1e-6)


def test_angular_span_straight_pass_matches_geometry():
    d, L = 1000.0, 400.0
    x = np.linspace(-L / 2, L / 2, 801)
    pos = np.stack([x, np.zeros_like(x), np.full_like(x, d)], axis=1)
    a = angular_span(pos, np.zeros_like(pos))
    assert a["first_last_deg"] == pytest.approx(np.rad2deg(2 * np.arctan(L / 2 / d)), abs=1e-6)


def test_angular_span_handles_platform_at_scene_point():
    pos = np.zeros((3, 3)); a = angular_span(pos, np.zeros((3, 3)))
    assert a["first_last_deg"] is None
