from __future__ import annotations

from backend.actions.action_space import ActionName
from backend.agents.base_agent import BaseAgent
from backend.schemas.agent_schema import AgentDecision
from backend.schemas.env_schema import ObservationResponse


class DummyAgent(BaseAgent):
    def decide(self, observation: ObservationResponse, task: str | None = None) -> AgentDecision:
        scene = observation.metadata.scene_name
        visible_count = len(observation.metadata.visible_objects)
        thought = (
            f"DummyAgent is probing scene {scene}. "
            f"Task={task or 'None'}. Visible objects={visible_count}. "
            "Rotate right to gather more context."
        )
        return AgentDecision(thought=thought, action=ActionName.ROTATE_RIGHT)
