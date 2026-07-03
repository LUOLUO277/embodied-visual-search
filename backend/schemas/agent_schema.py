from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.schemas.action_schema import HighLevelAction

THOUGHT_PHASES = (
    "initial_scan",
    "visual_search",
    "navigation",
    "interaction",
    "recovery",
    "completion_check",
)


class AgentThought(BaseModel):
    phase: Literal["initial_scan", "visual_search", "navigation", "interaction", "recovery", "completion_check"] = "visual_search"
    situation_analysis: str = ""
    spatial_reasoning: str | None = None
    memory_reasoning: str | None = None
    verification: str | None = None
    decision: str = ""

    @field_validator("situation_analysis", "decision", mode="before")
    @classmethod
    def normalize_required_text(cls, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return value.strip()

    @field_validator("spatial_reasoning", "memory_reasoning", "verification", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None


class MemoryUpdate(BaseModel):
    checked: str | None = None
    ruled_out: str | None = None
    clue: str | None = None
    avoid: str | None = None

    @field_validator("checked", "ruled_out", "clue", "avoid", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None


class SearchMemorySnapshot(BaseModel):
    summary: str = "Search has not started yet."
    checked: list[str] = Field(default_factory=list)
    ruled_out: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    recent_clues: list[str] = Field(default_factory=list)


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
    memory_update: MemoryUpdate | None = None
    search_memory: SearchMemorySnapshot | None = None
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
    memory_update: MemoryUpdate | None = None
    search_memory: SearchMemorySnapshot | None = None
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
    search_memory: SearchMemorySnapshot | None = None
