#!/usr/bin/env python3
"""Run the daily source-ingest, newspaper build and archive workflow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kobo_ingest import main

if __name__ == "__main__":
    raise SystemExit(main())
