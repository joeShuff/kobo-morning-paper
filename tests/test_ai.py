"""Tests for the provider-neutral AI editorial stage."""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import kobo_ai


def test_prompt_includes_source_context_expected_output_and_skills(tmp_path, monkeypatch):
    source = tmp_path / "dinners.txt"
    source.write_text("Today: pasta\nTomorrow: curry\nDay after tomorrow: soup", encoding="utf-8")
    (tmp_path / "dinners.context.txt").write_text(
        "These are the household dinner plans.", encoding="utf-8"
    )
    (tmp_path / "dinners.expected.txt").write_text(
        "Create a short Coming Up article with dated entries.", encoding="utf-8"
    )
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "coming-up.md").write_text(
        "Use a concise newspaper-style heading and list.", encoding="utf-8"
    )
    monkeypatch.setenv("KOBO_AI_SKILLS_DIR", str(skills))
    monkeypatch.setenv("KOBO_AI_CONTEXT", "This is a family newspaper.")
    monkeypatch.setenv("KOBO_AI_EXPECTED_OUTPUT", "Return articles as JSON.")
    prompt = kobo_ai.build_user_prompt([source], today=date(2026, 11, 26))
    assert "LOCAL DATE: 2026-11-26" in prompt
    assert "This is a family newspaper." in prompt
    assert "These are the household dinner plans." in prompt
    assert "Create a short Coming Up article" in prompt
    assert "Use a concise newspaper-style heading" in prompt
    assert "Today: pasta" in prompt


def test_normalise_articles_converts_plain_text_to_safe_html(tmp_path):
    source = tmp_path / "notes.txt"
    result = kobo_ai._normalise_articles({
        "articles": [{
            "section": "Coming up",
            "headline": "Dinner this week",
            "dek": "The next three evenings.",
            "body": "Today: pasta <b>and salad</b>.\n\nTomorrow: curry.",
        }]
    }, [source], today=date(2026, 11, 26))
    assert len(result) == 1
    article = result[0]
    assert article["title"] == "Dinner this week"
    assert article["section"] == "Coming up"
    assert article["published"] == "2026-11-26"
    assert "&lt;b&gt;and salad&lt;/b&gt;" in article["html"]
    assert article["html"].count("<p>") == 2
    assert article["url"].startswith("ai://")


def test_openai_compatible_endpoint_and_request(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": '{"articles": []}'}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(kobo_ai.requests, "post", fake_post)
    monkeypatch.setenv("KOBO_AI_PROVIDER", "openai-compatible")
    monkeypatch.setenv("KOBO_AI_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("KOBO_AI_MODEL", "qwen-local")
    monkeypatch.delenv("KOBO_AI_API_KEY", raising=False)
    assert kobo_ai._request_completion("system", "user") == '{"articles": []}'
    assert captured["url"] == "http://localhost:1234/v1/chat/completions"
    assert captured["json"]["model"] == "qwen-local"
    assert captured["json"]["messages"][0]["content"] == "system"


def test_anthropic_provider_uses_messages_api(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"content": [{"type": "text", "text": '{"articles": []}'}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(kobo_ai.requests, "post", fake_post)
    monkeypatch.setenv("KOBO_AI_PROVIDER", "anthropic")
    monkeypatch.setenv("KOBO_AI_API_KEY", "test-key")
    monkeypatch.setenv("KOBO_AI_MODEL", "claude-test")
    monkeypatch.delenv("KOBO_AI_BASE_URL", raising=False)
    assert kobo_ai._request_completion("system", "user") == '{"articles": []}'
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["json"]["system"] == "system"
