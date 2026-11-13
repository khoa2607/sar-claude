import json

import pytest

from sarsil.cphd.cli import main


def test_missing_file_gives_exit_2_and_message(capsys, tmp_path):
    rc = main([str(tmp_path / "x.cphd")])
    assert rc == 2
    assert "does not exist" in capsys.readouterr().err


@pytest.mark.realdata
def test_cli_writes_json_and_short_summary(capsys, real_path, tmp_path):
    out = tmp_path / "r.json"
    rc = main([str(real_path), "--json", str(out), "--scan-signal"])
    text = capsys.readouterr().out
    assert rc == 0
    assert len(text.splitlines()) < 60
    d = json.loads(out.read_text())
    assert d["channels"][0]["num_vectors"]["value"] == 8780
    assert "8780" in text


@pytest.mark.realdata
def test_cli_subaperture_is_labelled(real_path, tmp_path):
    out = tmp_path / "s.json"
    assert main([str(real_path), "--json", str(out), "--no-consistency", "--subaperture", "0", "1000"]) == 0
    sel = json.loads(out.read_text())["channels"][0]["aperture"]["selection"]
    assert sel["policy"] == "subaperture" and sel["count"] == 1000
