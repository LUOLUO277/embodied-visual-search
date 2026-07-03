from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.actions.action_adapter import execute_high_level_action
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
    MAX_PARSE_RETRIES = 3

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
        visible_objects, visible_ref_map = self._build_visible_affordances(observation)
        observation_summary = {
            "current_visual_observation": "The current first-person robot image is attached.",
            "visible_interactable_objects": visible_objects,
            "holding_objects": self._sanitize_holding_objects(observation.metadata.inventory_objects),
            "last_action_feedback": self._build_last_action_feedback(observation),
            "memory": {
                "semantic": self.search_state.semantic_memory.summary,
                "structured": {
                    "searched_areas": list(self.search_state.semantic_memory.searched_areas),
                    "negative_findings": list(self.search_state.semantic_memory.negative_findings),
                    "positive_clues": list(self.search_state.semantic_memory.positive_clues),
                    "current_hypothesis": self.search_state.semantic_memory.current_hypothesis,
                    "failed_actions": list(self.search_state.semantic_memory.failed_actions),
                },
            },
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
        try:
            parsed, raw_output = self._request_parsed_output(
                client=client,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                image_data_url=image_data_url,
            )
        except OutputParserError as exc:
            result = build_parse_error_result(str(exc))
            return self._finalize_step(
                thought=AgentThought(
                    situation_analysis="Model output parsing failed repeatedly.",
                    spatial_reasoning="",
                    task_planning=f"Retry limit reached after {self.MAX_PARSE_RETRIES} invalid model outputs.",
                    self_reflection="The model did not return a valid JSON object with thought and action fields.",
                    verification=str(exc),
                ),
                action=HighLevelAction(name="observe", argument=None, confidence=0.0),
                raw_model_output=getattr(exc, "raw_output", ""),
                action_result=result,
                observation=observation,
                memory_update={},
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
            return self._finalize_step(parsed.thought, parsed.action, raw_output, result, observation, parsed.memory_update)

        try:
            result = execute_high_level_action(parsed.action, self.env, visible_ref_map=visible_ref_map)
            next_observation = self.env.get_observation(task=self.search_state.task_instruction)
            return self._finalize_step(parsed.thought, parsed.action, raw_output, result, next_observation, parsed.memory_update)
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
            return self._finalize_step(parsed.thought, parsed.action, raw_output, result, observation, parsed.memory_update)

    def _request_parsed_output(
        self,
        client: OpenAICompatibleClient,
        system_prompt: str,
        user_prompt: str,
        image_data_url: str | None,
    ) -> tuple[Any, str]:
        retry_prompt = user_prompt
        last_error: OutputParserError | None = None
        last_raw_output = ""
        for attempt in range(1, self.MAX_PARSE_RETRIES + 1):
            raw_output = client.chat(system_prompt=system_prompt, user_text=retry_prompt, image_data_url=image_data_url)
            last_raw_output = raw_output
            try:
                return OutputParser.parse(raw_output), raw_output
            except OutputParserError as exc:
                last_error = exc
                if attempt >= self.MAX_PARSE_RETRIES:
                    setattr(exc, "raw_output", last_raw_output)
                    raise exc
                retry_prompt = self._build_parse_retry_prompt(
                    base_user_prompt=user_prompt,
                    attempt=attempt,
                    raw_output=raw_output,
                    error_message=str(exc),
                )
        assert last_error is not None
        setattr(last_error, "raw_output", last_raw_output)
        raise last_error

    def _build_parse_retry_prompt(self, base_user_prompt: str, attempt: int, raw_output: str, error_message: str) -> str:
        raw_snippet = raw_output[:1200].replace("\r", " ")
        return (
            f"{base_user_prompt}\n\n"
            f"Previous output attempt {attempt} could not be parsed: {error_message}\n"
            "Your previous response was invalid for the executor. Return exactly one valid JSON object with top-level fields thought, memory_update, and action. "
            "Do not output markdown fences, explanations, or partial JSON. If a field value is unknown, use null.\n"
            f"Previous invalid output:\n{raw_snippet}"
        )

    def _finalize_step(
        self,
        thought: AgentThought,
        action: HighLevelAction,
        raw_model_output: str,
        action_result: AgentActionResult,
        observation,
        memory_update: dict[str, Any],
    ) -> AgentStepResponse:
        self.search_state.current_step += 1
        self.search_state.agent_done = action_result.done
        self.search_state.last_error = action_result.error or action_result.message if not action_result.success else ""
        self.search_state.last_feedback = action_result.message
        if action.argument and action.name == "navigate to" and action_result.success:
            self.search_state.visited_targets.append(action.argument)
            self.search_state.visited_targets = self.search_state.visited_targets[-20:]
        self._update_semantic_memory(memory_update, action, action_result)
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

    def _build_visible_affordances(self, observation) -> tuple[list[dict[str, Any]], dict[str, str]]:
        visible_items = [item.model_dump() for item in observation.metadata.visible_objects if item.visible]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in sorted(visible_items, key=self._visible_sort_key):
            grouped[str(item.get("objectType") or "Object")].append(item)

        visible_interactable_objects: list[dict[str, Any]] = []
        visible_ref_map: dict[str, str] = {}
        for object_type, items in grouped.items():
            for index, item in enumerate(items, start=1):
                affordances = self._build_affordances(item)
                if not affordances:
                    continue
                ref = f"{object_type}_{index}"
                visible_ref_map[ref] = str(item.get("objectId") or "")
                visible_interactable_objects.append(
                    {
                        "ref": ref,
                        "type": object_type,
                        "distance": self._distance_bucket(item.get("distance")),
                        "affordances": affordances,
                    }
                )
        return visible_interactable_objects, visible_ref_map

    def _build_affordances(self, item: dict[str, Any]) -> list[str]:
        affordances: list[str] = []
        if item.get("pickupable"):
            affordances.append("pickup")
        if item.get("openable"):
            affordances.append("close" if item.get("isOpen") else "open")
        if item.get("toggleable"):
            affordances.append("toggle")
        if item.get("receptacle"):
            affordances.append("put in")
        return affordances

    def _build_last_action_feedback(self, observation) -> dict[str, Any]:
        if self.trajectory_store.items:
            last_result = self.trajectory_store.items[-1].action_result
            return {
                "success": last_result.success,
                "message": last_result.message,
            }
        message = observation.metadata.error_message or "No previous action has been executed."
        return {
            "success": bool(observation.metadata.last_action_success),
            "message": message,
        }

    def _sanitize_holding_objects(self, inventory_objects: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in inventory_objects:
            if not item:
                continue
            cleaned.append(str(item).split("|")[0])
        return cleaned

    def _update_semantic_memory(self, memory_update: dict[str, Any], action: HighLevelAction, action_result: AgentActionResult) -> None:
        semantic_memory = self.search_state.semantic_memory
        observed_area = self._clean_memory_text(memory_update.get("observed_area"))
        searched_area = self._clean_memory_text(memory_update.get("searched_area"))
        negative_finding = self._clean_memory_text(memory_update.get("negative_finding"))
        positive_clue = self._clean_memory_text(memory_update.get("positive_clue"))
        current_hypothesis = self._clean_memory_text(memory_update.get("current_hypothesis"))
        summary = self._clean_memory_text(memory_update.get("summary"))

        if searched_area:
            self._append_unique(semantic_memory.searched_areas, searched_area, limit=20)
        if negative_finding:
            self._append_unique(semantic_memory.negative_findings, negative_finding, limit=20)
        if positive_clue:
            self._append_unique(semantic_memory.positive_clues, positive_clue, limit=20)
        if current_hypothesis:
            semantic_memory.current_hypothesis = current_hypothesis
        if not action_result.success:
            semantic_memory.failed_actions.append(
                {
                    "action": action.name,
                    "argument": str(action.argument),
                    "message": action_result.message,
                }
            )
            semantic_memory.failed_actions = semantic_memory.failed_actions[-5:]

        if summary:
            semantic_memory.summary = summary
            return

        summary_parts = [
            f"Observed area: {observed_area}." if observed_area else "",
            f"Searched area: {searched_area}." if searched_area else "",
            f"Negative finding: {negative_finding}." if negative_finding else "",
            f"Positive clue: {positive_clue}." if positive_clue else "",
            f"Current hypothesis: {semantic_memory.current_hypothesis}." if semantic_memory.current_hypothesis else "",
        ]
        generated_summary = " ".join(part for part in summary_parts if part).strip()
        if generated_summary:
            semantic_memory.summary = generated_summary

    def _update_seen_objects(self, visible_objects) -> None:
        for item in visible_objects:
            self.search_state.seen_object_ids.add(item.objectId)

    def _append_unique(self, values: list[str], new_value: str, limit: int) -> None:
        if new_value in values:
            return
        values.append(new_value)
        if len(values) > limit:
            del values[:-limit]

    def _clean_memory_text(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    def _distance_bucket(self, value: Any) -> str:
        try:
            distance = float(value)
        except (TypeError, ValueError):
            return "far"
        if distance < 1.0:
            return "near"
        if distance < 2.0:
            return "middle"
        return "far"

    def _visible_sort_key(self, item: dict[str, Any]) -> tuple[str, float, str]:
        distance = item.get("distance")
        try:
            numeric_distance = float(distance)
        except (TypeError, ValueError):
            numeric_distance = 999.0
        return (
            str(item.get("objectType") or "Object"),
            numeric_distance,
            str(item.get("objectId") or ""),
        )
