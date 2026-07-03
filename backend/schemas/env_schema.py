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


class RoomCameraPose(BaseModel):
    position: dict[str, Any]
    rotation: dict[str, Any]
    target: dict[str, Any]
    field_of_view: float
    distance: float
    yaw: float
    pitch: float


class RoomObjectInfo(BaseModel):
    object_id: str
    object_type: str
    name: str
    distance: float | None = None
    position: dict[str, Any] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EnvMetadata(BaseModel):
    scene_name: str
    agent_pose: AgentPose
    visible_objects: list[str]
    last_action_success: bool
    error_message: str = ""
    task: str | None = None
    room_camera: RoomCameraPose | None = None


class RoomViewInspectRequest(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class RoomViewInspectResponse(BaseModel):
    hit: bool
    pixel_x: int
    pixel_y: int
    normalized_x: float
    normalized_y: float
    object: RoomObjectInfo | None = None
    message: str = ""


class RoomViewOrbitRequest(BaseModel):
    delta_yaw: float
    delta_pitch: float


class ObservationResponse(BaseModel):
    robot_view: str
    room_view: str | None = None
    metadata: EnvMetadata
