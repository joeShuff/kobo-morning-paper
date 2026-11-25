"""Collect daily source files into the existing newspaper build pipeline."""
import hashlib
import html
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from kobo_config import CFG, DATA_DIR

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX = Path(CFG.get("source_ingest_dir") or (DATA_DIR / "source-ingest")).expanduser()
ARCHIVE = Path(CFG.get("source_archive_dir") or (DATA_DIR / "source-archive")).expanduser()
QUEUE = DATA_DIR / "queue.txt"
ARTICLES = DATA_DIR / "articles"
BUILDER = REPO_ROOT / "scripts" / "kobo-digest-build.py"


def _valid_url(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    parsed = urlparse(value)
    return value if parsed.scheme in ("http", "https") and parsed.netloc else None


def _article_record(item):
    """Return (url, article-cache-record) or (url, None) for a URL-only item."""
    if isinstance(item, str):
        url = _valid_url(item)
        if not url:
            raise ValueError(f"not an HTTP(S) URL: {item!r}")
        return url, None
    if not isinstance(item, dict):
        raise ValueError("source entries must be URL strings or article objects")
    url = _valid_url(item.get("url") or item.get("link"))
    if not url:
        raise ValueError("article object is missing a valid url")
    body = item.get("html") or item.get("content") or item.get("text")
    if body is None:
        return url, None
    if "html" not in item:
        body = "<p>" + html.escape(str(body)).replace("\\n", "</p><p>") + "</p>"
    domain = item.get("domain") or urlparse(url).netloc.replace("www.", "")
    record = {
        "url": url,
        "title": str(item.get("title") or url)[:200],
        "domain": str(domain),
        "published": str(item.get("published") or item.get("date") or date.today().isoformat()),
        "saved": str(item.get("saved") or datetime.now(timezone.utc).isoformat()),
        "image": item.get("image"),
        "html": str(body),
    }
    return url, record


def _flatten_payload(payload):
    if isinstance(payload, list):
        for item in payload:
            yield from _flatten_payload(item)
    elif isinstance(payload, dict) and not (payload.get("url") or payload.get("link")):
        found = False
        for key in ("articles", "items", "urls", "links", "data"):
            if key in payload:
                found = True
                yield from _flatten_payload(payload[key])
        if not found:
            raise ValueError("JSON object must contain url/link or an articles, items, urls, links, or data array")
    else:
        yield payload


def parse_source_file(path):
    """Parse .txt/.urls/.list, .json, or .jsonl source files."""
    suffix = path.suffix.lower()
    if suffix in (".txt", ".urls", ".list"):
        payload = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                   if line.strip() and not line.lstrip().startswith("#")]
    elif suffix == ".json":
        payload = _flatten_payload(json.loads(path.read_text(encoding="utf-8")))
    elif suffix == ".jsonl":
        payload = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                try:
                    payload.extend(_flatten_payload(json.loads(line)))
                except (ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"line {line_number}: {exc}") from exc
    else:
        raise ValueError(f"unsupported source file type: {suffix or '(no extension)'}")

    urls, records = [], []
    for item in payload:
        url, record = _article_record(item)
        urls.append(url)
        if record:
            records.append(record)
    return urls, records


def collect_sources(files):
    """Stage all selected source files; return the URLs and number of cached articles."""
    urls, records = [], []
    for path in files:
        file_urls, file_records = parse_source_file(path)
        urls.extend(file_urls)
        records.extend(file_records)

    # Append URLs without clobbering anything already queued by another source.
    existing = QUEUE.read_text(encoding="utf-8").splitlines() if QUEUE.exists() else []
    seen = {line.strip() for line in existing if line.strip() and not line.lstrip().startswith("#")}
    new_urls = [url for url in dict.fromkeys(urls) if url not in seen]
    if new_urls:
        with QUEUE.open("a", encoding="utf-8") as queue:
            if existing and not existing[-1].endswith("\\n"):
                queue.write("\\n")
            queue.write("".join(url + "\\n" for url in new_urls))

    ARTICLES.mkdir(parents=True, exist_ok=True)
    cached = 0
    for record in records:
        name = hashlib.sha1(record["url"].encode()).hexdigest()[:16] + ".json"
        target = ARTICLES / name
        if not target.exists():
            target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            cached += 1
    return len(new_urls), cached


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
        files = sorted(p for p in INBOX.iterdir() if p.is_file() and not p.name.startswith("."))
        if not files:
            print(f"No source files in {INBOX}; running the normal builder for any queued/cached articles.")
        else:
            added_urls, cached_articles = collect_sources(files)
            print(f"Collected {len(files)} source file(s): {added_urls} new URL(s), {cached_articles} cached article(s).")

        result = subprocess.run([sys.executable, str(BUILDER)], cwd=REPO_ROOT)
        if result.returncode != 0:
            print("Newspaper build failed; source files have been left in the input folder for retry.", file=sys.stderr)
            return result.returncode

        if files:
            override = os.environ.get("KOBO_DATELINE_DATE")
            archive_date = override or date.today().isoformat()
            moved = archive_sources(files, archive_date)
            print(f"Archived {len(moved)} source file(s) to {ARCHIVE / archive_date}")
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
