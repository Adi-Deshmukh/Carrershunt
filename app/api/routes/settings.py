from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings as app_settings

router = APIRouter(prefix="/settings", tags=["settings"])

VALID_PROVIDERS = {"auto", "gemini", "grok", "openai"}


class SettingsUpdate(BaseModel):
    ai_provider: str | None = None
    ai_primary_provider: str | None = None
    ai_fallback_enabled: bool | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    xai_api_key: str | None = None
    xai_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    github_token: str | None = None
    serper_api_key: str | None = None


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}••••{value[-4:]}"


def _set_secret(name: str, value: str | None) -> None:
    if value is not None and value.strip():
        setattr(app_settings, name, value.strip())


def _configured_providers() -> list[str]:
    return [
        provider
        for provider, configured in (
            ("gemini", bool(app_settings.gemini_api_key)),
            ("grok", bool(app_settings.xai_api_key)),
            ("openai", bool(app_settings.openai_api_key)),
        )
        if configured
    ]


@router.get("")
def get_settings():
    return {
        "ai_provider": app_settings.ai_provider,
        "ai_primary_provider": app_settings.ai_primary_provider,
        "ai_fallback_enabled": app_settings.ai_fallback_enabled,
        "configured_providers": _configured_providers(),
        "gemini_model": app_settings.gemini_model,
        "gemini_configured": bool(app_settings.gemini_api_key),
        "gemini_api_key": _mask(app_settings.gemini_api_key),
        "xai_model": app_settings.xai_model,
        "xai_configured": bool(app_settings.xai_api_key),
        "xai_api_key": _mask(app_settings.xai_api_key),
        "openai_model": app_settings.openai_model,
        "openai_configured": bool(app_settings.openai_api_key),
        "openai_api_key": _mask(app_settings.openai_api_key),
        "github_configured": bool(app_settings.github_token),
        "github_token": _mask(app_settings.github_token),
        "serper_configured": bool(app_settings.serper_api_key),
        "serper_api_key": _mask(app_settings.serper_api_key),
    }


@router.post("")
def update_settings(data: SettingsUpdate):
    if data.ai_provider is not None and data.ai_provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=422, detail="ai_provider must be auto, gemini, grok, or openai")
    if (
        data.ai_primary_provider is not None
        and data.ai_primary_provider not in VALID_PROVIDERS - {"auto"}
    ):
        raise HTTPException(status_code=422, detail="ai_primary_provider must be gemini, grok, or openai")

    for name in ("ai_provider", "ai_primary_provider", "gemini_model", "xai_model", "openai_model"):
        value = getattr(data, name)
        if value is not None and value.strip():
            setattr(app_settings, name, value.strip())

    if data.ai_fallback_enabled is not None:
        app_settings.ai_fallback_enabled = data.ai_fallback_enabled

    for name in ("gemini_api_key", "xai_api_key", "openai_api_key", "github_token", "serper_api_key"):
        _set_secret(name, getattr(data, name))

    return {
        "message": "Integration settings updated in the current backend process.",
        "ai_provider": app_settings.ai_provider,
        "ai_primary_provider": app_settings.ai_primary_provider,
        "ai_fallback_enabled": app_settings.ai_fallback_enabled,
        "configured_providers": _configured_providers(),
        "github_configured": bool(app_settings.github_token),
        "serper_configured": bool(app_settings.serper_api_key),
    }
