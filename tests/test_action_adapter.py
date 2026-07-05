from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.actions.action_adapter import adapt_high_level_action, execute_high_level_action
from backend.actions.object_resolver import ObjectResolver
from backend.schemas.action_schema import HighLevelAction


class FakeEnv:
    def __init__(self, metadata: dict, fail_on_step: int | None = None, error_message: str = "Blocked by obstacle."):
        self._metadata = metadata
        self.fail_on_step = fail_on_step
        self.failure_message = error_message
        self.last_event = SimpleNamespace(metadata=metadata, frame=None)
        self.controller = object()
        self.performed_actions: list[dict] = []

    def require_metadata(self):
        return self._metadata

    def require_controller(self):
        return self.controller

    def perform_controller_action(self, payload):
        self.performed_actions.append(dict(payload))
        self._metadata["lastAction"] = payload.get("action", "")
        current_step = len(self.performed_actions)
        if self.fail_on_step is not None and current_step == self.fail_on_step:
            self._metadata["lastActionSuccess"] = False
            self._metadata["errorMessage"] = self.failure_message
            return
        self._metadata["lastActionSuccess"] = True
        self._metadata["errorMessage"] = ""

    def refresh_room_camera(self):
        return None

    def lookup_agent_position_preset(self, object_id: str):
        return None

    def save_frame(self, frame, prefix: str):
        return ""

    def save_combined_frames(self, frames, prefix: str):
        return ""


class ActionAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = {
            "agent": {"position": {"x": 0.0, "y": 0.9, "z": 0.0}},
            "inventoryObjects": [],
            "lastActionSuccess": True,
            "errorMessage": "",
            "objects": [
                {
                    "objectId": "Drawer|-01.00|+00.00|+01.00",
                    "objectType": "Drawer",
                    "visible": True,
                    "openable": True,
                    "isOpen": False,
                    "pickupable": False,
                    "toggleable": False,
                    "receptacle": True,
                    "position": {"x": -1.0, "y": 0.5, "z": 1.0},
                },
                {
                    "objectId": "Drawer|-01.40|+00.00|+01.00",
                    "objectType": "Drawer",
                    "visible": False,
                    "openable": True,
                    "isOpen": False,
                    "pickupable": False,
                    "toggleable": False,
                    "receptacle": True,
                    "position": {"x": -1.4, "y": 0.5, "z": 1.0},
                },
                {
                    "objectId": "Sofa|+01.00|+00.00|+02.00",
                    "objectType": "Sofa",
                    "visible": True,
                    "openable": False,
                    "pickupable": False,
                    "toggleable": False,
                    "receptacle": False,
                    "position": {"x": 1.0, "y": 0.0, "z": 2.0},
                },
            ],
        }
        self.visible_ref_map = {"Drawer_1": "Drawer|-01.00|+00.00|+01.00", "Sofa_1": "Sofa|+01.00|+00.00|+02.00"}

    def test_object_resolver_supports_type_indexed_and_object_id(self):
        resolver = ObjectResolver(self.metadata)
        by_type = resolver.resolve("Drawer")
        by_indexed = resolver.resolve("Drawer_1")
        by_id = resolver.resolve("objectId: Drawer|-01.00|+00.00|+01.00")

        self.assertTrue(by_type.success)
        self.assertEqual(by_type.resolved.object_type, "Drawer")
        self.assertTrue(by_indexed.success)
        self.assertEqual(by_indexed.resolved.object_id, "Drawer|-01.00|+00.00|+01.00")
        self.assertTrue(by_id.success)
        self.assertEqual(by_id.resolved.object_id, "Drawer|-01.00|+00.00|+01.00")

    def test_resolve_visible_ref_requires_current_ref(self):
        resolver = ObjectResolver(self.metadata)
        resolved = resolver.resolve_visible_ref("Drawer_1", self.visible_ref_map)
        missing = resolver.resolve_visible_ref("Drawer_2", self.visible_ref_map)

        self.assertTrue(resolved.success)
        self.assertEqual(resolved.resolved.object_id, "Drawer|-01.00|+00.00|+01.00")
        self.assertFalse(missing.success)
        self.assertIn("not visible", missing.message)

    def test_put_in_fails_when_inventory_is_empty(self):
        env = FakeEnv(self.metadata)
        result = execute_high_level_action(HighLevelAction(name="put in", argument="Drawer_1"), env, visible_ref_map=self.visible_ref_map)

        self.assertFalse(result.success)
        self.assertIn("Inventory is empty", result.message)

    def test_open_fails_for_non_openable_object(self):
        env = FakeEnv(self.metadata)
        result = execute_high_level_action(HighLevelAction(name="open", argument="Sofa_1"), env, visible_ref_map=self.visible_ref_map)

        self.assertFalse(result.success)
        self.assertIn("not openable", result.message)

    def test_interaction_rejects_non_visible_refs(self):
        env = FakeEnv(self.metadata)
        result = execute_high_level_action(HighLevelAction(name="pickup", argument="Drawer_2"), env, visible_ref_map=self.visible_ref_map)

        self.assertFalse(result.success)
        self.assertEqual(result.error_type, "illegal_action")
        self.assertIn("Observe, rotate, or move closer first", result.message)

    def test_navigation_rejects_non_visible_refs(self):
        env = FakeEnv(self.metadata)
        result = execute_high_level_action(HighLevelAction(name="navigate to", argument="Drawer_2"), env, visible_ref_map=self.visible_ref_map)

        self.assertFalse(result.success)
        self.assertEqual(result.error_type, "illegal_action")
        self.assertIn("not visible", result.message)

    def test_new_exploration_actions_are_adapted(self):
        expectations = {
            "move back": "MoveBack",
            "move left": "MoveLeft",
            "move right": "MoveRight",
            "rotate left": "RotateLeft",
            "rotate right": "RotateRight",
            "look up": "LookUp",
            "look down": "LookDown",
        }

        for high_level_name, controller_name in expectations.items():
            adapted = adapt_high_level_action(HighLevelAction(name=high_level_name), env=FakeEnv(self.metadata))
            self.assertEqual(adapted.kind, "controller_step")
            self.assertEqual(adapted.payload["action"], controller_name)

    def test_move_right_star_three_is_parsed_and_executed_three_times(self):
        env = FakeEnv(self.metadata)
        action = HighLevelAction.model_validate({"name": "move right*3"})
        result = execute_high_level_action(action, env)

        self.assertTrue(result.success)
        self.assertEqual(action.name, "move right")
        self.assertEqual(action.repetitions, 3)
        self.assertEqual([payload["action"] for payload in env.performed_actions], ["MoveRight", "MoveRight", "MoveRight"])
        self.assertEqual(result.adapted_action["repetitions"], 3)
        self.assertEqual(result.message, "Executed move right x3.")

    def test_repeated_movement_executes_multiple_steps(self):
        env = FakeEnv(self.metadata)
        action = HighLevelAction.model_validate({"name": "move forward*3"})
        result = execute_high_level_action(action, env)

        self.assertTrue(result.success)
        self.assertEqual(action.name, "move forward")
        self.assertEqual(action.repetitions, 3)
        self.assertEqual(len(env.performed_actions), 3)
        self.assertEqual(result.message, "Executed move forward x3.")

    def test_repeated_navigation_stops_on_first_failure(self):
        env = FakeEnv(self.metadata, fail_on_step=2, error_message="Blocked by chair.")
        action = HighLevelAction.model_validate({"name": "move right*3"})
        result = execute_high_level_action(action, env)

        self.assertFalse(result.success)
        self.assertEqual(len(env.performed_actions), 2)
        self.assertEqual(result.adapted_action["repetitions"], 3)
        self.assertEqual(result.adapted_action["completed_steps"], 1)
        self.assertEqual(result.adapted_action["failed_step"], 2)
        self.assertIn("Executed move right 1/3 steps", result.message)
        self.assertIn("failed at step 2", result.message)


if __name__ == "__main__":
    unittest.main()
