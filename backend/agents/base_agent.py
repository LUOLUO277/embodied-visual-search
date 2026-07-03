from __future__ import annotations

from abc import ABC, abstractmethod

from backend.schemas.agent_schema import AgentStepResponse


class BaseAgent(ABC):
    @abstractmethod
    def reset(self, task_instruction: str, target_object: str | None = None, max_steps: int = 30) -> None:
        raise NotImplementedError

    @abstractmethod
    def step(self, execute: bool = True) -> AgentStepResponse:
        raise NotImplementedError
