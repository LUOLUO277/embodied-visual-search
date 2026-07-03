from __future__ import annotations

import json
import unittest

from backend.llm.output_parser import OutputParser
from backend.llm.prompt_builder import build_prompt
from backend.schemas.action_schema import HighLevelAction
from backend.schemas.agent_schema import AgentActionResult, AgentThought, TrajectoryItem


class PromptBuilderTests(unittest.TestCase):
    def test_prompt_only_contains_clean_observation_fields(self):
        _, user_prompt = build_prompt(
            task_instruction="Find the mug.",
            target_object="Mug",
            observation={
                "current_visual_observation": "The current first-person robot image is attached.",
                "visible_interactable_objects": [{"ref": "Drawer_1", "type": "Drawer", "distance": "near", "affordances": ["open"]}],
                "holding_objects": [],
                "last_action_feedback": {"success": True, "message": "Moved successfully."},
                "memory": {"semantic": "Checked the table.", "structured": {"searched_areas": ["table"], "negative_findings": [], "positive_clues": [], "current_hypothesis": "", "failed_actions": []}},
            },
            trajectory=[],
            last_feedback="Moved successfully.",
            vision_enabled=True,
        )
        payload = json.loads(user_prompt)
        current_observation = payload["current_observation"]

        self.assertEqual(
            set(current_observation.keys()),
            {"current_visual_observation", "visible_interactable_objects", "holding_objects", "last_action_feedback", "memory"},
        )
        self.assertNotIn("legal_navigations", user_prompt)
        self.assertNotIn("legal_interactions", user_prompt)
        self.assertNotIn("agent_pose", user_prompt)
        self.assertNotIn("recent_seen_objects", user_prompt)
        self.assertNotIn("metadata_summary", user_prompt)
        self.assertIn("move forward*3", user_prompt)
        self.assertIn("1-5", user_prompt)
        self.assertIn("3-5 repetitions", user_prompt)
        self.assertIn("Reduce to 1-2 repetitions", user_prompt)

    def test_prompt_history_includes_action_repetitions(self):
        trajectory_item = TrajectoryItem(
            step=2,
            scene="FloorPlan1",
            task="Find the pillow",
            thought=AgentThought(
                situation_analysis="The sofa is ahead.",
                spatial_reasoning="A coffee table blocks the center path.",
                task_planning="Move right several times to bypass it.",
                self_reflection="A lateral detour is better than pushing forward.",
                verification="The right side looks clearer.",
            ),
            action=HighLevelAction(name="move right", repetitions=4),
            action_result=AgentActionResult(
                success=True,
                action_name="move right",
                argument=None,
                normalized_action="move right",
                message="Executed move right x4.",
                executed=True,
                done=False,
                image_paths=[],
                frame_available=True,
                legal_navigations=[],
                legal_interactions=[],
                metadata_summary={},
            ),
            raw_model_output="{}",
            visible_objects=[],
            seen_object_ids=[],
            holding_objects=[],
            agent_pose={},
            robot_view="",
            last_action_feedback={},
        )
        _, user_prompt = build_prompt(
            task_instruction="Find the pillow on the sofa and pick it up.",
            target_object="Pillow",
            observation={
                "current_visual_observation": "The current first-person robot image is attached.",
                "visible_interactable_objects": [],
                "holding_objects": [],
                "last_action_feedback": {"success": True, "message": "Executed move right x4."},
                "memory": {"semantic": "The coffee table blocks the center route.", "structured": {"searched_areas": [], "negative_findings": [], "positive_clues": [], "current_hypothesis": "Go around on the right.", "failed_actions": []}},
            },
            trajectory=[trajectory_item],
            last_feedback="Executed move right x4.",
            vision_enabled=True,
        )
        payload = json.loads(user_prompt)

        self.assertEqual(payload["trajectory_summary"][0]["action"]["repetitions"], 4)

    def test_output_parser_keeps_memory_update(self):
        parsed = OutputParser.parse(
            json.dumps(
                {
                    "thought": {
                        "situation_analysis": "A drawer is visible.",
                        "spatial_reasoning": "It is near the counter.",
                        "task_planning": "Open the drawer.",
                        "self_reflection": "This may reveal the target.",
                        "verification": "Drawer_1 is visible.",
                    },
                    "memory_update": {
                        "searched_area": "counter drawer",
                        "negative_finding": None,
                        "summary": "Checked the counter drawer.",
                    },
                    "action": {
                        "name": "open",
                        "argument": "Drawer_1",
                        "confidence": 0.9,
                    },
                }
            )
        )

        self.assertEqual(parsed.memory_update["searched_area"], "counter drawer")
        self.assertEqual(parsed.action.argument, "Drawer_1")

    def test_output_parser_repairs_truncated_json(self):
        raw_output = """```json
{
  \"thought\": {
    \"situation_analysis\": \"The box is visible.\",
    \"spatial_reasoning\": \"It is straight ahead.\",
    \"task_planning\": \"Move forward three times.\",
    \"self_reflection\": \"The move distance is short.\",
    \"verification\": \"Repeated movement is needed.\"
  },
  \"memory_update\": {
    \"observed_area\": \"floor by the window\",
    \"searched_area\": null,
    \"negative_finding\": null,
    \"positive_clue\": \"The box is almost reachable.\",
    \"current_hypothesis\": \"Three short forward moves should reach it.\",
    \"summary\": \"I am close to the box and need a few short forward moves.\"
  },
  \"action\": {
    \"name\": \"move forward*3\",
    \"argument\": null,
    \"confidence\":
```"""
        parsed = OutputParser.parse(raw_output)

        self.assertEqual(parsed.action.name, "move forward")
        self.assertEqual(parsed.action.repetitions, 3)
        self.assertIsNone(parsed.action.confidence)

    def test_repetition_count_is_limited_to_five(self):
        with self.assertRaises(Exception):
            HighLevelAction.model_validate({"name": "move forward*6"})


if __name__ == "__main__":
    unittest.main()
