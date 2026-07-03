from __future__ import annotations

from dataclasses import dataclass, field

from backend.schemas.agent_schema import AgentStepResponse


@dataclass
class SemanticMemory:
    summary: str = "Search has not started yet."
    searched_areas: list[str] = field(default_factory=list)
    negative_findings: list[str] = field(default_factory=list)
    positive_clues: list[str] = field(default_factory=list)
    current_hypothesis: str = ""
    failed_actions: list[dict[str, str]] = field(default_factory=list)


@dataclass
class SearchState:
    scene: str = ""
    task: str = ""
    task_instruction: str = ""
    target_object: str | None = None
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

    def reset_scene(self, scene: str, task: str = "") -> None:
        self.scene = scene
        self.task = task
        self.task_instruction = task
        self.target_object = None
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

    def reset_agent(self, task_instruction: str, target_object: str | None = None, max_steps: int = 30) -> None:
        self.task = task_instruction
        self.task_instruction = task_instruction
        self.target_object = target_object
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


search_state = SearchState()
