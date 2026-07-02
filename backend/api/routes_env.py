from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.actions.action_space import SUPPORTED_ACTIONS
from backend.envs.scene_registry import get_scene_payload
from backend.envs.thor_env import thor_env
from backend.memory.search_state import search_state
from backend.memory.trajectory import trajectory_store
from backend.schemas.action_schema import ActionRequest
from backend.schemas.env_schema import LoadSceneRequest, ObservationResponse

router = APIRouter(prefix="/api", tags=["environment"])


@router.get("/scenes")
def list_scenes() -> dict:
    return get_scene_payload()


@router.post("/env/load", response_model=ObservationResponse)
def load_scene(request: LoadSceneRequest) -> ObservationResponse:
    if request.scene not in get_scene_payload()["all_scenes"]:
        raise HTTPException(status_code=400, detail=f"Unsupported scene: {request.scene}")

    search_state.reset(scene=request.scene, task=request.task)
    trajectory_store.reset()
    try:
        return thor_env.load_scene(scene=request.scene, task=request.task)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "scene": request.scene,
                "platform": thor_env.platform_label(),
                "ai2thor_version": thor_env.ai2thor_version(),
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            },
        ) from exc


@router.get("/env/observation", response_model=ObservationResponse)
def get_observation() -> ObservationResponse:
    try:
        return thor_env.get_observation()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/env/action", response_model=ObservationResponse)
def step_action(request: ActionRequest) -> ObservationResponse:
    if request.action not in SUPPORTED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {request.action}")

    try:
        observation = thor_env.step(action_name=request.action)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    trajectory_store.record(
        scene=search_state.scene,
        task=search_state.task,
        thought=request.thought or "manual control",
        action=request.action,
        success=observation.metadata.last_action_success,
        error_message=observation.metadata.error_message,
        visible_objects=observation.metadata.visible_objects,
        agent_pose=observation.metadata.agent_pose.model_dump(),
    )
    return observation
