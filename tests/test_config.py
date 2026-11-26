"""Tests for environment-driven application configuration."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import kobo_config


def load_with_env(monkeypatch, values):
    for key in (
        "KOBO_DATA_DIR", "KOBO_PAPER_TITLE", "KOBO_PAPER_TAGLINE",
        "KOBO_MAX_AGE_DAYS", "KOBO_SOURCE_INGEST_DIR",
        "KOBO_SOURCE_ARCHIVE_DIR", "KOBO_OUTPUT_INGEST_DIRS",
        "KOBO_FONTS_DIR", "KOBO_MASTHEAD_FONT", "KOBO_SERIF_BOLD_FONT",
        "KOBO_SERIF_REGULAR_FONT", "KOBO_LEAD_IMAGE_AVOID_FACES",
        "KOBO_AI_PROVIDER", "KOBO_AI_BASE_URL", "KOBO_AI_API_KEY",
        "KOBO_AI_MODEL", "KOBO_AI_TIMEOUT_SECONDS", "KOBO_AI_MAX_TOKENS",
        "KOBO_AI_CONTEXT", "KOBO_AI_EXPECTED_OUTPUT", "KOBO_AI_SYSTEM_PROMPT",
        "KOBO_AI_SKILLS_DIR",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return kobo_config.load()


def test_defaults(monkeypatch):
    cfg = load_with_env(monkeypatch, {})
    assert cfg["paper_title"] == "The Morning Paper"
    assert cfg["max_age_days"] == 7
    assert cfg["output_ingest_dirs"] == []
    assert cfg["lead_image_avoid_faces"] is True
    assert cfg["ai_provider"] == "openai-compatible"
    assert cfg["ai_model"] == "local-model"
    assert cfg["ai_timeout_seconds"] == 180


def test_environment_values(monkeypatch):
    cfg = load_with_env(monkeypatch, {
        "KOBO_DATA_DIR": "/var/lib/paper",
        "KOBO_PAPER_TITLE": "Daily Reads",
        "KOBO_MAX_AGE_DAYS": "14",
        "KOBO_SOURCE_INGEST_DIR": "/incoming",
        "KOBO_SOURCE_ARCHIVE_DIR": "/archive",
        "KOBO_OUTPUT_INGEST_DIRS": "/library/one, /library/two",
        "KOBO_LEAD_IMAGE_AVOID_FACES": "false",
    })
    assert cfg["data_dir"] == "/var/lib/paper"
    assert cfg["paper_title"] == "Daily Reads"
    assert cfg["max_age_days"] == 14
    assert cfg["source_ingest_dir"] == "/incoming"
    assert cfg["source_archive_dir"] == "/archive"
    assert cfg["output_ingest_dirs"] == ["/library/one", "/library/two"]
    assert cfg["lead_image_avoid_faces"] is False


def test_invalid_integer_is_rejected(monkeypatch):
    with pytest.raises(ValueError, match="KOBO_MAX_AGE_DAYS"):
        load_with_env(monkeypatch, {"KOBO_MAX_AGE_DAYS": "many"})
