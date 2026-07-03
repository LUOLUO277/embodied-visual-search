from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.action_schema import HighLevelAction


class AgentThought(BaseModel):
    situation_analysis: str = ""
    spatial_reasoning: str = ""
    task_planning: str = ""
    self_reflection: str = ""
    verification: str = ""


class AgentResetRequest(BaseModel):
    task_instruction: str
    target_object: str | None = None
    max_steps: int = Field(default=30, ge=1, le=200)


class AgentStepRequest(BaseModel):
    execute: bool = True


class AgentRunRequest(BaseModel):
    execute: bool = True


class AgentActionResult(BaseModel):
    success: bool
    action_name: str = ""
    argument: str | None = None
    normalized_action: str = ""
    selected_object_id: str | None = None
    selected_object_type: str | None = None
    message: str = ""
    error_type: str | None = None
    error: str | None = None
    executed: bool = True
    done: bool = False
    adapted_action: dict[str, Any] | None = None
    image_paths: list[str] = Field(default_factory=list)
    frame_available: bool = False
    legal_navigations: list[str] = Field(default_factory=list)
    legal_interactions: list[dict[str, Any]] = Field(default_factory=list)
    metadata_summary: dict[str, Any] = Field(default_factory=dict)


class TrajectoryItem(BaseModel):
    step: int
    scene: str
    task: str
    thought: AgentThought
    action: HighLevelAction
    action_result: AgentActionResult
    raw_model_output: str = ""
    visible_objects: list[dict[str, Any]] = Field(default_factory=list)
    seen_object_ids: list[str] = Field(default_factory=list)
    holding_objects: list[str] = Field(default_factory=list)
    agent_pose: dict[str, Any]
    robot_view: str = ""
    last_action_feedback: dict[str, Any] = Field(default_factory=dict)


class AgentStepResponse(BaseModel):
    step: int
    thought: AgentThought
    action: HighLevelAction
    raw_model_output: str
    action_result: AgentActionResult
    robot_view: str | None = None
    trajectory: list[TrajectoryItem] = Field(default_factory=list)


class AgentStateResponse(BaseModel):
    active: bool
    running: bool = False
    stopped: bool = False
    done: bool = False
    scene: str = ""
    task_instruction: str = ""
    target_object: str | None = None
    max_steps: int = 30
    current_step: int = 0
    last_error: str = ""
    last_step: AgentStepResponse | None = None
