#!/usr/bin/env python3
"""Standalone launcher for the offline copy; uses only the standard library."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from webom.serve import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
