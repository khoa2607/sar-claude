"""Launcher for the read-only CPHD inspector (no package install needed).

    .venv\\Scripts\\python.exe scripts\\inspect_cphd.py cphd\\<file>.cphd [--scan-signal] [--thorough] [--hash]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sarsil.cphd.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
