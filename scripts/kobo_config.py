"""Environment-based configuration and defaults for the newspaper generator."""
import os
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean (true/false, yes/no, 1/0)")


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be zero or greater")
    return parsed


def load() -> dict:
    """Read settings from environment variables, falling back to built-in defaults."""
    return {
        "data_dir": os.getenv("KOBO_DATA_DIR", "/data"),
        "paper_title": os.getenv("KOBO_PAPER_TITLE", "The Morning Paper"),
        "paper_tagline": os.getenv("KOBO_PAPER_TAGLINE", "All the Reads Worth Your Time"),
        "max_age_days": _int("KOBO_MAX_AGE_DAYS", 7),
        "source_ingest_dir": os.getenv("KOBO_SOURCE_INGEST_DIR", ""),
        "source_archive_dir": os.getenv("KOBO_SOURCE_ARCHIVE_DIR", ""),
        "output_ingest_dirs": [
            item.strip() for item in os.getenv("KOBO_OUTPUT_INGEST_DIRS", "").split(",")
            if item.strip()
        ],
        "fonts_dir": os.getenv("KOBO_FONTS_DIR", "fonts"),
        "masthead_font": os.getenv("KOBO_MASTHEAD_FONT", "UnifrakturMaguntia-Book.ttf"),
        "serif_bold_font": os.getenv("KOBO_SERIF_BOLD_FONT", "PT_Serif-Web-Bold.ttf"),
        "serif_regular_font": os.getenv("KOBO_SERIF_REGULAR_FONT", "PT_Serif-Web-Regular.ttf"),
        "lead_image_avoid_faces": _bool("KOBO_LEAD_IMAGE_AVOID_FACES", True),
        "ai_provider": os.getenv("KOBO_AI_PROVIDER", "openai-compatible"),
        "ai_base_url": os.getenv("KOBO_AI_BASE_URL", ""),
        "ai_api_key": os.getenv("KOBO_AI_API_KEY", ""),
        "ai_model": os.getenv("KOBO_AI_MODEL", "local-model"),
        "ai_timeout_seconds": _int("KOBO_AI_TIMEOUT_SECONDS", 180),
        "ai_source_fetch_timeout_seconds": _int("KOBO_AI_SOURCE_FETCH_TIMEOUT_SECONDS", 30),
        "ai_max_tokens": _int("KOBO_AI_MAX_TOKENS", 6000),
        "ai_context": os.getenv("KOBO_AI_CONTEXT", ""),
        "ai_expected_output": os.getenv("KOBO_AI_EXPECTED_OUTPUT", ""),
        "ai_system_prompt": os.getenv("KOBO_AI_SYSTEM_PROMPT", ""),
        "ai_skills_dir": os.getenv("KOBO_AI_SKILLS_DIR", ""),
    }


CFG = load()
DATA_DIR = Path(CFG["data_dir"]).expanduser()
