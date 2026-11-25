#!/usr/bin/env python3
"""Keep the container alive and run the daily build at 03:00 local time."""
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "kobo-ingest-build.py"
RUN_AT_HOUR = 3
RUN_AT_MINUTE = 0


def run_build() -> int:
    print(f"[scheduler] Starting daily newspaper build at {datetime.now().astimezone().isoformat()}", flush=True)
    result = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT)
    print(f"[scheduler] Build finished with exit code {result.returncode}", flush=True)
    return result.returncode


def main() -> int:
    if "--run-now" in sys.argv[1:]:
        return run_build()

    print(
        f"[scheduler] Waiting for {RUN_AT_HOUR:02d}:{RUN_AT_MINUTE:02d} local time each day",
        flush=True,
    )
    completed_date = None
    retry_after = None

    while True:
        now = datetime.now().astimezone()
        due = now.replace(hour=RUN_AT_HOUR, minute=RUN_AT_MINUTE, second=0, microsecond=0)

        # Run once the scheduled time has passed. This also catches up after a
        # container restart later in the day instead of silently missing an edition.
        if now >= due and completed_date != now.date():
            if retry_after is None or now >= retry_after:
                result = run_build()
                if result == 0:
                    completed_date = now.date()
                    retry_after = None
                else:
                    retry_after = datetime.now().astimezone() + timedelta(minutes=15)
                    print("[scheduler] Build failed; will retry in 15 minutes.", flush=True)

        time.sleep(20)


if __name__ == "__main__":
    raise SystemExit(main())
