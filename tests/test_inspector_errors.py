import os

import pytest

from sarsil.cphd.errors import MalformedFileError, UnsupportedFormatError, CphdError
from sarsil.cphd.inspector import inspect_cphd, InspectOptions

OPT = InspectOptions(run_consistency=False)


def test_missing_file(tmp_path):
    with pytest.raises(MalformedFileError, match="does not exist"):
        inspect_cphd(tmp_path / "nope.cphd", OPT)


def test_directory_is_rejected(tmp_path):
    with pytest.raises(MalformedFileError, match="not a regular file"):
        inspect_cphd(tmp_path, OPT)


def test_empty_file(tmp_path):
    p = tmp_path / "e.cphd"
    p.write_bytes(b"")
    with pytest.raises(MalformedFileError, match="empty"):
        inspect_cphd(p, OPT)


def test_random_bytes_are_not_cphd(tmp_path):
    p = tmp_path / "r.cphd"
    p.write_bytes(os.urandom(4096))
    with pytest.raises(MalformedFileError, match="not a CPHD"):
        inspect_cphd(p, OPT)


def test_old_version_is_unsupported_with_actionable_message(tmp_path):
    p = tmp_path / "old.cphd"
    p.write_bytes(b"CPHD/0.3\nXML_BLOCK_SIZE := 10\n\x0c\n" + b"x" * 100)
    with pytest.raises(UnsupportedFormatError, match=r"0\.3.*1\.0\.1.*1\.1\.0"):
        inspect_cphd(p, OPT)


def test_valid_magic_but_garbage_body_is_controlled(tmp_path):
    p = tmp_path / "g.cphd"
    p.write_bytes(b"CPHD/1.1.0\n" + b"garbage\n" * 50)
    with pytest.raises(CphdError):
        inspect_cphd(p, OPT)


@pytest.mark.realdata
def test_truncated_real_file_is_reported_not_crashed(real_path, tmp_path):
    p = tmp_path / "trunc.cphd"
    with open(real_path, "rb") as f:
        p.write_bytes(f.read(2 * 2**20))
    with pytest.raises(MalformedFileError, match="truncated|smaller"):
        inspect_cphd(p, OPT)
