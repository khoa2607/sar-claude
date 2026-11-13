"""Synthetic multi-channel fixtures with known answers, plus negative tests."""
import json

import numpy as np
import pytest

import cphd_fixtures as fx
from sarsil.cphd.errors import MalformedFileError, UnsupportedFormatError
from sarsil.cphd.inspector import InspectOptions, inspect_cphd

pytestmark = pytest.mark.skipif(not fx.REAL.exists(), reason="fixture XML template comes from the local Umbra file")
NOCHK = dict(run_consistency=False)

CH2 = [dict(id="A", nv=64, ns=48, arc_deg=2.0), dict(id="B", nv=40, ns=32, arc_deg=0.5)]


@pytest.fixture(scope="module")
def two_ch(tmp_path_factory):
    return fx.build_cphd(tmp_path_factory.mktemp("syn") / "two.cphd", CH2)


def test_two_channels_are_discovered_with_their_own_dimensions(two_ch):
    r = inspect_cphd(two_ch, InspectOptions(**NOCHK))
    ids = [c["identifier"]["value"] for c in r["channels"]]
    assert ids == ["A", "B"]
    assert [(c["num_vectors"]["value"], c["num_samples"]["value"]) for c in r["channels"]] == [(64, 48), (40, 32)]
    assert r["global"]["num_channels"]["value"] == 2
    assert r["support_arrays"] == []
    assert r["layout"]["signal_block_matches_dimensions"] is True


def test_angular_span_equals_the_designed_arc_for_each_channel(two_ch):
    r = inspect_cphd(two_ch, InspectOptions(**NOCHK))
    for c, arc in zip(r["channels"], (2.0, 0.5)):
        a = c["aperture"]["angular_span"]
        assert a["first_last_deg"] == pytest.approx(arc, abs=1e-6)
        assert a["cumulative_deg"] == pytest.approx(arc, abs=1e-6)
        assert a["max_from_first_deg"] == pytest.approx(arc, abs=1e-6)


def test_trajectory_speed_and_timing_match_the_design(two_ch):
    c = inspect_cphd(two_ch, InspectOptions(**NOCHK))["channels"][0]["aperture"]
    omega = np.deg2rad(2.0) / (63 * fx.DT_S)
    assert c["tx_trajectory"]["speed_mean_mps"] == pytest.approx(fx.RADIUS_M * omega, rel=1e-9)
    assert c["timing"]["dt_median_s"] == pytest.approx(fx.DT_S, rel=1e-12)
    assert c["timing"]["nonuniform"] is False
    assert c["srp_motion_m"]["value"] == 0.0


def test_frequency_summary_is_exact(two_ch):
    f = inspect_cphd(two_ch, InspectOptions(**NOCHK))["channels"][1]["frequency"]
    assert f["pvp_union_bandwidth"]["value"] == pytest.approx(fx.FX2_HZ - fx.FX1_HZ)
    assert f["pvp_center_frequency"]["value"] == pytest.approx((fx.FX1_HZ + fx.FX2_HZ) / 2)


def test_report_is_deterministic_bytes(two_ch):
    a = json.dumps(inspect_cphd(two_ch, InspectOptions(scan_signal=True)), sort_keys=True)
    b = json.dumps(inspect_cphd(two_ch, InspectOptions(scan_signal=True)), sort_keys=True)
    assert a == b


def test_flagged_zero_fill_vectors_are_excluded_and_counted(tmp_path):
    p = fx.build_cphd(tmp_path / "f.cphd", [dict(id="A", nv=64, ns=16, arc_deg=1.0, flagged=[5, 6, 40])])
    r = inspect_cphd(p, InspectOptions(scan_signal=True, **NOCHK))
    ap = r["channels"][0]["aperture"]
    assert ap["selection"]["policy"] == "full"
    assert ap["selection"]["count"] == 61 and ap["selection"]["runs"] == [[0, 5], [7, 40], [41, 64]]
    s = ap["signal_status"]
    assert s["counts"] == {"0": 3, "1": 61, "other": 0} and s["all_normal"] is False
    assert s["signal_normal_metadata"] is False and s["signal_normal_consistent"] is True
    assert ap["timing"]["count"] == 61 and ap["timing"]["gap_indices"] == [5, 38]
    assert r["signal_scan"]["all_zero_vectors"] == 3


def test_unknown_signal_values_are_kept_but_flagged_uncertain(tmp_path):
    p = fx.build_cphd(tmp_path / "o.cphd", [dict(id="A", nv=32, ns=16, arc_deg=1.0)], signal_value_2=3)
    r = inspect_cphd(p, InspectOptions(**NOCHK))
    ap = r["channels"][0]["aperture"]
    assert ap["signal_status"]["counts"]["other"] == 1 and ap["signal_status"]["other_values"] == [2]
    assert ap["selection"]["count"] == 32
    caps = {c["capability"]: c["status"] for c in r["capabilities"]}
    assert caps["signal_status_semantics"] == "uncertain"


