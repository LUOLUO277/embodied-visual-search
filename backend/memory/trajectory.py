from __future__ import annotations

import json
from pathlib import Path

from backend.schemas.agent_schema import AgentActionResult, AgentThought, MemoryUpdate, SearchMemorySnapshot, TrajectoryItem
from backend.schemas.action_schema import HighLevelAction


class TrajectoryStore:
    def __init__(self) -> None:
        self.items: list[TrajectoryItem] = []
        self.output_path = Path("data/trajectories/latest_trajectory.json")

    def reset(self) -> None:
        self.items = []
        self._persist()

    def record(
        self,
        scene: str,
        task: str,
        thought: AgentThought,
        action: HighLevelAction,
        action_result: AgentActionResult,
        raw_model_output: str,
        visible_objects: list[dict],
        seen_object_ids: list[str],
        holding_objects: list[str],
        agent_pose: dict,
        robot_view: str,
        last_action_feedback: dict,
        memory_update: MemoryUpdate | None = None,
        search_memory: SearchMemorySnapshot | None = None,
    ) -> TrajectoryItem:
        item = TrajectoryItem(
            step=len(self.items) + 1,
            scene=scene,
            task=task,
            thought=thought,
            action=action,
            action_result=action_result,
            raw_model_output=raw_model_output,
            memory_update=memory_update,
            search_memory=search_memory,
            visible_objects=visible_objects,
            seen_object_ids=seen_object_ids,
            holding_objects=holding_objects,
            agent_pose=agent_pose,
            robot_view=robot_view,
            last_action_feedback=last_action_feedback,
        )
        self.items.append(item)
        self._persist()
        return item

    def _persist(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump() for item in self.items]
        self.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


trajectory_store = TrajectoryStore()
