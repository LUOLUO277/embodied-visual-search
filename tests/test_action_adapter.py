from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.actions.action_adapter import execute_high_level_action
from backend.actions.object_resolver import ObjectResolver
from backend.schemas.action_schema import HighLevelAction


class FakeEnv:
    def __init__(self, metadata: dict):
        self._metadata = metadata
        self.last_event = SimpleNamespace(metadata=metadata, frame=None)
        self.controller = object()

    def require_metadata(self):
        return self._metadata

    def require_controller(self):
        return self.controller

    def perform_controller_action(self, payload):
        self._metadata["lastAction"] = payload.get("action", "")
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

    def test_put_in_fails_when_inventory_is_empty(self):
        env = FakeEnv(self.metadata)
        result = execute_high_level_action(HighLevelAction(name="put in", argument="Drawer"), env)

        self.assertFalse(result.success)
        self.assertIn("Inventory is empty", result.message)

    def test_open_fails_for_non_openable_object(self):
        env = FakeEnv(self.metadata)
        result = execute_high_level_action(HighLevelAction(name="open", argument="Sofa"), env)

        self.assertFalse(result.success)
        self.assertIn("not openable", result.message)


if __name__ == "__main__":
    unittest.main()
