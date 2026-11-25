# kobo-morning-paper: a daily newspaper EPUB

A small, self-hosted pipeline that turns prepared article sources into a dated EPUB newspaper. Other programs are responsible for discovering, selecting and preparing content; this project consumes their files, builds the newspaper and publishes it.

There is no built-in AI, interest model, source discovery, or integration with Audiobookshelf, Seerr, TikTok or Kickstarter.

## How it works

1. **Receive sources.** Other programs write source files into the source inbox.
2. **Read and stage.** At the scheduled run, the ingest runner snapshots the inbox and parses supported files. URL-only entries are fetched and extracted with Trafilatura; entries containing article text or HTML are used directly.
3. **Build the edition.** The existing article store is combined with the newly supplied content, filtered by the configured age limit, and rendered into a dated EPUB with a generated cover and tappable front page.
4. **Publish.** The dated EPUB is copied atomically into each configured output ingest destination.
5. **Archive inputs.** After the build and all output publishing succeed, the source files from that run are moved into the dated source archive. Files arriving during a run are left for the next edition.

The source inbox is input. Output ingest directories are destinations for the finished EPUB.

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

## Environment variables

There is no configuration file. Every setting is an environment variable with a built-in default. In Docker Compose, values can be supplied in a `.env` file next to `compose.yaml`; Compose automatically reads it. Start with:

```sh
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `TZ` | `Europe/London` | Container timezone; controls local scheduling and edition dates. |
| `KOBO_SCHEDULE_TIME` | `03:00` | Daily scheduler time, 24-hour `HH:MM`. |
| `KOBO_DATA_DIR` | `/data` | Persistent working directory for queue, cache, logs and EPUB. |
| `KOBO_SOURCE_INGEST_DIR` | `/data/source-ingest` | Inbox for source files. |
| `KOBO_SOURCE_ARCHIVE_DIR` | `/data/source-archive` | Processed source files, archived under a date folder. |
| `KOBO_OUTPUT_INGEST_DIRS` | *(empty)* | Comma-separated list of existing output folders for the finished EPUB. |
| `KOBO_PAPER_TITLE` | `The Morning Paper` | Newspaper title. |
| `KOBO_PAPER_TAGLINE` | `All the Reads Worth Your Time` | Cover/front-page tagline. |
| `KOBO_MAX_AGE_DAYS` | `7` | Exclude articles older than this many days. |
| `KOBO_FONTS_DIR` | `fonts` | Font directory; relative paths are resolved under the data directory. |
| `KOBO_MASTHEAD_FONT` | `UnifrakturMaguntia-Book.ttf` | Masthead font filename. |
| `KOBO_SERIF_BOLD_FONT` | `PT_Serif-Web-Bold.ttf` | Bold serif font filename. |
| `KOBO_SERIF_REGULAR_FONT` | `PT_Serif-Web-Regular.ttf` | Regular serif font filename. |
| `KOBO_LEAD_IMAGE_AVOID_FACES` | `true` | Skip prominent faces when choosing lead/front-page images. |
| `KOBO_SCHEDULER_RETRY_MINUTES` | `15` | Minutes between retries after a failed scheduled build. |
| `KOBO_SCHEDULER_POLL_SECONDS` | `20` | How often the scheduler checks whether the build is due. |

`KOBO_OUTPUT_INGEST_DIRS` accepts comma-separated container paths, for example `/output/bookorbit,/output/another-library`. Each destination must already exist and be writable. If the value is empty, the EPUB remains in `KOBO_DATA_DIR`.

The schedule runs in the timezone selected by `TZ`. For example, set `TZ=Europe/London` and `KOBO_SCHEDULE_TIME=04:15` to run at 4:15am UK local time, including daylight-saving changes.

## Run locally

```sh
git clone https://github.com/joeShuff/kobo-morning-paper.git
cd kobo-morning-paper
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
KOBO_DATA_DIR="$PWD/data" .venv/bin/python scripts/kobo-ingest-build.py
```

The generated EPUB is `<KOBO_DATA_DIR>/read-later.epub`. For local scheduling, use your system cron with the example in `crontab.example`; the built-in scheduler is used by Docker.

To build from cached fixture articles without network access:

```sh
.venv/bin/python scripts/kobo-digest-build.py --dry-build /path/to/test-data
```

## Docker deployment

The container runs its own scheduler, catches up after downtime and retries failed builds. The default schedule is 03:00 Europe/London.

```sh
git clone https://github.com/joeShuff/kobo-morning-paper.git newspaper
cd newspaper
mkdir -p data
cp .env.example .env
docker compose up -d --build
docker compose logs -f newspaper
```

Drop source files into `./data/source-ingest` on the host. Working data, article cache, generated EPUB and dated archives persist under `./data`.

A producer container can mount the same inbox:

```yaml
volumes:
  - /path/to/newspaper/data/source-ingest:/newspaper-ingest
```

To publish the EPUB to another application, mount its ingest folder into this container and add the container-side mount path to `KOBO_OUTPUT_INGEST_DIRS` in `.env`:

```yaml
volumes:
  - /path/to/bookorbit/ingest:/output/bookorbit
```

To trigger a build manually:

```sh
docker compose run --rm newspaper python scripts/kobo-ingest-build.py
```

## Tests

```sh
.venv/bin/python -m pytest
```

## Main components

- `scripts/kobo-ingest-build.py`: source intake, build orchestration and archiving.
- `scripts/kobo_ingest.py`: source file parsing and staging helpers.
- `scripts/kobo-digest-build.py`: fetch, extract, render, and publish the EPUB.
- `scripts/kobo_config.py`: environment-variable loader and defaults.

## License

MIT
