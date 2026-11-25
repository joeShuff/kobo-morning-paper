# kobo-morning-paper: a daily newspaper EPUB

A small, self-hosted pipeline that turns prepared article sources into a dated EPUB newspaper. Other programs are responsible for discovering, selecting and preparing content; this project consumes their files, builds the newspaper and publishes it.

There is no built-in AI, interest model, source discovery, or integration with Audiobookshelf, Seerr, TikTok or Kickstarter.

## How it works

1. **Receive sources.** Other programs write source files into `source_ingest_dir`.
2. **Read and stage.** At the scheduled run, the ingest runner snapshots the inbox and parses supported files. URL-only entries are fetched and extracted with Trafilatura; entries containing article text or HTML are used directly.
3. **Build the edition.** The existing article store is combined with the newly supplied content, filtered by the configured age limit, and rendered into a dated EPUB with a generated cover and tappable front page.
4. **Publish.** The dated EPUB is copied atomically into each configured `output_ingest_dirs` destination.
5. **Archive inputs.** After the build and all output publishing succeed, the source files from that run are moved into `source_archive_dir/YYYY-MM-DD/`. Files arriving during a run are left for the next edition.

The source inbox is input. `output_ingest_dirs` are destinations for the finished EPUB.

## Source file formats

- **`.txt`, `.urls`, `.list`** — one HTTP(S) article URL per line. Blank lines and lines beginning with `#` are ignored.
- **`.json`** — an array of URLs/article objects, a single article object, or an object containing an `articles`, `items`, `urls`, `links`, or `data` array.
- **`.jsonl`** — one URL string or article object per line.

An article object can include `url` (or `link`), `title`, `published` (or `date`), `domain`, `image`, and pre-extracted `html` or plain-text `content`/`text`. If article content is supplied, the generator does not fetch that URL.

Example:
```json
{
  "articles": [
    {"url": "https://example.com/story", "title": "A story"},
    {
      "url": "https://example.com/another-story",
      "title": "Another story",
      "published": "2026-11-25",
      "text": "The already extracted article text."
    }
  ]
}
```

**For producers:** write to a temporary filename and rename it into the inbox only when complete. The runner snapshots the inbox at startup. Unsupported or malformed files are left in place and reported; source files are archived only after the EPUB build and publishing succeed.

## Configuration

Copy `config.example.json` to `config.json`. All settings have defaults; the only settings most deployments need to change are:

- `data_dir`: persistent working directory for the article cache, logs and generated EPUB.
- `source_ingest_dir`: inbox for source files. Defaults to `<data_dir>/source-ingest`.
- `source_archive_dir`: dated archive for processed source files. Defaults to `<data_dir>/source-archive`.
- `output_ingest_dirs`: optional list of existing, writable folders where the finished EPUB is copied.
- `paper_title` and `paper_tagline`: newspaper branding.
- `max_age_days`: exclude older cached/source articles from the edition. Set to a suitably high value if upstream producers already manage freshness.

Example:
```json
{
  "data_dir": "/srv/morning-paper",
  "source_ingest_dir": "/srv/morning-paper/source-ingest",
  "source_archive_dir": "/srv/morning-paper/source-archive",
  "output_ingest_dirs": ["/srv/book-library/ingest"]
}
```

Fonts and the optional lead-image face filter are presentation settings, not source integrations. Secrets and third-party service credentials are not needed.

## Run locally

```sh
git clone https://github.com/joeShuff/kobo-morning-paper.git
cd kobo-morning-paper
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.example.json config.json
.venv/bin/python scripts/kobo-ingest-build.py
```

The generated EPUB is `<data_dir>/read-later.epub`. Add the 03:00 entry from `crontab.example` to run it daily. To build from cached fixture articles without network access, use:

```sh
.venv/bin/python scripts/kobo-digest-build.py --dry-build /path/to/test-data
```

## Docker deployment

The image runs its own scheduler at 03:00 local container time. It catches up after downtime and retries failed builds every 15 minutes.

```sh
git clone https://github.com/joeShuff/kobo-morning-paper.git newspaper
cd newspaper
mkdir -p data
cp config.docker.example.json config.json
docker compose up -d --build
docker compose logs -f newspaper
```

Drop source files into `./data/source-ingest` on the host. Working data, article cache, generated EPUB and dated archives persist under `./data`.

A producer container can mount the same inbox:
```yaml
volumes:
  - /path/to/newspaper/data/source-ingest:/newspaper-ingest
```

If another application should receive the EPUB, mount its ingest folder into this container and set the container-side path in `output_ingest_dirs`. The Compose file uses `TZ=Europe/London` by default; change it to adjust the schedule timezone.

To trigger a build manually:
```sh
docker compose run --rm newspaper python scripts/kobo-ingest-build.py
```

## Tests

```sh
.venv/bin/python -m pytest
```

## Main components

- `scripts/kobo-ingest-build.py`: daily source intake, build orchestration and archiving.
- `scripts/kobo_ingest.py`: source file parsing and staging helpers.
- `scripts/kobo-digest-build.py`: fetch, extract, render, and publish the EPUB.
- `scripts/kobo_config.py`: small configuration loader.

## License

MIT
