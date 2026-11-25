# kobo-morning-paper: a daily newspaper EPUB

Every morning a fresh, dated EPUB newspaper is generated from source files collected throughout the previous day. The pipeline is reader-agnostic: it writes a local EPUB and can copy that edition into any number of configured output ingest folders.

![System design](preview.png)

This repo is the code behind that pipeline. You run it on your own server. Nothing here calls a hosted service except the sites you read and, optionally, your own LLM.

## How it works

1. **Collect sources throughout the day.** Any other service can drop a source file into the configured `source_ingest_dir`. The default is `<data_dir>/source-ingest`.
2. **Build at 3:00 AM.** The scheduled `scripts/kobo-ingest-build.py` takes a snapshot of the files in the input folder, adds their URLs/articles to the newspaper's existing article store, and runs the normal EPUB builder.
3. **Archive the batch.** Only after the build and all configured output publishing succeeds, the files from that snapshot are moved into `source_archive_dir/YYYY-MM-DD/`. Files arriving while a build is running are left for the next day's edition.
4. **Publish outputs.** The dated EPUB is copied atomically into every directory listed in `output_ingest_dirs`. These can be watched by any reader/library application; this project does not call any destination-specific API.

The source folder is separate from `output_ingest_dirs`: one is where other services put input data, the other is where the finished EPUB is delivered.

## Source file formats

The ingest runner accepts these files:

- **`.txt`, `.urls`, `.list`** — one HTTP(S) article URL per line. Blank lines and lines beginning with `#` are ignored.
- **`.json`** — a JSON array of URLs or article objects, or an object containing an `articles`, `items`, `urls`, `links`, or `data` array. A single article object can also be supplied.
- **`.jsonl`** — one URL string or article object per line.

A URL-only entry is fetched and extracted by the normal newspaper builder. An article object can include `url`, `title`, `published` (or `date`), `domain`, `image`, and pre-extracted `html` (or plain-text `content` / `text`). Providing article content skips the network fetch for that item.

Example JSON:
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

**Important for producers:** write files to a temporary filename and rename them into the input folder only when the file is complete. The runner snapshots the folder at startup; anything arriving after that snapshot is included in the next run. Unsupported or malformed files are not archived, and a failed build leaves the batch in place for retry.

## What you need

- A server that runs scheduled jobs
- Python 3.10 or newer
- Optional: output ingest folders belonging to your reader/library applications
- Optional: Audiobookshelf, Seerr/Overseerr, a media request log, TikTok collections, and Kickstarter IMAP access for interest signals

## Setup

1. **Install.**
   ```sh
   git clone https://github.com/joeShuff/kobo-morning-paper.git
   cd kobo-morning-paper
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
   `opencv-python-headless` and `numpy` are only for the lead-image face filter. `yt-dlp` is only for TikTok collections.

2. **Configure.** Copy `config.example.json` to `config.json`, then edit it:
   - `data_dir`: where the pipeline keeps the queue, cached articles, logs and generated EPUB.
   - `source_ingest_dir`: input folder where other services drop files. Defaults to `<data_dir>/source-ingest`.
   - `source_archive_dir`: where successfully processed source files are stored, in date-named subfolders. Defaults to `<data_dir>/source-archive`.
   - `output_ingest_dirs`: optional list of absolute paths where the finished EPUB is copied. Each folder must already exist and be writable. Use an empty list to keep the EPUB only in `data_dir`.

   Example:
   ```json
   {
     "data_dir": "/srv/morning-paper",
     "source_ingest_dir": "/srv/morning-paper/source-ingest",
     "source_archive_dir": "/srv/morning-paper/source-archive",
     "output_ingest_dirs": ["/srv/book-library/ingest"]
   }
   ```

   The dated EPUB filename is, for example, `the-morning-paper-2026-11-25.epub`. Its title and publication date metadata also include the edition date. Output copies use a temporary file and atomic rename, so a watcher cannot pick up a partially written EPUB. If an output destination fails, the run fails and the input source files remain available for retry.

   Scripts find the config through `KOBO_PAPER_CONFIG`, then `./config.json`, then the repo root. `config.json` is in `.gitignore`.

3. **Add source producers.** Configure your other services to write one of the supported formats into `source_ingest_dir`. They do not need to call this project or know about the newspaper build process.

4. **Run once by hand.**
   ```sh
   .venv/bin/python scripts/kobo-ingest-build.py
   ```
   The generated EPUB is at `<data_dir>/read-later.epub`; successful source files are moved to `<source_archive_dir>/YYYY-MM-DD/`. To run the lower-level builder against cached fixture articles without network access, use:
   ```sh
   .venv/bin/python scripts/kobo-digest-build.py --dry-build /path/to/test-data
   ```

5. **Schedule.** Add the 3:00 AM line from `crontab.example` to your cron table. The example also retains the optional interest-model job; it is independent of the source-file ingest workflow.

## Files

- `scripts/kobo-ingest-build.py`: daily source intake, build orchestration and archiving.
- `scripts/kobo_ingest.py`: source file parsing and staging helpers.
- `scripts/kobo-digest-build.py`: fetch, extract, build and publish the EPUB.
- `scripts/kobo-interests.py`: optional interest model.
- `scripts/kobo-queue.py`: URL intake helper for the legacy queue workflow.
- `scripts/kobo_config.py`: shared config loader and defaults.
- `tests/`, `fixtures/`: smoke tests using local fixture articles.

## Test

```sh
.venv/bin/python -m pytest
```

## Open-source parts

trafilatura, ebooklib, Pillow, yt-dlp.

## License

MIT
