from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.agents.dummy_agent import DummyAgent
from backend.envs.thor_env import thor_env
from backend.memory.search_state import search_state
from backend.memory.trajectory import trajectory_store
from backend.schemas.agent_schema import AgentStepRequest, AgentStepResponse

router = APIRouter(prefix="/api", tags=["agent"])

dummy_agent = DummyAgent()


@router.post("/agent/step", response_model=AgentStepResponse)
def agent_step(request: AgentStepRequest) -> AgentStepResponse:
    if request.task is not None:
        search_state.task = request.task

    try:
        observation = thor_env.get_observation()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    decision = dummy_agent.decide(observation=observation, task=search_state.task)
    observation = thor_env.step(action_name=decision.action)

    trajectory_item = trajectory_store.record(
        scene=search_state.scene,
        task=search_state.task,
        thought=decision.thought,
        action=decision.action,
        success=observation.metadata.last_action_success,
        error_message=observation.metadata.error_message,
        visible_objects=observation.metadata.visible_objects,
        agent_pose=observation.metadata.agent_pose.model_dump(),
    )
    return AgentStepResponse(decision=decision, observation=observation, trajectory=trajectory_item)


@router.get("/trajectory")
def get_trajectory() -> dict:
    return {"items": trajectory_store.items}
