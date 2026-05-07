from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel
from pydantic import Field

from stt.whisper_stt import FasterWhisperSTT
from stt.whisper_stt import WhisperCppSTT


class AssistantSettingsResponse(BaseModel):
    theme: str
    speechModel: str
    computeDevice: str
    responseMode: str
    voiceVolume: int


class AssistantSettingsRequest(BaseModel):
    theme: str = Field(default="white")
    speechModel: str = Field(default="base")
    computeDevice: str = Field(default="cpu")
    responseMode: str = Field(default="template")
    voiceVolume: int = Field(default=75, ge=0, le=100)


class SettingsService:
    DEFAULT_SETTINGS = {
        "theme": "white",
        "speechModel": "base",
        "computeDevice": "cpu",
        "responseMode": "template",
        "voiceVolume": 75,
    }

    ALLOWED_THEMES = {"white", "black"}
    ALLOWED_MODELS = {"tiny", "base", "medium"}
    ALLOWED_DEVICES = {"cpu", "cuda"}
    ALLOWED_RESPONSE_MODES = {"template", "llm"}

    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = settings_path or (Path(__file__).resolve().parent / "data" / "assistant_settings.json")

    def sanitize(self, raw: dict) -> dict:
        settings = {**self.DEFAULT_SETTINGS, **raw}

        theme = str(settings.get("theme", "white")).lower()
        settings["theme"] = theme if theme in self.ALLOWED_THEMES else "white"

        model = str(settings.get("speechModel", "base")).lower()
        settings["speechModel"] = model if model in self.ALLOWED_MODELS else "base"

        device = str(settings.get("computeDevice", "cpu")).lower()
        settings["computeDevice"] = device if device in self.ALLOWED_DEVICES else "cpu"

        response_mode = str(settings.get("responseMode", "template")).lower()
        settings["responseMode"] = response_mode if response_mode in self.ALLOWED_RESPONSE_MODES else "template"

        try:
            volume = int(settings.get("voiceVolume", 75))
        except (TypeError, ValueError):
            volume = 75
        settings["voiceVolume"] = max(0, min(100, volume))

        return settings

    def load(self) -> dict:
        if not self.settings_path.exists():
            return self.DEFAULT_SETTINGS.copy()

        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self.DEFAULT_SETTINGS.copy()

        if not isinstance(raw, dict):
            return self.DEFAULT_SETTINGS.copy()

        return self.sanitize(raw)

    def save(self, settings: dict) -> dict:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        sanitized = self.sanitize(settings)
        self.settings_path.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
        return sanitized

    def create_stt(self, settings: dict | None = None):
        active = settings if settings is not None else self.load()
        whisper_url = os.getenv("WHISPER_URL", "").strip()
        if whisper_url:
            return WhisperCppSTT(
                base_url=whisper_url,
                model_size=active["speechModel"],
                device=active["computeDevice"],
            )

        return FasterWhisperSTT(model_size=active["speechModel"], device=active["computeDevice"])
