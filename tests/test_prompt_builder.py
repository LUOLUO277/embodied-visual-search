from __future__ import annotations

import json
import unittest

from backend.actions.action_adapter import get_action_payload
from backend.llm.output_parser import OutputParser, OutputParserError
from backend.llm.prompt_builder import build_prompt
from backend.schemas.action_schema import HighLevelAction
from backend.schemas.agent_schema import AgentActionResult, AgentThought, MemoryUpdate, SearchMemorySnapshot, TrajectoryItem


class PromptBuilderTests(unittest.TestCase):
    def test_prompt_only_contains_allowed_observation_fields_and_policies(self):
        _, user_prompt = build_prompt(
            task_instruction="Find the mug.",
            target_object="Mug",
            observation={
                "current_visual_observation": "The current first-person robot image is attached.",
                "visible_interactable_objects": [{"ref": "Drawer_1", "type": "Drawer", "distance": "near", "affordances": ["open"]}],
                "holding_objects": [],
                "last_action_feedback": {"success": True, "message": "Moved successfully."},
                "memory": {
                    "summary": "Checked the table.",
                    "checked": ["table"],
                    "ruled_out": ["visible table surface"],
                    "avoid": ["blocked forward move"],
                    "recent_clues": ["A closed drawer is visible."],
                },
            },
            trajectory=[],
            last_feedback="Moved successfully.",
            vision_enabled=True,
        )
        payload = json.loads(user_prompt)

        self.assertEqual(set(payload["observation"].keys()), {"image", "visible_interactable_objects", "holding", "last_feedback"})
        self.assertEqual(set(payload["memory"].keys()), {"summary", "checked", "ruled_out", "avoid", "recent_clues"})
        self.assertIn("movement_policy", payload)
        self.assertIn("search_policy", payload)
        self.assertNotIn("objectId", user_prompt)
        self.assertNotIn("room_view", user_prompt)
        self.assertNotIn("metadata_summary", user_prompt)

    def test_prompt_includes_target_reference_without_object_id(self):
        _, user_prompt = build_prompt(
            task_instruction="Pick it up.",
            target_object=None,
            observation={
                "current_visual_observation": "The current first-person robot image is attached.",
                "visible_interactable_objects": [],
                "holding_objects": [],
                "last_action_feedback": {"success": True, "message": "Ready."},
                "memory": {"summary": "", "checked": [], "ruled_out": [], "avoid": [], "recent_clues": []},
                "target_reference": {"type": "Box", "note": "Selected from room view."},
            },
            trajectory=[],
            last_feedback="Ready.",
            vision_enabled=True,
            target_reference_type="Box",
            target_reference_note="Selected from room view.",
        )
        payload = json.loads(user_prompt)

        self.assertIn("target_reference", payload)
        self.assertEqual(payload["target_reference"]["type_hint"], "Box")
        self.assertIn("attached target reference image", payload["target_reference"]["image"])
        self.assertNotIn("object_id", user_prompt)
        self.assertIn("visible object refs only", payload["task"])

    def test_prompt_history_uses_phase_situation_and_decision(self):
        trajectory_item = TrajectoryItem(
            step=2,
            scene="FloorPlan1",
            task="Find the pillow",
            thought=AgentThought(
                phase="navigation",
                situation_analysis="The sofa area is ahead but partly occluded.",
                spatial_reasoning="Move right several times to bypass the table.",
                memory_reasoning="The center path was already blocked.",
                verification=None,
                decision="Move right efficiently to reveal the sofa area.",
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
            memory_update=MemoryUpdate(),
            search_memory=SearchMemorySnapshot(),
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
                "memory": {"summary": "The coffee table blocks the center route.", "checked": [], "ruled_out": [], "avoid": ["center blocked"], "recent_clues": []},
            },
            trajectory=[trajectory_item],
            last_feedback="Executed move right x4.",
            vision_enabled=True,
        )
        payload = json.loads(user_prompt)

        self.assertEqual(payload["recent_steps"][0]["phase"], "navigation")
        self.assertEqual(payload["recent_steps"][0]["situation"], "The sofa area is ahead but partly occluded.")
        self.assertEqual(payload["recent_steps"][0]["decision"], "Move right efficiently to reveal the sofa area.")
        self.assertEqual(payload["recent_steps"][0]["action"]["repetitions"], 4)

    def test_output_parser_accepts_phase_aware_thought(self):
        parsed = OutputParser.parse(
            json.dumps(
                {
                    "thought": {
                        "phase": "visual_search",
                        "situation_analysis": "A drawer is visible.",
                        "spatial_reasoning": "It is near the counter.",
                        "memory_reasoning": "Nothing has been checked yet.",
                        "verification": None,
                        "decision": "Open the drawer.",
                    },
                    "memory_update": {
                        "checked": "counter drawer",
                        "ruled_out": None,
                        "clue": "A closed drawer is visible.",
                        "avoid": None,
                    },
                    "action": {"name": "open", "argument": "Drawer_1", "confidence": 0.9},
                }
            )
        )

        self.assertEqual(parsed.thought.phase, "visual_search")
        self.assertEqual(parsed.thought.decision, "Open the drawer.")
        self.assertEqual(parsed.memory_update.checked, "counter drawer")
        self.assertEqual(parsed.action.argument, "Drawer_1")

    def test_repetition_count_is_clamped_to_five(self):
        action = HighLevelAction.model_validate({"name": "move forward*8"})
        self.assertEqual(action.name, "move forward")
        self.assertEqual(action.repetitions, 5)

    def test_non_repeatable_action_with_star_count_is_rejected(self):
        with self.assertRaises(OutputParserError):
            OutputParser.parse(json.dumps({
                "thought": {"phase": "interaction", "situation_analysis": "The drawer is visible.", "spatial_reasoning": None, "memory_reasoning": None, "verification": None, "decision": "Open it."},
                "memory_update": {"checked": None, "ruled_out": None, "clue": None, "avoid": None},
                "action": {"name": "open*2", "argument": "Drawer_1", "confidence": 0.5},
            }))

    def test_repeatable_actions_parse_expected_counts(self):
        self.assertEqual(HighLevelAction.model_validate({"name": "move forward*4"}).repetitions, 4)
        self.assertEqual(HighLevelAction.model_validate({"name": "rotate left*3"}).repetitions, 3)
        self.assertEqual(HighLevelAction.model_validate({"name": "look down*2"}).repetitions, 2)
        self.assertEqual(HighLevelAction.model_validate({"name": "move forward"}).repetitions, 1)

    def test_action_adapter_payload_still_exists_for_repeatable_actions(self):
        self.assertEqual(get_action_payload("move forward")["action"], "MoveAhead")
        self.assertEqual(get_action_payload("rotate left")["action"], "RotateLeft")


if __name__ == "__main__":
    unittest.main()
