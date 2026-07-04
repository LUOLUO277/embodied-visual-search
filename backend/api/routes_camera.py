from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.envs.thor_env import thor_env
from backend.schemas.env_schema import (
    ObservationResponse,
    RoomObjectSelectRequest,
    RoomObjectSelectResponse,
    RoomViewInspectRequest,
    RoomViewInspectResponse,
    RoomViewOrbitRequest,
)

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


@router.post("/room/orbit", response_model=ObservationResponse)
def orbit_room_camera(request: RoomViewOrbitRequest) -> ObservationResponse:
    try:
        return thor_env.orbit_room_camera(
            delta_yaw=request.delta_yaw,
            delta_pitch=request.delta_pitch,
            delta_distance=request.delta_distance,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/room/inspect", response_model=RoomViewInspectResponse)
def inspect_room_view(request: RoomViewInspectRequest) -> RoomViewInspectResponse:
    try:
        return thor_env.inspect_room_view(x=request.x, y=request.y)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/room/select-object", response_model=RoomObjectSelectResponse)
def select_room_object(request: RoomObjectSelectRequest) -> RoomObjectSelectResponse:
    try:
        return thor_env.select_room_object(x=request.x, y=request.y, focus=request.focus, make_snapshot=request.make_snapshot)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
