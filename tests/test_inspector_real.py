import hashlib
import json

import numpy as np
import pytest

pytestmark = pytest.mark.realdata
CATS = {"measured", "derived", "assumed", "unavailable"}


def walk_params(o, path=""):
    """Yield every provenance-tagged leaf dict in a report."""
    if isinstance(o, dict):
        if "provenance" in o and "source" in o:
            yield path, o
        else:
            for k, v in o.items():
                yield from walk_params(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_params(v, f"{path}[{i}]")


def test_format_and_file_identity(report):
    assert report["source"]["size_bytes"] == 616_837_024
    assert report["source"]["name"].endswith("_CPHD.cphd")
    assert report["format"]["version"]["value"] == "1.1.0"
    assert report["format"]["supported"] is True


def test_channel_dimensions_are_independently_confirmed(report):
    ch = report["channels"]
    assert len(ch) == 1
    c = ch[0]
    assert c["identifier"]["value"] == "Primary"
    assert c["num_vectors"]["value"] == 8780 and c["num_samples"]["value"] == 8747
    assert c["signal_dtype"]["value"] == ">c8"
    assert c["signal_bytes"]["value"] == 8780 * 8747 * 8


def test_domain_and_no_raw_waveform_claim(report):
    g = report["global"]
    assert g["domain"]["value"] == "FX" and g["sgn"]["value"] == -1
    assert g["collect_type"]["value"] == "MONOSTATIC"
    assert "transmitted_waveform_samples" in report["unavailable_by_design"]
    assert report["tx_waveform"]["samples_in_file"]["provenance"] == "unavailable"
    # metadata bandwidth is reported separately from the per-vector processing bandwidth
    assert "rf_bandwidth_metadata" in report["tx_waveform"]
    assert "pvp_union_bandwidth" in report["channels"][0]["frequency"]


def test_pvp_fields_listed(report):
    names = report["channels"][0]["pvp_fields"]
    for n in ("TxTime", "TxPos", "RcvPos", "SRPPos", "FX1", "FX2", "SIGNAL"):
        assert n in names


def test_every_reported_parameter_has_valid_provenance(report):
    leaves = list(walk_params(report))
    assert len(leaves) > 40
    for path, leaf in leaves:
        assert leaf["provenance"] in CATS, path
        assert leaf["source"], path
        if leaf["provenance"] == "unavailable":
            assert leaf["value"] is None, path


def test_full_aperture_is_default_and_complete(report):
    ap = report["channels"][0]["aperture"]
    sel = ap["selection"]
    assert sel["policy"] == "full" and sel["count"] == 8780 and sel["runs"] == [[0, 8780]]
    assert ap["vectors_total"] == 8780


def test_aperture_uses_actual_pvp_times(report):
    t = report["channels"][0]["aperture"]["timing"]
    assert t["count"] == 8780
    assert t["duration_s"] == pytest.approx(1.388486224 - 0.002747658666666667, rel=1e-9)
    assert t["non_monotonic_count"] == 0
    assert t["dt_median_s"] == pytest.approx(t["duration_s"] / 8779, rel=1e-3)


def test_geometry_is_self_consistent(report):
    a = report["channels"][0]["aperture"]
    tx = a["tx_trajectory"]
    # speed from the velocity PVP must agree with path length / duration
    assert tx["speed_mean_mps"] == pytest.approx(tx["path_length_m"] / a["timing"]["duration_s"], rel=0.01)
    ang = a["angular_span"]
    assert 0 < ang["first_last_deg"] <= ang["cumulative_deg"] * (1 + 1e-9)
    assert ang["first_last_deg"] <= ang["max_from_first_deg"] + 1e-9
    assert "ECF" in a["geometry_definition"]


def test_scene_extent_is_only_what_metadata_declares(report):
    a = report["channels"][0]["aperture"]
    assert a["image_area_metadata"]["provenance"] == "measured"
    assert "not resolution" in a["interpretation_note"]


def test_consistency_split_between_failed_inapplicable_and_passed(report):
    c = report["consistency"]
    assert c["ran"] is True and c["thorough"] is False
    assert c["total"] == c["passed"] + c["failed"] + c["inapplicable"]
    assert c["failed"] == 0 and c["failures"] == []
    assert c["inapplicable"] >= 1
    assert all(s["reason"] for s in c["inapplicable_checks"])


def test_signal_scan_covers_all_vectors_in_multiple_chunks(report):
    s = report["signal_scan"]
    assert s["vectors_scanned"] == 8780 and s["chunks"] > 1
    assert s["nonfinite_samples"] == 0
    assert s["max_abs"] > 0 and s["mean_power"] > 0


def test_signal_scan_matches_independent_sarkit_read(report, real_path):
    import sarkit.cphd as sc
    with open(real_path, "rb") as f:
        sig = sc.Reader(f).read_signal("Primary")
        ref = float(np.mean(np.abs(np.asarray(sig[:64], dtype=np.complex128)) ** 2))
    assert report["signal_scan"]["first_64_vectors_mean_power"] == pytest.approx(ref, rel=1e-9)


def test_report_is_json_serializable(report):
    json.dumps(report)


def test_input_file_is_never_modified(real_path, real_sha256):
    from sarsil.cphd.inspector import inspect_cphd, InspectOptions
    st = real_path.stat()
    inspect_cphd(real_path, InspectOptions(scan_signal=True))
    st2 = real_path.stat()
    assert (st.st_size, st.st_mtime_ns) == (st2.st_size, st2.st_mtime_ns)
    h = hashlib.sha256()
    with open(real_path, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    assert h.hexdigest() == real_sha256
