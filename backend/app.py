from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_agent import router as agent_router
from backend.api.routes_camera import router as camera_router
from backend.api.routes_env import router as env_router
from backend.api.routes_settings import router as settings_router

load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="Embodied Visual Search V1", version="0.1.0")
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(env_router)
    app.include_router(agent_router)
    app.include_router(camera_router)
    app.include_router(settings_router)
    return app


app = create_app()
