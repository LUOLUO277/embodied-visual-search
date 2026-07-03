from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.llm.model_settings import model_settings_store
from backend.llm.openai_compatible_client import OpenAICompatibleClient
from backend.schemas.model_settings_schema import ModelSettings, ModelSettingsResponse, ModelTestResponse

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings/model", response_model=ModelSettingsResponse)
def get_model_settings() -> ModelSettingsResponse:
    return model_settings_store.masked_response()


@router.post("/settings/model", response_model=ModelSettingsResponse)
def save_model_settings(settings: ModelSettings) -> ModelSettingsResponse:
    try:
        model_settings_store.save(settings)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save model settings: {exc}") from exc
    return model_settings_store.masked_response()


@router.post("/settings/model/test", response_model=ModelTestResponse)
def test_model_settings(settings: ModelSettings | None = None) -> ModelTestResponse:
    try:
        effective_settings = settings or model_settings_store.load()
        raw_response = OpenAICompatibleClient(effective_settings).test_connection()
        return ModelTestResponse(success=True, message="Model connection succeeded.", raw_response=raw_response)
    except Exception as exc:
        return ModelTestResponse(success=False, message=str(exc), raw_response=None)
