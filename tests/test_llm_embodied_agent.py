from __future__ import annotations

import json
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

thor_env_module = types.ModuleType("backend.envs.thor_env")
thor_env_module.ThorEnv = object
sys.modules.setdefault("backend.envs.thor_env", thor_env_module)

from backend.agents.llm_embodied_agent import LLMEmbodiedAgent
from backend.memory.search_state import SearchState
from backend.memory.trajectory import TrajectoryStore
from backend.schemas.agent_schema import ObserveView


class FakePose:
    def model_dump(self):
        return {"position": {"x": 0.0, "y": 0.9, "z": 0.0}, "rotation": {"x": 0.0, "y": 0.0, "z": 0.0}}


class FakeObservation:
    def __init__(self, robot_view: str = "robot_front") -> None:
        self.robot_view = robot_view
        self.metadata = SimpleNamespace(
            visible_objects=[],
            inventory_objects=[],
            scene_name="FloorPlan1",
            agent_pose=FakePose(),
            last_action="Observe",
            last_action_success=True,
            error_message="",
        )


class FakeEnv:
    def get_observation(self, task: str):
        return FakeObservation()


class AgentObserveViewInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.search_state = SearchState(
            task_instruction="Find the mug.",
            agent_active=True,
            last_observe_views=[
                ObserveView(label="front", relative_rotation="0", description="Front", image_base64="front_b64"),
                ObserveView(label="left", relative_rotation="left 90", description="Left", image_base64="left_b64"),
                ObserveView(label="back", relative_rotation="left 180", description="Back", image_base64="back_b64"),
                ObserveView(label="right", relative_rotation="left 270", description="Right", image_base64="right_b64"),
            ],
        )
        self.agent = LLMEmbodiedAgent(FakeEnv(), self.search_state, TrajectoryStore())

    def _run_step_and_capture(self, target_reference: str | None = None) -> tuple[list[str], str]:
        captured: dict[str, object] = {}

        class FakeClient:
            def __init__(self, settings) -> None:
                self.settings = settings

            def chat(self, system_prompt: str, user_text: str, image_data_urls: list[str] | None = None) -> str:
                captured["prompt"] = user_text
                captured["images"] = list(image_data_urls or [])
                return json.dumps(
                    {
                        "thought": {
                            "phase": "navigation",
                            "situation_analysis": "The left observe view suggests the promising direction.",
                            "spatial_reasoning": "Rotate left toward the promising clue.",
                            "memory_reasoning": None,
                            "verification": None,
                            "decision": "Rotate left to align with the clue.",
                        },
                        "memory_update": {
                            "checked": None,
                            "ruled_out": None,
                            "clue": "target-like object appears in left view",
                            "avoid": None,
                        },
                        "action": {
                            "name": "rotate left",
                            "argument": None,
                            "confidence": 0.8,
                        },
                    }
                )

        self.search_state.selected_target_image = target_reference

        with patch("backend.agents.llm_embodied_agent.model_settings_store.load", return_value=SimpleNamespace(vision_enabled=True)), patch(
            "backend.agents.llm_embodied_agent.OpenAICompatibleClient", FakeClient
        ):
            response = self.agent.step(execute=False)

        self.assertEqual(response.action.name, "rotate left")
        self.assertEqual(self.search_state.last_observe_views, [])
        return captured["images"], captured["prompt"]

    def test_step_sends_current_view_plus_three_non_front_observe_views(self):
        images, prompt = self._run_step_and_capture()

        self.assertEqual(
            images,
            [
                "data:image/png;base64,robot_front",
                "data:image/png;base64,left_b64",
                "data:image/png;base64,back_b64",
                "data:image/png;base64,right_b64",
            ],
        )
        payload = json.loads(prompt)
        self.assertEqual([item["label"] for item in payload["observation"]["observe_views"]["views"]], ["left", "back", "right"])
        self.assertIn(
            "current robot view/front, observe-left, observe-back, observe-right",
            payload["observation"]["observe_views"]["note"],
        )

    def test_step_appends_target_reference_after_observe_views(self):
        images, _ = self._run_step_and_capture(target_reference="target_b64")

        self.assertEqual(len(images), 5)
        self.assertEqual(images[-1], "data:image/png;base64,target_b64")


if __name__ == "__main__":
    unittest.main()
