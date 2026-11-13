import json
from pathlib import Path

import pytest

from sarsil.compare.cphd_sicd import compare_cphd_sicd

ROOT = Path(__file__).resolve().parents[1] / "cphd"
CPHD = ROOT / "2023-11-19-16-12-16_UMBRA-05_CPHD.cphd"
SICD = ROOT / "2023-11-19-16-12-16_UMBRA-05_SICD.nitf"
pytestmark = [pytest.mark.realdata, pytest.mark.skipif(not (CPHD.exists() and SICD.exists()), reason="local data absent")]
STATUS = {"within_tolerance", "exceeds_tolerance", "informational"}


@pytest.fixture(scope="module")
def cmp():
    return compare_cphd_sicd(CPHD, SICD)


def row(cmp, rid):
    return next(r for r in cmp["rows"] if r["id"] == rid)


def test_every_row_states_its_tolerance_basis_and_a_valid_status(cmp):
    ids = [r["id"] for r in cmp["rows"]]
    assert len(ids) == len(set(ids)) and len(ids) >= 20
    for r in cmp["rows"]:
        assert r["status"] in STATUS and r["tolerance_basis"], r["id"]
        if r["status"] != "informational":
            assert r["tolerance"] is not None and r["difference"] is not None, r["id"]


def test_status_is_consistent_with_difference_and_tolerance(cmp):
    for r in cmp["rows"]:
        if r["status"] == "informational":
            continue
        ok = abs(r["difference"]) <= r["tolerance"]
        assert (r["status"] == "within_tolerance") == ok, r["id"]


def test_summary_counts_add_up(cmp):
    s = cmp["summary"]
    assert s["total"] == len(cmp["rows"]) == s["within_tolerance"] + s["exceeds_tolerance"] + s["informational"]
    assert cmp["tolerances"]["geometry_m"] == pytest.approx(0.5900147166795388)   # finest SICD ImpRespWid


def test_positions_frequencies_counts_and_waveform_match(cmp):
    for rid in ("scp_vs_iarp_ecf_m", "scp_vs_srp_pvp_ecf_m", "area_corners_max_m", "tx_freq_min_hz", "tx_freq_max_hz",
                "num_vectors", "tx_pulse_length_s", "tx_rf_bandwidth_hz", "tx_fm_rate_hz_per_s", "adc_sample_rate_hz",
                "rcv_window_length_s", "collect_start"):
        assert row(cmp, rid)["status"] == "within_tolerance", rid


def test_time_axes_are_related_by_the_one_way_delay_and_the_cod_time(cmp):
    # SICD time = CPHD transmit time + SlantRange/c (undocumented relation; tested as a numerical hypothesis)
    assert row(cmp, "sicd_start_minus_cphd_start_s_vs_slant_range_over_c")["status"] == "within_tolerance"
    assert row(cmp, "sicd_center_time_vs_cphd_srp_cod_time_s")["status"] == "within_tolerance"
    assert row(cmp, "aperture_duration_s")["status"] == "within_tolerance"


def test_polar_angle_span_agrees_with_cphd_line_of_sight_span(cmp):
    r = row(cmp, "angular_span_deg")
    assert r["status"] == "within_tolerance" and 0.9 < r["cphd"] < 1.0


def test_polarization_is_listed_side_by_side_without_reconciliation(cmp):
    r = row(cmp, "polarization_strings")
    assert r["status"] == "informational"
    assert r["cphd"] == ["X", "X"] and r["sicd"] == ["OTHER", "OTHER"]
    assert "VV" not in json.dumps(cmp)


def test_processing_differences_are_listed(cmp):
    r = row(cmp, "sicd_processing_steps")
    assert any("RFI" in s for s in r["sicd"]) and r["status"] == "informational"


def test_report_is_deterministic(cmp):
    assert json.dumps(cmp, sort_keys=True) == json.dumps(compare_cphd_sicd(CPHD, SICD), sort_keys=True)


def test_arp_offset_is_explained_by_the_reference_time_offset(cmp):
    # Post-hoc explanation (identified after seeing the exceedances): offset ~ platform speed x time offset.
    r = row(cmp, "arp_offset_vs_speed_times_time_offset_m")
    assert r["status"] == "informational" and "post-hoc" in r["note"]
    assert r["cphd"] == pytest.approx(r["sicd"], rel=0.01)
    assert row(cmp, "arp_position_ecf_m")["status"] == "exceeds_tolerance"   # reported, not hidden
