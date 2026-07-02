from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoadSceneRequest(BaseModel):
    scene: str = Field(..., examples=["FloorPlan211"])
    task: str = ""


class AgentPose(BaseModel):
    position: dict[str, Any]
    rotation: dict[str, Any]
    camera_horizon: float


class EnvMetadata(BaseModel):
    scene_name: str
    agent_pose: AgentPose
    visible_objects: list[str]
    last_action_success: bool
    error_message: str = ""
    task: str | None = None


class ObservationResponse(BaseModel):
    robot_view: str
    room_view: str | None = None
    metadata: EnvMetadata
