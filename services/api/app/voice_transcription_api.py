"""Server-side multilingual audio transcription for AETHON voice chat."""
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/v1/voice", tags=["voice"])
MAX_AUDIO_BYTES = 20 * 1024 * 1024
ALLOWED_SUFFIXES = {".webm", ".wav", ".mp3", ".m4a", ".mp4", ".mpeg", ".mpga", ".ogg", ".oga", ".flac"}


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe a short audio turn; provider credentials never leave the server."""
    suffix = Path(file.filename or "voice.webm").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "Unsupported audio format. Record audio in your browser and try again.")
    audio = await file.read(MAX_AUDIO_BYTES + 1)
    if not audio:
        raise HTTPException(400, "The recording is empty.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Recording is too large. Keep each voice turn under 20 MB.")

    api_key = os.getenv("AETHON_MODEL_API_KEY", "").strip()
    base_url = os.getenv("AETHON_MODEL_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    model = os.getenv("AETHON_TRANSCRIPTION_MODEL", "whisper-large-v3").strip()
    if not api_key:
        raise HTTPException(503, "Multilingual voice transcription is not configured. Add the provider API key to the server environment.")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = await client.post(
                f"{base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data={"model": model, "response_format": "json"},
                files={"file": (file.filename or f"voice{suffix}", audio, file.content_type or "application/octet-stream")},
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Audio transcription timed out. Please try a shorter recording.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Audio transcription provider is temporarily unavailable.") from exc
    if response.status_code >= 400:
        # Do not return upstream response bodies: they may contain operational details.
        raise HTTPException(502, f"Audio transcription failed (provider HTTP {response.status_code}).")
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(502, "Audio transcription returned an invalid response.") from exc
    transcript = payload.get("text")
    if not isinstance(transcript, str) or not transcript.strip():
        raise HTTPException(422, "No speech was detected. Please try again.")
    return {"ok": True, "text": transcript.strip(), "language": payload.get("language")}
