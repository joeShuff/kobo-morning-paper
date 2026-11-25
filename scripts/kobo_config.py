"""Shared configuration for the morning-paper scripts.

Settings come from a JSON file. Lookup order:
  1. the path in the KOBO_PAPER_CONFIG environment variable
  2. ./config.json (the current directory)
  3. config.json in the repo root (next to scripts/)
Every key has a default, so the scripts run with no config file at all.
Secrets (the optional IMAP login) are read from environment variables, never from the file.
"""
import json
import os
from pathlib import Path

DEFAULTS = {
    # Where the pipeline keeps its files: queue.txt, articles/, interests.json, the EPUB, logs.
    "data_dir": "~/kobo-articles",
    # The paper itself.
    "paper_title": "The Morning Paper",
    "paper_tagline": "All the Reads Worth Your Time",
    "max_age_days": 7,                    # drop articles older than this (pinned.txt bypasses)
    # Daily source-file intake and date-based archive. Empty means use data_dir defaults.
    "source_ingest_dir": "",
    "source_archive_dir": "",
    # Fonts for the generated cover and front page (TTF files). See README, "Fonts".
    "fonts_dir": "fonts",                 # relative to data_dir unless absolute
    "masthead_font": "UnifrakturMaguntia-Book.ttf",
    "serif_bold_font": "PT_Serif-Web-Bold.ttf",
    "serif_regular_font": "PT_Serif-Web-Regular.ttf",
    # Optional destinations scanned by external library/import services.
    "output_ingest_dirs": [],
    # Interest model sources.
    "audiobookshelf_container": "",
    "audiobookshelf_db": "/config/absdatabase.sqlite",
    "media_watch_file": "",
    "media_requester": "me",
    "seerr_url": "",
    "seerr_settings": "",
    "seerr_user": "",
    "ytdlp": "yt-dlp",
    "tiktok_collections": [],
    "exclude_titles": [],
    "exclude_requesters": [],
    "genres": ["fiction", "fantasy"],
    "extra_rules": [],
    "lead_image_avoid_faces": True,
    "kickstarter_enabled": False,
    "imap_host": "imap.gmail.com",
    "imap_folder": "[Gmail]/All Mail",
}


def config_path() -> Path:
    env = os.environ.get("KOBO_PAPER_CONFIG")
    if env:
        return Path(env).expanduser()
    for p in (Path.cwd() / "config.json", Path(__file__).resolve().parent.parent / "config.json"):
        if p.exists():
            return p
    return Path("config.json")


def load() -> dict:
    cfg = dict(DEFAULTS)
    p = config_path()
    if p.exists():
        cfg.update({k: v for k, v in json.loads(p.read_text()).items() if not k.startswith("_")})
    return cfg


CFG = load()
DATA_DIR = Path(CFG["data_dir"]).expanduser()
