"""Tests for environment-driven application configuration."""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import kobo_config


def reload_config(monkeypatch, values):
    for key in list(__import__("os").environ):
        if key.startswith("KOBO_"):
            monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(kobo_config)


def test_defaults(monkeypatch):
    cfg = reload_config(monkeypatch, {})
    assert cfg.CFG["paper_title"] == "The Morning Paper"
    assert cfg.CFG["max_age_days"] == 7
    assert cfg.CFG["output_ingest_dirs"] == []
    assert cfg.CFG["lead_image_avoid_faces"] is True


def test_environment_values(monkeypatch):
    cfg = reload_config(monkeypatch, {
        "KOBO_DATA_DIR": "/var/lib/paper",
        "KOBO_PAPER_TITLE": "Daily Reads",
        "KOBO_MAX_AGE_DAYS": "14",
        "KOBO_SOURCE_INGEST_DIR": "/incoming",
        "KOBO_SOURCE_ARCHIVE_DIR": "/archive",
        "KOBO_OUTPUT_INGEST_DIRS": "/library/one, /library/two",
        "KOBO_LEAD_IMAGE_AVOID_FACES": "false",
    })
    assert str(cfg.DATA_DIR) == "/var/lib/paper"
    assert cfg.CFG["paper_title"] == "Daily Reads"
    assert cfg.CFG["max_age_days"] == 14
    assert cfg.CFG["source_ingest_dir"] == "/incoming"
    assert cfg.CFG["source_archive_dir"] == "/archive"
    assert cfg.CFG["output_ingest_dirs"] == ["/library/one", "/library/two"]
    assert cfg.CFG["lead_image_avoid_faces"] is False


def test_invalid_integer_is_rejected(monkeypatch):
    import pytest
    with pytest.raises(ValueError, match="KOBO_MAX_AGE_DAYS"):
        reload_config(monkeypatch, {"KOBO_MAX_AGE_DAYS": "many"})
