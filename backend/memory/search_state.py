from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchState:
    scene: str = ""
    task: str = ""

    def reset(self, scene: str, task: str = "") -> None:
        self.scene = scene
        self.task = task


search_state = SearchState()
