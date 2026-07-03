from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.agents.llm_embodied_agent import LLMEmbodiedAgent
from backend.envs.thor_env import thor_env
from backend.memory.search_state import search_state
from backend.memory.trajectory import trajectory_store
from backend.schemas.agent_schema import (
    AgentResetRequest,
    AgentRunRequest,
    AgentStateResponse,
    AgentStepRequest,
    AgentStepResponse,
    SearchMemorySnapshot,
)

router = APIRouter(prefix="/api", tags=["agent"])
agent = LLMEmbodiedAgent(env=thor_env, search_state=search_state, trajectory_store=trajectory_store)


@router.post("/agent/reset", response_model=AgentStateResponse)
def reset_agent(request: AgentResetRequest) -> AgentStateResponse:
    try:
        agent.reset(
            task_instruction=request.task_instruction,
            target_object=request.target_object,
            max_steps=request.max_steps,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_agent_state()


@router.post("/agent/step", response_model=AgentStepResponse)
def agent_step(request: AgentStepRequest) -> AgentStepResponse:
    if not search_state.agent_active:
        raise HTTPException(status_code=400, detail="Agent not initialized. Call /api/agent/reset first.")
    if search_state.agent_done:
        raise HTTPException(status_code=400, detail="Agent already finished. Reset the agent to start a new run.")
    try:
        return agent.step(execute=request.execute)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/agent/run", response_model=list[AgentStepResponse])
def agent_run(request: AgentRunRequest) -> list[AgentStepResponse]:
    if not search_state.agent_active:
        raise HTTPException(status_code=400, detail="Agent not initialized. Call /api/agent/reset first.")
    search_state.agent_running = True
    search_state.agent_stopped = False
    results: list[AgentStepResponse] = []
    try:
        while not search_state.agent_done and not search_state.agent_stopped and search_state.current_step < search_state.max_steps:
            results.append(agent.step(execute=request.execute))
            if results[-1].action_result.error_type == "parse_error" and not results[-1].action_result.success:
                break
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        search_state.agent_running = False


@router.get("/agent/state", response_model=AgentStateResponse)
def get_agent_state() -> AgentStateResponse:
    return AgentStateResponse(
        active=search_state.agent_active,
        running=search_state.agent_running,
        stopped=search_state.agent_stopped,
        done=search_state.agent_done,
        scene=search_state.scene,
        task_instruction=search_state.task_instruction,
        target_object=search_state.target_object,
        max_steps=search_state.max_steps,
        current_step=search_state.current_step,
        last_error=search_state.last_error,
        last_step=search_state.last_step,
        search_memory=SearchMemorySnapshot(
            summary=search_state.semantic_memory.summary,
            checked=list(search_state.semantic_memory.checked),
            ruled_out=list(search_state.semantic_memory.ruled_out),
            avoid=list(search_state.semantic_memory.avoid),
            recent_clues=list(search_state.semantic_memory.recent_clues),
        ),
    )


@router.post("/agent/stop", response_model=AgentStateResponse)
def stop_agent() -> AgentStateResponse:
    search_state.agent_running = False
    search_state.agent_stopped = True
    return get_agent_state()


@router.get("/trajectory")
def get_trajectory() -> dict:
    return {"items": trajectory_store.items}
