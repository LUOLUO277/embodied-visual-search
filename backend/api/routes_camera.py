from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.envs.thor_env import thor_env

router = APIRouter(prefix="/api/camera", tags=["camera"])


@router.get("/views")
def get_views() -> dict:
    try:
        observation = thor_env.get_observation()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "scene": observation.metadata.scene_name,
        "robot_view": observation.robot_view,
        "room_view": observation.room_view,
    }
