"""Small configuration surface for the source-ingest newspaper generator.

All content discovery and preparation happens upstream. This application only
reads prepared source files, builds the EPUB, and publishes it.
"""
import json
import os
from pathlib import Path

DEFAULTS = {
    "data_dir": "~/kobo-articles",
    "paper_title": "The Morning Paper",
    "paper_tagline": "All the Reads Worth Your Time",
    "max_age_days": 7,
    "source_ingest_dir": "",
    "source_archive_dir": "",
    "output_ingest_dirs": [],
    "fonts_dir": "fonts",
    "masthead_font": "UnifrakturMaguntia-Book.ttf",
    "serif_bold_font": "PT_Serif-Web-Bold.ttf",
    "serif_regular_font": "PT_Serif-Web-Regular.ttf",
    "lead_image_avoid_faces": True,
}


def config_path() -> Path:
    env = os.environ.get("KOBO_PAPER_CONFIG")
    if env:
        return Path(env).expanduser()
    for path in (Path.cwd() / "config.json", Path(__file__).resolve().parent.parent / "config.json"):
        if path.exists():
            return path
    return Path("config.json")


def load() -> dict:
    cfg = dict(DEFAULTS)
    path = config_path()
    if path.exists():
        cfg.update({key: value for key, value in json.loads(path.read_text()).items()
                    if not key.startswith("_")})
    return cfg


CFG = load()
DATA_DIR = Path(CFG["data_dir"]).expanduser()
