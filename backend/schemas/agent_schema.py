from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from backend.schemas.env_schema import ObservationResponse


class AgentDecision(BaseModel):
    thought: str
    action: str


class AgentStepRequest(BaseModel):
    task: str | None = None


class TrajectoryItem(BaseModel):
    step: int
    scene: str
    task: str
    thought: str
    action: str
    success: bool
    error_message: str
    visible_objects: list[str]
    agent_pose: dict[str, Any]


class AgentStepResponse(BaseModel):
    decision: AgentDecision
    observation: ObservationResponse
    trajectory: TrajectoryItem
