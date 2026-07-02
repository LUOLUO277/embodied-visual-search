from __future__ import annotations

ROOM_SCENES = {
    "Kitchen": [f"FloorPlan{i}" for i in range(1, 31)],
    "LivingRoom": [f"FloorPlan{i}" for i in range(201, 231)],
    "Bedroom": [f"FloorPlan{i}" for i in range(301, 331)],
    "Bathroom": [f"FloorPlan{i}" for i in range(401, 431)],
}


def get_scene_payload() -> dict:
    all_scenes = [scene for scenes in ROOM_SCENES.values() for scene in scenes]
    return {
        "room_types": list(ROOM_SCENES.keys()),
        "scenes_by_room": ROOM_SCENES,
        "all_scenes": all_scenes,
    }
