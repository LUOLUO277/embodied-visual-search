from __future__ import annotations

import json
import os
from pathlib import Path

from backend.schemas.model_settings_schema import ModelSettings, ModelSettingsResponse


class ModelSettingsStore:
    def __init__(self) -> None:
        self.path = Path("backend/config/model_settings.local.json")

    def load(self) -> ModelSettings:
        env_settings = ModelSettings(
            base_url=os.getenv("OPENAI_COMPAT_BASE_URL", "https://ai.dianhuomao.shop/v1"),
            api_key=os.getenv("OPENAI_COMPAT_API_KEY", "sk-rH7GKOri7wFZMYEZcteiuzliyhZReZoeSFKgLtqI0uHP5yfq"),
            model=os.getenv("OPENAI_COMPAT_MODEL", "【J-C思考】gemini-2.5-pro（3）"),
            temperature=0.2,
            max_tokens=1024,
            timeout=120,
            vision_enabled=True,
        )
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(env_settings.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
            return env_settings
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except Exception:
            return env_settings
        merged = env_settings.model_dump()
        merged.update({key: value for key, value in payload.items() if value is not None})
        return ModelSettings.model_validate(merged)

    def save(self, settings: ModelSettings) -> ModelSettings:
        existing = self.load()
        payload = settings.model_dump()
        if payload.get("api_key") in (None, ""):
            payload["api_key"] = existing.api_key
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return ModelSettings.model_validate(payload)

    def masked_response(self) -> ModelSettingsResponse:
        settings = self.load()
        api_key = settings.api_key or ""
        return ModelSettingsResponse(
            base_url=settings.base_url,
            api_key_set=bool(api_key),
            api_key_masked=self._mask(api_key),
            model=settings.model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            timeout=settings.timeout,
            vision_enabled=settings.vision_enabled,
        )

    @staticmethod
    def _mask(api_key: str) -> str:
        if not api_key:
            return ""
        if len(api_key) <= 6:
            return "*" * len(api_key)
        return f"{api_key[:3]}-****{api_key[-4:]}" if api_key.startswith("sk-") else f"****{api_key[-4:]}"


model_settings_store = ModelSettingsStore()

