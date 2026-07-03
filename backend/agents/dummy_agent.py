from __future__ import annotations

from backend.actions.action_space import HIGH_LEVEL_ACTIONS
from backend.agents.base_agent import BaseAgent
from backend.schemas.agent_schema import AgentActionResult, AgentStepResponse, AgentThought, MemoryUpdate, SearchMemorySnapshot
from backend.schemas.action_schema import HighLevelAction


class DummyAgent(BaseAgent):
    def reset(self, task_instruction: str, target_object: str | None = None, max_steps: int = 30) -> None:
        self.task_instruction = task_instruction

    def step(self, execute: bool = True) -> AgentStepResponse:
        thought = AgentThought(
            phase="visual_search",
            situation_analysis="Dummy agent placeholder.",
            spatial_reasoning=None,
            memory_reasoning=None,
            verification=None,
            decision=f"Available actions: {', '.join(HIGH_LEVEL_ACTIONS)}.",
        )
        action = HighLevelAction(name="observe", argument=None, confidence=0.0)
        return AgentStepResponse(
            step=1,
            thought=thought,
            action=action,
            raw_model_output="{}",
            memory_update=MemoryUpdate(),
            search_memory=SearchMemorySnapshot(),
            action_result=AgentActionResult(success=False, message="Dummy agent should not be used for LLM execution.", executed=False),
            robot_view=None,
            trajectory=[],
        )
