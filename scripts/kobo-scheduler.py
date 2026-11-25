#!/usr/bin/env python3
"""Keep the container alive and run the daily build at 03:00 local time."""
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from kobo_config import DATA_DIR

RUNNER = ROOT / "scripts" / "kobo-ingest-build.py"
RUN_AT_HOUR = 3
RUN_AT_MINUTE = 0
LAST_SUCCESS = DATA_DIR / ".last-successful-build-date"


def run_build() -> int:
    print(f"[scheduler] Starting daily newspaper build at {datetime.now().astimezone().isoformat()}", flush=True)
    result = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT)
    print(f"[scheduler] Build finished with exit code {result.returncode}", flush=True)
    return result.returncode


def read_last_success():
    try:
        return datetime.strptime(LAST_SUCCESS.read_text(encoding="utf-8").strip(), "%Y-%m-%d").date()
    except (OSError, ValueError):
        return None


def main() -> int:
    if "--run-now" in sys.argv[1:]:
        return run_build()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    completed_date = read_last_success()
    print(
        f"[scheduler] Waiting for {RUN_AT_HOUR:02d}:{RUN_AT_MINUTE:02d} local time each day",
        flush=True,
    )
    retry_after = None

    while True:
        now = datetime.now().astimezone()
        due = now.replace(hour=RUN_AT_HOUR, minute=RUN_AT_MINUTE, second=0, microsecond=0)

        # Run once the scheduled time has passed. Persist success so a container
        # restart does not generate the same edition again. Also catches up if
        # the container was stopped at the scheduled time.
        if now >= due and completed_date != now.date():
            if retry_after is None or now >= retry_after:
                result = run_build()
                if result == 0:
                    completed_date = now.date()
                    try:
                        LAST_SUCCESS.write_text(completed_date.isoformat(), encoding="utf-8")
                    except OSError as exc:
                        print(f"[scheduler] Could not persist completion date: {exc}", flush=True)
                    retry_after = None
                else:
                    retry_after = datetime.now().astimezone() + timedelta(minutes=15)
                    print("[scheduler] Build failed; will retry in 15 minutes.", flush=True)

        time.sleep(20)


if __name__ == "__main__":
    raise SystemExit(main())
