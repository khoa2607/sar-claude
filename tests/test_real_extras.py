import json

import pytest

from sarsil.cphd.inspector import InspectOptions, inspect_cphd

pytestmark = pytest.mark.realdata
STATUSES = {"supported", "unsupported", "uncertain", "not_evaluated"}


def test_capability_assessment_is_explicit(report):
    caps = {c["capability"]: c for c in report["capabilities"]}
    assert all(c["status"] in STATUSES and c["reason"] for c in caps.values())
    assert caps["tx_waveform_reconstruction"]["status"] == "unsupported"
    assert caps["multi_provider_compatibility"]["status"] == "not_evaluated"
    assert caps["image_formation_readiness"]["status"] == "not_evaluated"
    assert caps["fx_domain_inspection"]["status"] == "supported"
    assert caps["multi_channel_inspection"]["status"] == "uncertain"   # only one real channel exists


def test_pvp_availability_and_support_arrays(report):
    assert report["channels"][0]["pvp_availability"]["core_missing"] == []
    assert [(s["identifier"]["value"], s["num_rows"]["value"], s["num_cols"]["value"])
            for s in report["support_arrays"]] == [("Antenna", 201, 201), ("Antenna_element", 2, 2)]


def test_declared_reference_geometry_agrees_with_sarkit_recomputation(report):
    d = report["channels"][0]["aperture"]["reference_geometry_difference"]["value"]
    assert abs(d["SlantRange"]) < 0.01 and abs(d["GroundRange"]) < 0.01
    for k in ("AzimuthAngle", "GrazeAngle", "IncidenceAngle", "DopplerConeAngle"):
        assert abs(d[k]) < 1e-6


def test_signal_status_for_this_file(report):
    s = report["channels"][0]["aperture"]["signal_status"]
    assert s["counts"] == {"0": 0, "1": 8780, "other": 0} and s["signal_normal_consistent"] is True


def test_source_polarization_is_reported_unreconciled(report):
    p = report["channels"][0]["parameters"]
    assert (p["tx_pol"]["value"], p["rcv_pol"]["value"]) == ("X", "X")
    assert p["tx_pol"]["source"].startswith("XML:")
    text = json.dumps(report)
    assert '"VV"' not in text and "external" not in text.lower()


def test_real_report_is_deterministic_bytes(real_path):
    a = json.dumps(inspect_cphd(real_path), sort_keys=True)
    b = json.dumps(inspect_cphd(real_path), sort_keys=True)
    assert a == b


def test_real_inspection_never_allocates_the_signal(real_path):
    r = inspect_cphd(real_path, InspectOptions(measure_performance=True))
    assert r["performance"]["python_heap_peak_bytes"] < 64 * 2**20          # signal block is 614 MB


def test_real_scan_heap_follows_the_chunk_budget(real_path):
    r = inspect_cphd(real_path, InspectOptions(scan_signal=True, run_consistency=False,
                                               chunk_budget_bytes=8 * 2**20, measure_performance=True))
    assert r["signal_scan"]["vectors_scanned"] == 8780
    assert r["performance"]["python_heap_peak_bytes"] < 48 * 2**20
