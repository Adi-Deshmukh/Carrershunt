from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services.ai_service import AIService


class _Message:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Message(content)


class _Response:
    def __init__(self, content: str):
        self.choices = [_Choice(content)]


def test_provider_order_prefers_primary_then_fallback():
    with patch.object(settings, "ai_provider", "auto"), patch.object(
        settings, "ai_primary_provider", "gemini"
    ):
        service = AIService.__new__(AIService)
        service.providers = {"gemini": MagicMock(), "grok": MagicMock(), "openai": MagicMock()}
        assert service.provider_order() == ["gemini", "grok", "openai"]


def test_json_falls_back_after_provider_error():
    service = AIService.__new__(AIService)
    gemini = MagicMock()
    grok = MagicMock()
    openai_client = MagicMock()
    gemini.chat.completions.create.side_effect = RuntimeError("gemini down")
    grok.chat.completions.create.return_value = _Response('{"ok": true}')
    service.providers = {"gemini": gemini, "grok": grok, "openai": openai_client}

    with patch.object(settings, "ai_provider", "auto"), patch.object(
        settings, "ai_primary_provider", "gemini"
    ):
        assert service._json("test") == {"ok": True}
    openai_client.chat.completions.create.assert_not_called()


def test_text_falls_back_after_provider_error():
    service = AIService.__new__(AIService)
    gemini = MagicMock()
    grok = MagicMock()
    gemini.chat.completions.create.side_effect = RuntimeError("gemini down")
    grok.chat.completions.create.return_value = _Response("fallback response")
    service.providers = {"gemini": gemini, "grok": grok}

    with patch.object(settings, "ai_provider", "auto"), patch.object(
        settings, "ai_primary_provider", "gemini"
    ):
        assert service._text("test") == "fallback response"
