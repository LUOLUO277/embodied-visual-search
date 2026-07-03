from __future__ import annotations

from pydantic import BaseModel, Field


class ModelSettings(BaseModel):
    base_url: str = "https://ai.dianhuomao.shop/v1"
    api_key: str | None = "sk-rH7GKOri7wFZMYEZcteiuzliyhZReZoeSFKgLtqI0uHP5yfq"
    model: str = "【J-C思考】gemini-2.5-pro（3）"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    timeout: int = Field(default=120, ge=1, le=600)
    vision_enabled: bool = True


class ModelSettingsResponse(BaseModel):
    base_url: str = "https://ai.dianhuomao.shop/v1"
    api_key_set: bool = False
    api_key_masked: str = ""
    model: str = "【J-C思考】gemini-2.5-pro（3）"
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout: int = 120
    vision_enabled: bool = True


class ModelTestResponse(BaseModel):
    success: bool
    message: str
    raw_response: str | None = None

