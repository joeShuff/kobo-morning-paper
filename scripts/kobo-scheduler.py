#!/usr/bin/env python3
"""Keep the container alive and run the daily build at a configurable local time."""
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from kobo_config import DATA_DIR

RUNNER = ROOT / "scripts" / "kobo-ingest-build.py"
SCHEDULE_TIME = os.getenv("KOBO_SCHEDULE_TIME", "03:00")
RETRY_MINUTES = int(os.getenv("KOBO_SCHEDULER_RETRY_MINUTES", "15"))
POLL_SECONDS = int(os.getenv("KOBO_SCHEDULER_POLL_SECONDS", "20"))
LAST_SUCCESS = DATA_DIR / ".last-successful-build-date"


def scheduled_time():
    try:
        parsed = datetime.strptime(SCHEDULE_TIME, "%H:%M")
    except ValueError as exc:
        raise ValueError("KOBO_SCHEDULE_TIME must use 24-hour HH:MM format (for example 03:00)") from exc
    return parsed.hour, parsed.minute


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

    try:
        run_hour, run_minute = scheduled_time()
        if RETRY_MINUTES < 1 or POLL_SECONDS < 1:
            raise ValueError("KOBO_SCHEDULER_RETRY_MINUTES and KOBO_SCHEDULER_POLL_SECONDS must be positive")
    except ValueError as exc:
        print(f"[scheduler] Configuration error: {exc}", file=sys.stderr, flush=True)
        return 2

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    completed_date = read_last_success()
    print(
        f"[scheduler] Waiting for {run_hour:02d}:{run_minute:02d} local time each day",
        flush=True,
    )
    print(f"[scheduler] Timezone: {datetime.now().astimezone().tzinfo}", flush=True)
    retry_after = None

    while True:
        now = datetime.now().astimezone()
        due = now.replace(hour=run_hour, minute=run_minute, second=0, microsecond=0)

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
                    retry_after = datetime.now().astimezone() + timedelta(minutes=RETRY_MINUTES)
                    print(f"[scheduler] Build failed; will retry in {RETRY_MINUTES} minutes.", flush=True)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
