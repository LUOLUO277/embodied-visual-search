from __future__ import annotations

import json
from pathlib import Path

from backend.schemas.agent_schema import TrajectoryItem


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
        thought: str,
        action: str,
        success: bool,
        error_message: str,
        visible_objects: list[str],
        agent_pose: dict,
    ) -> TrajectoryItem:
        item = TrajectoryItem(
            step=len(self.items) + 1,
            scene=scene,
            task=task,
            thought=thought,
            action=action,
            success=success,
            error_message=error_message,
            visible_objects=visible_objects,
            agent_pose=agent_pose,
        )
        self.items.append(item)
        self._persist()
        return item

    def _persist(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump() for item in self.items]
        self.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


trajectory_store = TrajectoryStore()
