from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings as app_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
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


@router.get("")
def get_settings():
    return {
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
    if data.openai_api_key is not None and data.openai_api_key.strip():
        app_settings.openai_api_key = data.openai_api_key.strip()
    if data.openai_model is not None and data.openai_model.strip():
        app_settings.openai_model = data.openai_model.strip()
    if data.github_token is not None and data.github_token.strip():
        app_settings.github_token = data.github_token.strip()
    if data.serper_api_key is not None and data.serper_api_key.strip():
        app_settings.serper_api_key = data.serper_api_key.strip()

    return {
        "message": "Integration settings updated in the current backend process.",
        "openai_model": app_settings.openai_model,
        "openai_configured": bool(app_settings.openai_api_key),
        "github_configured": bool(app_settings.github_token),
        "serper_configured": bool(app_settings.serper_api_key),
    }
