from __future__ import annotations

from abc import ABC, abstractmethod

from backend.schemas.agent_schema import AgentDecision
from backend.schemas.env_schema import ObservationResponse


class BaseAgent(ABC):
    @abstractmethod
    def decide(self, observation: ObservationResponse, task: str | None = None) -> AgentDecision:
        raise NotImplementedError
