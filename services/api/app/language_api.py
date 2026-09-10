from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.language_service import SUPPORTED_LANGUAGES, detect_language, normalize_language

router = APIRouter(prefix="/v1/languages", tags=["languages"])


class LanguageDetectionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    language: str | None = Field(default=None, min_length=2, max_length=20)


@router.get("")
def list_languages() -> list[dict[str, str]]:
    return [
        {"code": p.tts_locale, "name": p.name, "native_name": p.native_name, "language": p.code}
        for p in SUPPORTED_LANGUAGES.values()
    ]


@router.post("/detect")
def detect(request: LanguageDetectionRequest) -> dict[str, str]:
    profile = detect_language(request.text, request.language)
    return {"language": profile.code, "locale": profile.tts_locale, "name": profile.name, "native_name": profile.native_name}


@router.get("/{language}")
def get_language(language: str) -> dict[str, str]:
    profile = normalize_language(language)
    return {"language": profile.code, "locale": profile.tts_locale, "name": profile.name, "native_name": profile.native_name}
