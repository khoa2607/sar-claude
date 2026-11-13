import hashlib
from pathlib import Path

import pytest

REAL = Path(__file__).resolve().parents[1] / "cphd" / "2023-11-19-16-12-16_UMBRA-05_CPHD.cphd"


@pytest.fixture(scope="session")
def real_path():
    if not REAL.exists():
        pytest.skip("local Umbra CPHD not present")
    return REAL


@pytest.fixture(scope="session")
def real_sha256(real_path):
    h = hashlib.sha256()
    with open(real_path, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


@pytest.fixture(scope="session")
def report(real_path):
    from sarsil.cphd.inspector import inspect_cphd, InspectOptions
    return inspect_cphd(real_path, InspectOptions(scan_signal=True, chunk_budget_bytes=8 * 2**20))
