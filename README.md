# kobo-morning-paper: a daily newspaper EPUB

Every morning a fresh, dated EPUB of about 10 articles is generated. The pipeline is reader-agnostic: it writes a local EPUB and can copy that edition into any number of configured output ingest folders.

![System design](preview.png)

This repo is the code behind that pipeline. You run it on your own server. Nothing here calls a hosted service except the sites you read and, optionally, your own LLM.

## How it works

1. **Interest model** (`scripts/kobo-interests.py`, 5:15 AM) reads optional sources and writes `interests.json`.
   - Reading activity 35%: Audiobookshelf progress from the last 30 days.
   - Media requests 30%: titles you asked your server to fetch (a JSONL log and/or Seerr/Overseerr requests).
   - Genres 20%: your standing genres from `config.json`.
   - TikTok 10%: public TikTok collections, read with yt-dlp.
   - Kickstarter 5%: backed projects, at most one item, read-only over IMAP.
   - If an optional source fails, its weight moves to Reading activity and Media requests (35:30), and `interests.json` says why.
2. **Curation** (5:30 AM): an LLM reads `interests.json` and picks about 10 article URLs into `queue.txt`. This step is **yours to plug in**. See `curate.example.sh` for the contract. No curation agent ships in this repo.
3. **Fetch + extract** (`scripts/kobo-digest-build.py`, 6:00 AM): trafilatura turns each URL into clean article text and stores it under `articles/`.
4. **Build edition**: ebooklib writes a dated EPUB, newest first, one chapter per article, with a generated cover and tappable front page.
5. **Publish outputs**: the dated EPUB is copied atomically into every directory listed in `output_ingest_dirs`. The folders can belong to any application that watches an ingest directory; this project does not call any destination-specific API.

`scripts/kobo-queue.py` is a small intake helper. It reads a message, finds lines that look like `kobo: https://...`, and appends them to `queue.txt`. Anything that can run a command can feed it (a chat bot, an SSH shortcut).

## What you need

- A server that runs scheduled jobs
- Python 3.10 or newer
- An LLM, or any tool, for the curation step
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
   - `data_dir`: where the pipeline keeps `queue.txt`, `articles/`, `interests.json`, logs and the generated EPUB.
   - `paper_title`, `paper_tagline`: printed on the cover and front page.
   - `output_ingest_dirs`: a list of absolute paths to output ingest folders. Each folder must already exist and be writable by the pipeline process. Use an empty list to keep the EPUB only in `data_dir`.

   Example:
   ```json
   {
     "data_dir": "/srv/morning-paper",
     "paper_title": "The Morning Paper",
     "output_ingest_dirs": [
       "/srv/book-library/ingest",
       "/srv/another-reader/import"
     ]
   }
   ```

   The same dated filename is copied to each destination, for example `the-morning-paper-2026-11-24.epub`. The EPUB title and publication date metadata also include the edition date. Copies use a temporary file and atomic rename, so an ingest scanner cannot pick up a partially written EPUB. If any configured folder is missing or cannot be written, the run reports failure and retains `queue.txt` so publishing can be retried.

   Scripts find the config through `KOBO_PAPER_CONFIG`, then `./config.json`, then the repo root. `config.json` is in `.gitignore`.

   For Kickstarter, set `KOBO_IMAP_USER` and `KOBO_IMAP_PASSWORD` in the environment. The password never goes in the config file.

3. **Sources and interests.** Configure only the sources you want in `config.json`. The article selection step is independent of the ingest destinations: your curation script reads `interests.json` and appends article URLs to `queue.txt`.

4. **Fonts (optional).** The cover uses UnifrakturMaguntia and PT Serif TTF files. Put them in `<data_dir>/fonts/` (names are set by `masthead_font`, `serif_bold_font`, and `serif_regular_font`). Without them the build still works and uses Pillow's built-in font.

5. **Run once by hand.**
   ```sh
   .venv/bin/python scripts/kobo-interests.py
   cp curate.example.sh curate.sh
   printf 'https://example.com/an-article\\n' >> /srv/morning-paper/queue.txt
   .venv/bin/python scripts/kobo-digest-build.py
   ```
   The generated EPUB is at `<data_dir>/read-later.epub` and dated copies appear in each configured output ingest folder. For a self-contained test build from cached article JSON files, use:
   ```sh
   .venv/bin/python scripts/kobo-digest-build.py --dry-build /path/to/test-data
   ```

6. **Schedule.** `crontab.example` has the 5:15 / 5:30 / 6:00 AM lines. Edit the paths and add them to your cron table.

## Files

- `scripts/kobo-interests.py`: the interest model.
- `scripts/kobo-queue.py`: URL intake helper.
- `scripts/kobo-digest-build.py`: fetch, extract, build and publish the EPUB.
- `scripts/kobo_config.py`: shared config loader and defaults.
- `curate.example.sh`: the curation contract.
- `tests/test_smoke.py`, `fixtures/`: smoke tests using local fixture articles.

## Test

```sh
.venv/bin/python -m pytest
```

The smoke tests build an EPUB from fixture articles and verify publishing to multiple ingest folders.

## Open-source parts

trafilatura, ebooklib, Pillow, yt-dlp.

## License

MIT
