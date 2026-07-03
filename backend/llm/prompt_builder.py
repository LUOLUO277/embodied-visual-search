from __future__ import annotations

import json

from backend.actions.action_space import HIGH_LEVEL_ACTIONS
from backend.schemas.agent_schema import TrajectoryItem

SYSTEM_PROMPT = """You are an embodied robot agent in an AI2-THOR indoor room.
You need to complete the human instruction through multi-turn interaction.
At each step, you must reason from the current first-person observation, action history, and environment feedback.
You must select exactly one action from Available_Actions.

Available_Actions:
- observe
- move forward
- navigate to <object>
- pickup <object>
- put in <object>
- toggle <object>
- open <object>
- close <object>
- end

Before making a decision, think in the following structured fields:
- situation_analysis
- spatial_reasoning
- task_planning
- self_reflection
- verification

Then output exactly one JSON object.
Do not output markdown.
Do not output any action outside Available_Actions.
Prefer action.argument values drawn from legal_navigations or legal_interactions when possible.
Do not invent object names that are not visible or mentioned in history unless you are using observe or move forward to explore."""


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
                "thought": item.thought.model_dump(),
                "action": item.action.model_dump(),
                "action_result": item.action_result.model_dump(),
                "visible_objects": item.visible_objects[:8],
            }
        )

    user_payload = {
        "task_instruction": task_instruction,
        "target_object": target_object,
        "available_actions": HIGH_LEVEL_ACTIONS,
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
            "action": {
                "name": "one of Available_Actions",
                "argument": "object name, indexed name, or objectId when required, else null",
                "confidence": "number in [0, 1]",
            },
        },
        "instruction": "Return exactly one JSON object and no markdown.",
    }
    return SYSTEM_PROMPT, json.dumps(user_payload, ensure_ascii=False, indent=2)
