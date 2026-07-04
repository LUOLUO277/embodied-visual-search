from __future__ import annotations

import json

from backend.actions.action_space import HIGH_LEVEL_ACTIONS
from backend.schemas.agent_schema import TrajectoryItem

SYSTEM_PROMPT = """You are an embodied visual-search agent in an AI2-THOR indoor room.

Your job is to complete the human instruction through observation-action interaction.

Use only:
- the current first-person image,
- the visible interactable object refs,
- the brief search memory,
- the recent trajectory and last action feedback.

Rules:
- Do not assume a global map, hidden objects, object ids, or simulator metadata.
- For interaction actions, use only refs from visible_interactable_objects.
- If a target reference image is attached, it is only a visual hint for what to look for, not a visible ref or simulator id.
- The target reference image may come from a room view and may not be visible in the current first-person image yet.
- If the target is visible and reachable, act on it.
- If uncertain, gather more evidence by moving, rotating, looking, observing, navigating to a visible object, or opening relevant visible containers.
- Avoid repeating failed actions or already checked places.
- End only after the task is completed or repeated evidence shows it cannot be completed.

Movement efficiency:
- Movement and camera actions are repeatable: move forward, move back, move left, move right, rotate left, rotate right, look up, look down.
- Use the compact form action*N, where N is an integer from 1 to 5, such as move forward*4 or rotate left*3.
- When the path or view direction is clear and you expect the same micro-action to be needed several times, prefer 3-5 repetitions in one step.
- Use 1-2 repetitions only when recently blocked, close to an interaction target, collision risk is high, uncertainty is high, or a small re-observation is needed.
- Do not split obvious consecutive movement or camera actions into many single-step outputs.
- After blocked feedback, do not repeat the same blocked action blindly; choose a smaller repeat, sidestep, rotate, observe, or another route.

Thought policy:
You must output a concise but useful reasoning summary, not a long chain-of-thought.
- phase: one of initial_scan, visual_search, navigation, interaction, recovery, completion_check.
- situation_analysis: required every step. Explain what the current first-person image and visible interactable objects imply for the task.
- spatial_reasoning: use when deciding where to move, rotate, look, observe, or navigate.
- memory_reasoning: use when memory.checked, memory.ruled_out, memory.avoid, recent clues, or failed feedback affect the next decision.
- verification: use before pickup or end, or when target identity is uncertain.
- decision: required every step. Explain why the selected action is the next best action.
- Use null for reasoning fields that are not needed. Do not write long paragraphs.
- In initial_scan, situation_analysis must be especially careful: identify visible task-relevant evidence, whether the target is visible, and the first search direction.
- Before moving toward a place, check memory.ruled_out and memory.avoid.
- If the target is clearly absent from the current viewed area, mark it in memory_update.ruled_out.
- If the previous action failed or repeated search is detected, use phase=recovery.
- Before pickup or end, use phase=completion_check or include verification.

Return exactly one JSON object. No markdown."""

EXAMPLES = [
    {
        "thought": {
            "phase": "initial_scan",
            "situation_analysis": "The robot is facing a shelf or counter area. The target is not clearly visible yet, but the visible area may be relevant to the instruction.",
            "spatial_reasoning": "The open path ahead can reveal more of the shelf or counter area if the robot moves forward several steps.",
            "memory_reasoning": "No area has been checked yet, so there is no ruled-out region to avoid.",
            "verification": None,
            "decision": "Move forward efficiently to inspect the likely search area.",
        },
        "memory_update": {
            "checked": None,
            "ruled_out": None,
            "clue": "A shelf or counter area may contain the target.",
            "avoid": None,
        },
        "action": {"name": "move forward*3", "argument": None, "confidence": 0.76},
    }
]


def build_prompt(
    task_instruction: str,
    target_object: str | None,
    observation: dict,
    trajectory: list[TrajectoryItem],
    last_feedback: str,
    vision_enabled: bool,
    target_reference_type: str | None = None,
    target_reference_note: str | None = None,
) -> tuple[str, str]:
    history = []
    for item in trajectory[-4:]:
        history.append(
            {
                "step": item.step,
                "phase": item.thought.phase,
                "situation": item.thought.situation_analysis,
                "decision": item.thought.decision,
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

    task_text = task_instruction
    if observation.get("target_reference"):
        task_text = (
            f"User instruction: {task_instruction}\n"
            "The target object is shown in the attached target reference image. "
            "Find the matching object from the current first-person robot view and complete the instruction using visible object refs only."
        )

    user_payload = {
        "task": task_text,
        "actions": HIGH_LEVEL_ACTIONS,
        "movement_policy": {
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
            "default": "Prefer *3 to *5 for clear repeated movement or camera adjustment.",
            "cautious": "Use *1 to *2 only when blocked, close to a target or object, uncertain, or needing re-observation.",
            "examples": ["move forward*4", "move right*3", "rotate left*4", "look down*2"],
        },
        "observation": {
            "image": observation.get("current_visual_observation", "attached first-person robot image"),
            "visible_interactable_objects": observation.get("visible_interactable_objects", []),
            "holding": observation.get("holding_objects", []),
            "last_feedback": observation.get("last_action_feedback", {"success": None, "message": last_feedback}),
        },
        "memory": {
            "summary": observation.get("memory", {}).get("summary", "Search has not started yet."),
            "checked": observation.get("memory", {}).get("checked", []),
            "ruled_out": observation.get("memory", {}).get("ruled_out", []),
            "avoid": observation.get("memory", {}).get("avoid", []),
            "recent_clues": observation.get("memory", {}).get("recent_clues", []),
        },
        "search_policy": {
            "visual_absence": "If the target is clearly absent from the current viewed area, mark that area as ruled_out and avoid returning there.",
            "container_search": "After opening or inspecting a visible container and not finding the target, mark it as ruled_out.",
            "anti_loop": "Before moving or navigating, compare the destination with memory.ruled_out and memory.avoid.",
            "revisit_rule": "Only revisit a ruled-out area if the viewpoint changed, a container was opened, or new evidence suggests it is useful.",
        },
        "recent_steps": history,
        "examples": EXAMPLES,
        "output": {
            "thought": {
                "phase": "one of: initial_scan, visual_search, navigation, interaction, recovery, completion_check",
                "situation_analysis": "required concise analysis of current visual and task evidence",
                "spatial_reasoning": "movement or viewpoint reasoning, or null",
                "memory_reasoning": "how memory affects this decision, or null",
                "verification": "target or task verification before pickup or end, or null",
                "decision": "required concise reason for the selected action",
            },
            "memory_update": {
                "checked": "what was checked this step, or null",
                "ruled_out": "place, object, or view that likely does not contain the target, or null",
                "clue": "useful clue found this step, or null",
                "avoid": "what to avoid repeating next, or null",
            },
            "action": {
                "name": "one action from actions; repeatable movement or camera actions should usually use *3-*5 when clear, e.g. move forward*4; use *1-*2 only when cautious",
                "argument": "visible object ref when required, else null",
                "confidence": "number in [0, 1] or null",
            },
        },
    }
    if observation.get("target_reference"):
        user_payload["target_reference"] = {
            "image": "attached target reference image",
            "note": target_reference_note or "The user selected this object from the room view. Use it as the visual target reference. It may not be visible in the current first-person image.",
        }
    elif target_object:
        user_payload["target_object"] = target_object
    if vision_enabled:
        user_payload["vision_enabled"] = True
    return SYSTEM_PROMPT, json.dumps(user_payload, ensure_ascii=False, indent=2)
