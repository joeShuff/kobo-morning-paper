"""Snapshot plain-text sources, generate articles with an AI editor, build and archive."""
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

from kobo_config import CFG, DATA_DIR

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX = Path(CFG.get("source_ingest_dir") or (DATA_DIR / "source-ingest")).expanduser()
ARCHIVE = Path(CFG.get("source_archive_dir") or (DATA_DIR / "source-archive")).expanduser()
BUILDER = REPO_ROOT / "scripts" / "kobo-digest-build.py"


def _is_companion(path):
    return path.name.endswith(".context.txt") or path.name.endswith(".expected.txt")


def archive_sources(files, archive_date):
    destination = ARCHIVE / archive_date
    destination.mkdir(parents=True, exist_ok=True)
    moved = []
    for source in files:
        if not source.exists():
            continue
        target = destination / source.name
        if target.exists():
            stamp = datetime.now().strftime("%H%M%S%f")
            target = destination / f"{source.stem}-{stamp}{source.suffix}"
        shutil.move(str(source), str(target))
        moved.append(target)
    return moved


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INBOX.mkdir(parents=True, exist_ok=True)
    lock = DATA_DIR / ".source-ingest-build.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        print(f"Another ingest build is already running ({lock})", file=sys.stderr)
        return 1
    os.close(fd)

    try:
        # Snapshot once: files arriving after this point belong to the next edition.
        files = sorted(
            path for path in INBOX.iterdir()
            if path.is_file() and not path.name.startswith(".")
        )
        source_files = [path for path in files if not _is_companion(path)]

        if source_files:
            # Import only when needed so a legacy queue-only build does not require
            # AI configuration or a reachable model endpoint.
            from kobo_ai import AIError, generate_articles
            try:
                # Copy the startup snapshot, including any companion files, so files
                # arriving or changing during the AI request are deferred to next run.
                with tempfile.TemporaryDirectory(prefix=".source-snapshot-", dir=DATA_DIR) as temp_dir:
                    snapshot_dir = Path(temp_dir)
                    for path in files:
                        shutil.copy2(path, snapshot_dir / path.name)
                    snapshot_sources = [snapshot_dir / path.name for path in source_files]
                    articles, edition = generate_articles(snapshot_sources)
            except AIError as exc:
                print(f"AI editorial step failed: {exc}", file=sys.stderr)
                return 1
            print(
                f"AI editor generated {len(articles)} article(s) from "
                f"{len(source_files)} source file(s)."
            )
            if edition.get("headline"):
                print(f"Edition headline suggestion: {edition['headline']}")
        elif files:
            print("Only context/expected-output sidecars were found; no source text to process.")
            return 1
        else:
            print(f"No source files in {INBOX}; building from any existing queued or cached articles.")

        result = subprocess.run([sys.executable, str(BUILDER)], cwd=REPO_ROOT)
        if result.returncode != 0:
            print("Newspaper build failed; source files have been left in the input folder for retry.", file=sys.stderr)
            return result.returncode

        if files:
            override = os.environ.get("KOBO_DATELINE_DATE")
            archive_date = override or date.today().isoformat()
            moved = archive_sources(files, archive_date)
            print(f"Archived {len(moved)} source/sidecar file(s) to {ARCHIVE / archive_date}")
        return 0
    except Exception as exc:
        print(f"Source ingest failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
