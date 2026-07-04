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


class VisibleObject(BaseModel):
    objectId: str
    objectType: str
    name: str
    visible: bool = True
    distance: float | None = None
    pickupable: bool = False
    receptacle: bool = False
    openable: bool = False
    isOpen: bool | None = None
    toggleable: bool = False
    isToggled: bool | None = None
    parentReceptacles: list[str] = Field(default_factory=list)


class RoomObjectInfo(BaseModel):
    object_id: str
    object_type: str
    name: str
    distance: float | None = None
    position: dict[str, Any] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class RoomHitCandidate(BaseModel):
    object_id: str
    score: float
    reason: str


class EnvMetadata(BaseModel):
    scene_name: str
    agent_pose: AgentPose
    visible_objects: list[VisibleObject]
    last_action: str = ""
    last_action_success: bool
    error_message: str = ""
    inventory_objects: list[str] = Field(default_factory=list)
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
    hit_reason: str = ""
    candidates: list[RoomHitCandidate] = Field(default_factory=list)


class RoomViewOrbitRequest(BaseModel):
    delta_yaw: float
    delta_pitch: float
    delta_distance: float = 0.0


class RoomObjectSelectRequest(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    focus: bool = True
    make_snapshot: bool = True


class RoomObjectSelectResponse(BaseModel):
    hit: bool
    pixel_x: int
    pixel_y: int
    normalized_x: float
    normalized_y: float
    object: RoomObjectInfo | None = None
    room_view: str | None = None
    room_camera: RoomCameraPose | None = None
    target_snapshot: str | None = None
    target_snapshot_path: str | None = None
    message: str = ""
    hit_reason: str = ""
    candidates: list[RoomHitCandidate] = Field(default_factory=list)


class ObservationResponse(BaseModel):
    robot_view: str
    room_view: str | None = None
    metadata: EnvMetadata
