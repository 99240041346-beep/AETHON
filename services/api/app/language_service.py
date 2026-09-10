from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    name: str
    tts_locale: str
    native_name: str


SUPPORTED_LANGUAGES: dict[str, LanguageProfile] = {
    "en": LanguageProfile("en", "English", "en-US", "English"),
    "te": LanguageProfile("te", "Telugu", "te-IN", "తెలుగు"),
    "hi": LanguageProfile("hi", "Hindi", "hi-IN", "हिन्दी"),
    "ta": LanguageProfile("ta", "Tamil", "ta-IN", "தமிழ்"),
    "kn": LanguageProfile("kn", "Kannada", "kn-IN", "ಕನ್ನಡ"),
    "ml": LanguageProfile("ml", "Malayalam", "ml-IN", "മലയാളം"),
    "bn": LanguageProfile("bn", "Bengali", "bn-IN", "বাংলা"),
    "mr": LanguageProfile("mr", "Marathi", "mr-IN", "मराठी"),
    "gu": LanguageProfile("gu", "Gujarati", "gu-IN", "ગુજરાતી"),
    "pa": LanguageProfile("pa", "Punjabi", "pa-IN", "ਪੰਜਾਬੀ"),
    "es": LanguageProfile("es", "Spanish", "es-ES", "Español"),
    "fr": LanguageProfile("fr", "French", "fr-FR", "Français"),
    "de": LanguageProfile("de", "German", "de-DE", "Deutsch"),
    "pt": LanguageProfile("pt", "Portuguese", "pt-BR", "Português"),
    "ja": LanguageProfile("ja", "Japanese", "ja-JP", "日本語"),
    "ko": LanguageProfile("ko", "Korean", "ko-KR", "한국어"),
    "zh": LanguageProfile("zh", "Chinese", "zh-CN", "中文"),
}


def normalize_language(value: str | None) -> LanguageProfile:
    raw = (value or "en").strip().lower().replace("_", "-")
    code = raw.split("-", 1)[0]
    return SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES["en"])


def detect_language(text: str, requested: str | None = None) -> LanguageProfile:
    requested_profile = normalize_language(requested)
    if requested and requested_profile.code != "en":
        return requested_profile
    if not text.strip():
        return requested_profile
    # Deterministic script detection for common supported languages.
    ranges = (
        ("te", r"[\u0C00-\u0C7F]"), ("hi", r"[\u0900-\u097F]"),
        ("ta", r"[\u0B80-\u0BFF]"), ("kn", r"[\u0C80-\u0CFF]"),
        ("ml", r"[\u0D00-\u0D7F]"), ("bn", r"[\u0980-\u09FF]"),
        ("mr", r"[\u0900-\u097F]"), ("gu", r"[\u0A80-\u0AFF]"),
        ("pa", r"[\u0A00-\u0A7F]"), ("ja", r"[\u3040-\u30FF]"),
        ("ko", r"[\uAC00-\uD7AF]"), ("zh", r"[\u4E00-\u9FFF]"),
    )
    for code, pattern in ranges:
        if re.search(pattern, text):
            return SUPPORTED_LANGUAGES[code]
    return requested_profile


def language_instruction(profile: LanguageProfile) -> str:
    if profile.code == "te":
        return "Respond naturally in Telugu. Telugu-English mixed input is supported; preserve useful English technical terms."
    return f"Respond naturally in {profile.name}. Preserve the user's language and do not translate unless asked."


def deterministic_ack(profile: LanguageProfile, text: str) -> str:
    messages = {
        "te": f"నేను విన్నాను: {text}",
        "hi": f"मैंने सुना: {text}",
        "ta": f"நான் கேட்டேன்: {text}",
        "kn": f"ನಾನು ಕೇಳಿದೆ: {text}",
        "ml": f"ഞാൻ കേട്ടു: {text}",
        "bn": f"আমি শুনেছি: {text}",
        "mr": f"मी ऐकले: {text}",
        "gu": f"મેં સાંભળ્યું: {text}",
        "pa": f"ਮੈਂ ਸੁਣਿਆ: {text}",
        "es": f"He escuchado: {text}",
        "fr": f"J’ai entendu : {text}",
        "de": f"Ich habe gehört: {text}",
        "pt": f"Eu ouvi: {text}",
        "ja": f"聞き取りました: {text}",
        "ko": f"들었습니다: {text}",
        "zh": f"我听到了：{text}",
    }
    return messages.get(profile.code, f"I heard you: {text}")


def action_ack(profile: LanguageProfile, app: str) -> str:
    messages = {
        "te": f"సరే Harsha, {app} ఓపెన్ చేస్తున్నాను.",
        "hi": f"ठीक है Harsha, {app} खोल रहा हूँ।",
        "ta": f"சரி Harsha, {app} திறக்கிறேன்.",
        "kn": f"ಸರಿ Harsha, {app} ತೆರೆಯುತ್ತಿದ್ದೇನೆ.",
        "ml": f"ശരി Harsha, {app} തുറക്കുന്നു.",
        "es": f"De acuerdo Harsha, abriendo {app}.",
        "fr": f"D’accord Harsha, j’ouvre {app}.",
        "de": f"Okay Harsha, ich öffne {app}.",
        "pt": f"Certo Harsha, abrindo {app}.",
        "ja": f"わかりました Harsha、{app}を開きます。",
        "ko": f"알겠습니다 Harsha, {app}을(를) 엽니다.",
        "zh": f"好的 Harsha，正在打开 {app}。",
    }
    return messages.get(profile.code, f"Okay Harsha, opening {app}.")
