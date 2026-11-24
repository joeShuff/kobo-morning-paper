"""Smoke test: build an EPUB from two fixture articles. No network, no Calibre."""
import importlib.util
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_dry_build_makes_epub(tmp_path):
    shutil.copytree(ROOT / "fixtures" / "articles", tmp_path / "articles")
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "kobo-digest-build.py"), "--dry-build", str(tmp_path)],
        capture_output=True, text=True, cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "KOBO_PAPER_CONFIG": str(tmp_path / "none.json")},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    epub = tmp_path / "read-later.epub"
    assert epub.exists()
    with zipfile.ZipFile(epub) as z:
        names = z.namelist()
        assert "mimetype" in names
        assert "EPUB/art_0.xhtml" in names and "EPUB/art_1.xhtml" in names
        assert "EPUB/frontpage.xhtml" in names
        body = z.read("EPUB/art_0.xhtml").decode()
    assert "Example Article" in body


def test_bookorbit_ingest_publishes_dated_edition(tmp_path):
    import json

    shutil.copytree(ROOT / "fixtures" / "articles", tmp_path / "articles")
    ingest = tmp_path / "bookorbit-ingest"
    ingest.mkdir()
    config = {
        "data_dir": str(tmp_path),
        "calibre_enabled": False,
        "bookorbit_ingest_dir": str(ingest),
        "lead_image_avoid_faces": False,
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
        "KOBO_PAPER_CONFIG": str(config_path),
        "KOBO_DATELINE_DATE": "2026-11-24",
    }
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "kobo-digest-build.py")],
        capture_output=True, text=True, cwd=tmp_path, env=env,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    published = ingest / "the-morning-paper-2026-11-24.epub"
    assert published.exists()
    with zipfile.ZipFile(published) as z:
        from xml.etree import ElementTree as ET
        opf_name = next(n for n in z.namelist() if n.endswith(".opf"))
        opf = ET.fromstring(z.read(opf_name))
        ns = {"dc": "http://purl.org/dc/elements/1.1/"}
        assert opf.findtext("dc:title", namespaces=ns) == "The Morning Paper — 24 November 2026"
        assert opf.findtext("dc:date", namespaces=ns) == "2026-11-24"


def test_queue_extracts_kobo_lines():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("kq", ROOT / "scripts" / "kobo-queue.py")
    kq = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kq)
    assert kq.extract_urls("hi\nkobo: https://example.com/x\nkobo: <https://example.org/y>\nnope") == [
        "https://example.com/x", "https://example.org/y"]
