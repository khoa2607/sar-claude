import json
from pathlib import Path

import pytest

from sarsil.cphd.errors import MalformedFileError
from sarsil.sicd.inspector import inspect_sicd

SICD = Path(__file__).resolve().parents[1] / "cphd" / "2023-11-19-16-12-16_UMBRA-05_SICD.nitf"
CATS = {"measured", "derived", "assumed", "unavailable"}


def test_missing_file(tmp_path):
    with pytest.raises(MalformedFileError, match="does not exist"):
        inspect_sicd(tmp_path / "x.nitf")


def test_empty_file(tmp_path):
    p = tmp_path / "e.nitf"
    p.write_bytes(b"")
    with pytest.raises(MalformedFileError, match="empty"):
        inspect_sicd(p)


def test_non_nitf_bytes(tmp_path):
    p = tmp_path / "r.nitf"
    p.write_bytes(b"not a nitf" * 100)
    with pytest.raises(MalformedFileError, match="not a NITF"):
        inspect_sicd(p)


@pytest.fixture(scope="module")
def rep():
    if not SICD.exists():
        pytest.skip("local SICD not present")
    return inspect_sicd(SICD)


def leaves(o, path=""):
    if isinstance(o, dict):
        if "provenance" in o and "source" in o:
            yield path, o
        else:
            for k, v in o.items():
                yield from leaves(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{path}[{i}]")


@pytest.mark.realdata
def test_image_and_grid_facts(rep):
    assert rep["source"]["size_bytes"] == 215_757_674
    assert rep["format"]["sicd_version"]["value"] == "1.2.1"
    im = rep["image"]
    assert (im["num_rows"]["value"], im["num_cols"]["value"]) == (5045, 5345)
    assert im["pixel_type"]["value"] == "RE32F_IM32F"
    assert (im["scp_pixel_row"]["value"], im["scp_pixel_col"]["value"]) == (2513, 2667)
    g = rep["grid"]
    assert g["type"]["value"] == "RGAZIM" and g["image_plane"]["value"] == "SLANT"
    assert g["row_ss_m"]["value"] == pytest.approx(0.5265507301753968)
    assert g["col_ss_m"]["value"] == pytest.approx(0.8889602541742135)


@pytest.mark.realdata
def test_formation_and_unavailable_weighting(rep):
    f = rep["formation"]
    assert f["algorithm"]["value"] == "PFA"
    assert f["az_autofocus"]["value"] == "NO" and f["rg_autofocus"]["value"] == "NO"
    assert any("RFI" in s["value"] for s in f["processing_steps"])
    assert rep["grid"]["row_weighting"]["provenance"] == "unavailable"
    assert rep["grid"]["col_weighting"]["provenance"] == "unavailable"


@pytest.mark.realdata
def test_frequency_timeline_geometry(rep):
    assert rep["frequency"]["tx_min_hz"]["value"] == pytest.approx(9465727102.942764)
    assert rep["timeline"]["ipp_start"]["value"] == 0 and rep["timeline"]["ipp_end"]["value"] == 8779
    assert rep["geodata"]["scp_ecf_m"]["value"][0] == pytest.approx(-552223.3276367188)
    assert rep["scpcoa"]["slant_range_m"]["value"] == pytest.approx(649078.6456362829)


@pytest.mark.realdata
def test_consistency_and_provenance_and_determinism(rep):
    c = rep["consistency"]
    assert c["ran"] is True and c["failed"] == 0 and c["total"] == c["passed"] + c["failed"] + c["inapplicable"]
    ls = list(leaves(rep))
    assert len(ls) > 30
    for path, leaf in ls:
        assert leaf["provenance"] in CATS and leaf["source"], path
        if leaf["provenance"] == "unavailable":
            assert leaf["value"] is None, path
    assert json.dumps(rep, sort_keys=True) == json.dumps(inspect_sicd(SICD), sort_keys=True)


@pytest.mark.realdata
def test_polarization_is_reported_as_stated_in_the_sicd(rep):
    assert rep["waveform"]["tx_polarization"]["value"] == "OTHER"
    assert "VV" not in json.dumps(rep)
