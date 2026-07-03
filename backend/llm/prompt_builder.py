from __future__ import annotations

import json

from backend.actions.action_space import HIGH_LEVEL_ACTIONS
from backend.schemas.agent_schema import TrajectoryItem

SYSTEM_PROMPT = """You are an embodied robot agent in an AI2-THOR indoor room.
You need to complete the human instruction through multi-turn interaction.

At each step, reason only from:
- the human language instruction,
- the current first-person robot image,
- the visible interactable objects in the current image,
- the semantic and structured search memory,
- the previous action feedback.

Do not assume access to a global object list, map, hidden objects, object ids, or simulator metadata.
Do not use invisible objects as action arguments.
Use visible_interactable_objects refs, such as Box_1 or Drawer_1, when interacting with objects.
Only movement and camera-adjustment actions may be repeated, using forms such as move forward*3 or rotate left*2.
When repeating an action, the repetition count must be an integer from 1 to 5.
Default policy for repeated movement or camera-adjustment actions: if the path looks clear and you expect the same micro-action to be needed several times, output 3 to 5 repetitions in one step rather than 1 repetition.
Use 1 to 2 repetitions only when the previous feedback indicates blocking, collision risk, uncertainty, a likely interaction-range change, or a need to re-observe after a small adjustment.
If you already know that several short forward, backward, sideways, rotation, or look actions are needed, prefer combining them into a single repeated action such as move right*3, rotate left*4, or move forward*5 instead of splitting them across multiple turns.
Do not split obviously consecutive short movement or camera-adjustment actions into many single-step outputs unless you are uncertain, need to re-observe after one step, or expect a possible collision or interaction change.
After a blocked move, do not keep repeating the same blocked action blindly. Choose an alternative such as sidestep, rotate, observe, or a smaller repetition count.
Do not output end just because one route, one action, or a few local moves failed. End only when the task is completed, or when repeated evidence from multiple observations strongly suggests the task cannot be completed.
Avoid searching the same area repeatedly unless new evidence appears.
If the target is found and successfully held, output end.
You must output exactly one JSON object and no markdown.
"""


def build_prompt(
    task_instruction: str,
    target_object: str | None,
    observation: dict,
    trajectory: list[TrajectoryItem],
    last_feedback: str,
    vision_enabled: bool,
) -> tuple[str, str]:
    history = []
    for item in trajectory[-6:]:
        history.append(
            {
                "step": item.step,
                "thought_summary": item.thought.task_planning,
                "action": {
                    "name": item.action.name,
                    "argument": item.action.argument,
                    "repetitions": item.action.repetitions,
                },
                "result": {
                    "success": item.action_result.success,
                    "message": item.action_result.message,
                },
            }
        )

    user_payload = {
        "task_instruction": task_instruction,
        "target_object": target_object,
        "available_actions": HIGH_LEVEL_ACTIONS,
        "repeatable_actions": [
            "move forward",
            "move back",
            "move left",
            "move right",
            "rotate left",
            "rotate right",
            "look up",
            "look down",
        ],
        "repetition_policy": {
            "default_when_clear": "Use 3-5 repetitions for repeated movement or camera-adjustment actions when the path seems clear and you expect multiple short steps in the same direction.",
            "reduced_when_risky": "Reduce to 1-2 repetitions only when blocked recently, collision is likely, uncertainty is high, or you need to re-observe after a small change.",
            "format_examples": ["move forward*4", "move right*3", "rotate left*5", "look down*2"],
        },
        "current_observation": observation,
        "last_feedback": last_feedback,
        "trajectory_summary": history,
        "vision_enabled": vision_enabled,
        "output_format": {
            "thought": {
                "situation_analysis": "string",
                "spatial_reasoning": "string",
                "task_planning": "string",
                "self_reflection": "string",
                "verification": "string",
            },
            "memory_update": {
                "observed_area": "string or null",
                "searched_area": "string or null",
                "negative_finding": "string or null",
                "positive_clue": "string or null",
                "current_hypothesis": "string or null",
                "summary": "updated concise natural-language search memory, string or null",
            },
            "action": {
                "name": "one of Available_Actions; only movement or camera-adjustment actions may use forms like move forward*3; default to 3-5 repetitions when the path is clear; reduce to 1-2 only when blocked or uncertain; repetition count must be 1-5",
                "argument": "visible object ref when required, else null",
                "confidence": "number in [0, 1] or null",
            },
        },
        "instruction": "Return exactly one JSON object and no markdown.",
    }
    return SYSTEM_PROMPT, json.dumps(user_payload, ensure_ascii=False, indent=2)
