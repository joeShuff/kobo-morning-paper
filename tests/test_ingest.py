"""Tests for the daily source-file ingest helpers."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("kobo_ingest", ROOT / "scripts" / "kobo_ingest.py")
ingest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ingest)


def test_parse_text_urls_ignores_comments_and_blank_lines(tmp_path):
    source = tmp_path / "feed.txt"
    source.write_text("# comment\n\nhttps://example.com/one\nhttps://example.org/two\n")
    urls, articles = ingest.parse_source_file(source)
    assert urls == ["https://example.com/one", "https://example.org/two"]
    assert articles == []


def test_parse_json_article_objects_and_url_arrays(tmp_path):
    source = tmp_path / "feed.json"
    source.write_text(json.dumps({
        "articles": [
            {"url": "https://example.com/story", "title": "Story", "text": "Body text"},
            "https://example.org/another"
        ]
    }))
    urls, articles = ingest.parse_source_file(source)
    assert urls == ["https://example.com/story", "https://example.org/another"]
    assert articles[0]["title"] == "Story"
    assert "Body text" in articles[0]["html"]
    assert articles[0]["domain"] == "example.com"


def test_parse_jsonl_pre_extracted_article(tmp_path):
    source = tmp_path / "feed.jsonl"
    source.write_text(
        json.dumps({"url": "https://example.com/story", "title": "Story", "html": "<p>Body</p>"}) + "\n"
    )
    urls, articles = ingest.parse_source_file(source)
    assert urls == ["https://example.com/story"]
    assert articles[0]["html"] == "<p>Body</p>"


def test_unsupported_and_invalid_source_files_are_rejected(tmp_path):
    unsupported = tmp_path / "feed.csv"
    unsupported.write_text("url\n")
    try:
        ingest.parse_source_file(unsupported)
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unsupported file was accepted")

    invalid = tmp_path / "bad.json"
    invalid.write_text('{"articles": [{"url": "not-a-url"}]}')
    try:
        ingest.parse_source_file(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid URL was accepted")


def test_archive_sources_uses_date_folder_and_preserves_names(tmp_path, monkeypatch):
    source_dir = tmp_path / "incoming"
    source_dir.mkdir()
    source = source_dir / "morning.json"
    source.write_text("{}")
    monkeypatch.setattr(ingest, "ARCHIVE", tmp_path / "archive")
    moved = ingest.archive_sources([source], "2026-11-25")
    assert moved == [tmp_path / "archive" / "2026-11-25" / "morning.json"]
    assert moved[0].read_text() == "{}"
    assert not source.exists()