def test_nonfinite_sample_is_detected_by_the_scan(tmp_path):
    p = fx.build_cphd(tmp_path / "n.cphd", [dict(id="A", nv=32, ns=16, arc_deg=1.0)], nan_at=("A", 10, 3))
    s = inspect_cphd(p, InspectOptions(scan_signal=True, **NOCHK))["signal_scan"]
    assert s["nonfinite_samples"] == 1


def test_nonuniform_threshold_is_configurable(tmp_path):
    p = fx.build_cphd(tmp_path / "j.cphd", [dict(id="A", nv=64, ns=16, arc_deg=1.0)], jitter_frac=0.002)
    assert inspect_cphd(p, InspectOptions(**NOCHK))["channels"][0]["aperture"]["timing"]["nonuniform"] is True
    loose = inspect_cphd(p, InspectOptions(nonuniform_rtol=0.02, **NOCHK))
    assert loose["channels"][0]["aperture"]["timing"]["nonuniform"] is False


def test_scan_memory_is_bounded_by_the_budget_not_the_file(tmp_path):
    p = fx.build_cphd(tmp_path / "big.cphd", [dict(id="A", nv=2000, ns=1000, arc_deg=1.0)])  # 16 MB of signal
    r = inspect_cphd(p, InspectOptions(scan_signal=True, chunk_budget_bytes=2 * 2**20, measure_performance=True, **NOCHK))
    assert r["signal_scan"]["chunks"] > 1 and r["signal_scan"]["vectors_scanned"] == 2000
    assert r["performance"]["python_heap_peak_bytes"] < 8 * 2**20      # well below the 16 MB signal block


def test_inspection_without_scan_does_not_read_the_signal(tmp_path):
    p = fx.build_cphd(tmp_path / "big2.cphd", [dict(id="A", nv=2000, ns=1000, arc_deg=1.0)])
    r = inspect_cphd(p, InspectOptions(measure_performance=True, **NOCHK))
    assert "signal_scan" not in r and r["performance"]["python_heap_peak_bytes"] < 4 * 2**20


# ---- negative tests
def test_truncated_signal_block_is_a_controlled_error(tmp_path):
    p = fx.build_cphd(tmp_path / "t.cphd", [dict(id="A", nv=32, ns=16, arc_deg=1.0)])
    p.write_bytes(p.read_bytes()[:-1000])
    with pytest.raises(MalformedFileError, match="truncated|smaller"):
        inspect_cphd(p, InspectOptions(**NOCHK))


def test_unsupported_signal_format_is_reported(tmp_path):
    p = fx.build_cphd(tmp_path / "u.cphd", [dict(id="A", nv=32, ns=16, arc_deg=1.0)])
    raw = p.read_bytes()
    assert raw.count(b"<SignalArrayFormat>CF8<") == 1
    p.write_bytes(raw.replace(b"<SignalArrayFormat>CF8<", b"<SignalArrayFormat>ZZ9<"))
    with pytest.raises(UnsupportedFormatError, match="SignalArrayFormat"):
        inspect_cphd(p, InspectOptions(**NOCHK))


def test_duplicate_channel_ids_are_rejected(tmp_path):
    p = fx.build_cphd(tmp_path / "d.cphd", [dict(id="A", nv=32, ns=16, arc_deg=1.0), dict(id="B", nv=32, ns=16, arc_deg=1.0)])
    raw = p.read_bytes()
    p.write_bytes(raw.replace(b"<Identifier>B</Identifier>", b"<Identifier>A</Identifier>"))
    with pytest.raises(MalformedFileError, match="duplicate channel"):
        inspect_cphd(p, InspectOptions(**NOCHK))


def test_corrupted_xml_is_a_controlled_error(tmp_path):
    p = fx.build_cphd(tmp_path / "c.cphd", [dict(id="A", nv=32, ns=16, arc_deg=1.0)])
    raw = p.read_bytes()
    i = raw.index(b"<CPHD")
    p.write_bytes(raw[:i] + b"<<<<<" + raw[i + 5:])
    with pytest.raises(MalformedFileError):
        inspect_cphd(p, InspectOptions(**NOCHK))


def test_signal_offset_beyond_block_is_rejected(tmp_path):
    p = fx.build_cphd(tmp_path / "o2.cphd", [dict(id="A", nv=32, ns=16, arc_deg=1.0), dict(id="B", nv=32, ns=16, arc_deg=1.0)])
    raw = p.read_bytes()
    old = f"<SignalArrayByteOffset>{32 * 16 * 8}<".encode()
    assert raw.count(old) == 1
    p.write_bytes(raw.replace(old, f"<SignalArrayByteOffset>{32 * 16 * 8 + 9}<".encode()))
    with pytest.raises(MalformedFileError, match="beyond the SIGNAL block"):
        inspect_cphd(p, InspectOptions(**NOCHK))
