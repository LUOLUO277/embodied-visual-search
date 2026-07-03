from __future__ import annotations

from backend.actions.action_adapter import execute_high_level_action
from backend.envs.thor_env import ThorEnv
from backend.schemas.action_schema import HighLevelAction


def main() -> None:
    env = ThorEnv()
    env.load_scene("FloorPlan211", task="Smoke action adapter")
    sequence = [
        HighLevelAction(name="observe"),
        HighLevelAction(name="navigate to", argument="Sofa"),
    ]

    visible_types = {item["objectType"] for item in env.get_visible_object_summaries()}
    if "Laptop" in visible_types:
        sequence.append(HighLevelAction(name="navigate to", argument="Laptop"))
    else:
        sequence.append(HighLevelAction(name="navigate to", argument="Newspaper"))

    pickup_candidate = next((item["objectType"] for item in env.get_visible_object_summaries() if item.get("pickupable")), None)
    if pickup_candidate:
        sequence.append(HighLevelAction(name="pickup", argument=pickup_candidate))

    for action in sequence:
        result = execute_high_level_action(action, env)
        print(f"{action.name} {action.argument or ''}".strip())
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
