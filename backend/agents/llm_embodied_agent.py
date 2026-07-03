from __future__ import annotations

from backend.actions.action_adapter import execute_high_level_action, summarize_visible_objects
from backend.actions.object_resolver import ObjectResolver
from backend.agents.base_agent import BaseAgent
from backend.envs.thor_env import ThorEnv
from backend.llm.model_settings import model_settings_store
from backend.llm.openai_compatible_client import OpenAICompatibleClient
from backend.llm.output_parser import OutputParser, OutputParserError, build_parse_error_result
from backend.llm.prompt_builder import build_prompt
from backend.memory.search_state import SearchState
from backend.memory.trajectory import TrajectoryStore
from backend.schemas.agent_schema import AgentActionResult, AgentStepResponse, AgentThought
from backend.schemas.action_schema import HighLevelAction


class LLMEmbodiedAgent(BaseAgent):
    def __init__(self, env: ThorEnv, search_state: SearchState, trajectory_store: TrajectoryStore) -> None:
        self.env = env
        self.search_state = search_state
        self.trajectory_store = trajectory_store

    def reset(self, task_instruction: str, target_object: str | None = None, max_steps: int = 30) -> None:
        self.search_state.reset_agent(task_instruction=task_instruction, target_object=target_object, max_steps=max_steps)
        self.trajectory_store.reset()
        observation = self.env.get_observation(task=task_instruction)
        self._update_seen_objects(observation.metadata.visible_objects)

    def step(self, execute: bool = True) -> AgentStepResponse:
        settings = model_settings_store.load()
        observation = self.env.get_observation(task=self.search_state.task_instruction)
        self._update_seen_objects(observation.metadata.visible_objects)
        resolver = ObjectResolver(self.env.require_metadata())
        last_result = self.trajectory_store.items[-1].action_result.model_dump() if self.trajectory_store.items else None
        observation_summary = {
            "available_high_level_actions": [
                "observe",
                "move forward",
                "navigate to",
                "pickup",
                "put in",
                "toggle",
                "open",
                "close",
                "end",
            ],
            "visible_objects_summary": summarize_visible_objects(self.env),
            "visible_objects": [item.model_dump() for item in observation.metadata.visible_objects],
            "last_action_feedback": {
                "lastAction": observation.metadata.last_action,
                "lastActionSuccess": observation.metadata.last_action_success,
                "errorMessage": observation.metadata.error_message,
            },
            "legal_navigations": resolver.legal_navigations(),
            "legal_interactions": resolver.legal_interactions(),
            "inventory_objects": observation.metadata.inventory_objects,
            "searched_or_visited_history": self.search_state.visited_targets,
            "last_action_result": last_result,
            "last_error_message": self.search_state.last_error,
            "holding_objects": observation.metadata.inventory_objects,
            "agent_pose": observation.metadata.agent_pose.model_dump(),
            "recent_seen_objects": sorted(self.search_state.seen_object_ids),
        }
        system_prompt, user_prompt = build_prompt(
            task_instruction=self.search_state.task_instruction,
            target_object=self.search_state.target_object,
            observation=observation_summary,
            trajectory=self.trajectory_store.items,
            last_feedback=self.search_state.last_feedback,
            vision_enabled=settings.vision_enabled,
        )
        client = OpenAICompatibleClient(settings)
        image_data_url = f"data:image/png;base64,{observation.robot_view}" if settings.vision_enabled and observation.robot_view else None
        raw_output = client.chat(system_prompt=system_prompt, user_text=user_prompt, image_data_url=image_data_url)
        try:
            parsed = OutputParser.parse(raw_output)
        except OutputParserError as exc:
            result = build_parse_error_result(str(exc))
            return self._finalize_step(
                thought=AgentThought(
                    situation_analysis="Model output parsing failed.",
                    spatial_reasoning="",
                    task_planning="Retry with valid JSON output.",
                    self_reflection="",
                    verification=str(exc),
                ),
                action=HighLevelAction(name="observe", argument=None, confidence=0.0, raw_text=raw_output),
                raw_model_output=raw_output,
                action_result=result,
                observation=observation,
            )

        if not execute:
            result = AgentActionResult(
                success=True,
                action_name=parsed.action.name,
                argument=parsed.action.argument,
                normalized_action=parsed.action.name,
                message="Execution skipped.",
                executed=False,
            )
            return self._finalize_step(parsed.thought, parsed.action, raw_output, result, observation)

        try:
            result = execute_high_level_action(parsed.action, self.env)
            next_observation = self.env.get_observation(task=self.search_state.task_instruction)
            return self._finalize_step(parsed.thought, parsed.action, raw_output, result, next_observation)
        except Exception as exc:
            result = AgentActionResult(
                success=False,
                action_name=parsed.action.name,
                argument=parsed.action.argument,
                normalized_action=parsed.action.name,
                message=str(exc),
                error_type="action_error",
                error=str(exc),
                executed=False,
            )
            return self._finalize_step(parsed.thought, parsed.action, raw_output, result, observation)

    def _finalize_step(
        self,
        thought: AgentThought,
        action: HighLevelAction,
        raw_model_output: str,
        action_result: AgentActionResult,
        observation,
    ) -> AgentStepResponse:
        self.search_state.current_step += 1
        self.search_state.agent_done = action_result.done
        self.search_state.last_error = action_result.error or action_result.message if not action_result.success else ""
        self.search_state.last_feedback = action_result.message
        if action.argument and action.name == "navigate to" and action_result.success:
            self.search_state.visited_targets.append(action.argument)
            self.search_state.visited_targets = self.search_state.visited_targets[-20:]
        self._update_seen_objects(observation.metadata.visible_objects)
        self.trajectory_store.record(
            scene=observation.metadata.scene_name,
            task=self.search_state.task_instruction,
            thought=thought,
            action=action,
            action_result=action_result,
            raw_model_output=raw_model_output,
            visible_objects=[item.model_dump() for item in observation.metadata.visible_objects],
            seen_object_ids=sorted(self.search_state.seen_object_ids),
            holding_objects=observation.metadata.inventory_objects,
            agent_pose=observation.metadata.agent_pose.model_dump(),
            robot_view=observation.robot_view,
            last_action_feedback={
                "lastAction": observation.metadata.last_action,
                "lastActionSuccess": observation.metadata.last_action_success,
                "errorMessage": observation.metadata.error_message,
            },
        )
        response = AgentStepResponse(
            step=self.search_state.current_step,
            thought=thought,
            action=action,
            raw_model_output=raw_model_output,
            action_result=action_result,
            robot_view=observation.robot_view,
            trajectory=list(self.trajectory_store.items),
        )
        self.search_state.last_step = response
        return response

    def _update_seen_objects(self, visible_objects) -> None:
        for item in visible_objects:
            self.search_state.seen_object_ids.add(item.objectId)
