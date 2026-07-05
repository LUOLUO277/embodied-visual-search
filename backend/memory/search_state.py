from __future__ import annotations

from dataclasses import dataclass, field

from backend.schemas.agent_schema import AgentStepResponse, ObserveView


@dataclass
class SemanticMemory:
    summary: str = "Search has not started yet."
    checked: list[str] = field(default_factory=list)
    ruled_out: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    recent_clues: list[str] = field(default_factory=list)


@dataclass
class SearchState:
    scene: str = ""
    task: str = ""
    task_instruction: str = ""
    target_object: str | None = None
    selected_target_image: str | None = None
    selected_target_type: str | None = None
    selected_target_note: str | None = None
    max_steps: int = 30
    agent_active: bool = False
    agent_running: bool = False
    agent_stopped: bool = False
    agent_done: bool = False
    current_step: int = 0
    last_error: str = ""
    last_feedback: str = ""
    visited_targets: list[str] = field(default_factory=list)
    last_step: AgentStepResponse | None = None
    seen_object_ids: set[str] = field(default_factory=set)
    semantic_memory: SemanticMemory = field(default_factory=SemanticMemory)
    last_observe_views: list[ObserveView] = field(default_factory=list)

    def reset_scene(self, scene: str, task: str = "") -> None:
        self.scene = scene
        self.task = task
        self.task_instruction = task
        self.target_object = None
        self.selected_target_image = None
        self.selected_target_type = None
        self.selected_target_note = None
        self.max_steps = 30
        self.agent_active = False
        self.agent_running = False
        self.agent_stopped = False
        self.agent_done = False
        self.current_step = 0
        self.last_error = ""
        self.last_feedback = ""
        self.visited_targets = []
        self.last_step = None
        self.seen_object_ids = set()
        self.semantic_memory = SemanticMemory()
        self.last_observe_views = []

    def reset_agent(
        self,
        task_instruction: str,
        target_object: str | None = None,
        max_steps: int = 30,
        target_reference_image: str | None = None,
        target_reference_type: str | None = None,
        target_reference_note: str | None = None,
    ) -> None:
        self.task = task_instruction
        self.task_instruction = task_instruction
        self.target_object = target_object
        self.selected_target_image = target_reference_image
        self.selected_target_type = target_reference_type
        self.selected_target_note = target_reference_note
        self.max_steps = max_steps
        self.agent_active = True
        self.agent_running = False
        self.agent_stopped = False
        self.agent_done = False
        self.current_step = 0
        self.last_error = ""
        self.last_feedback = ""
        self.visited_targets = []
        self.last_step = None
        self.seen_object_ids = set()
        self.semantic_memory = SemanticMemory()
        self.last_observe_views = []


search_state = SearchState()
