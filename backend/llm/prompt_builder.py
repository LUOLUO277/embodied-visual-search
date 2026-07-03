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

Phase guide:
- initial_scan: first 1-2 steps after reset or after entering a new search area.
- visual_search: inspect the current view and decide whether to search, move, open, or rule out an area.
- navigation: move, rotate, look, observe, or navigate to improve viewpoint.
- interaction: open, close, pickup, toggle, or put in a visible ref.
- recovery: handle failed action, blocked movement, contradiction, or repeated search.
- completion_check: verify target match or task completion before pickup or end.

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
    },
    {
        "thought": {
            "phase": "visual_search",
            "situation_analysis": "The current shelf area is visible, and no object matching the target description is present in this view.",
            "spatial_reasoning": "Rotating right can reveal a different area without revisiting the same checked shelf view.",
            "memory_reasoning": "This shelf view should be ruled out unless the viewpoint changes or new evidence appears.",
            "verification": None,
            "decision": "Mark this view as ruled out and rotate to inspect a new area.",
        },
        "memory_update": {
            "checked": "The current visible shelf area was inspected.",
            "ruled_out": "The currently visible shelf area does not contain the target.",
            "clue": None,
            "avoid": "Do not return to the same shelf view unless the viewpoint changes.",
        },
        "action": {"name": "rotate right*3", "argument": None, "confidence": 0.74},
    },
    {
        "thought": {
            "phase": "recovery",
            "situation_analysis": "The previous forward movement failed, so the current direction is likely blocked.",
            "spatial_reasoning": "Rotating can reveal an alternate path without repeating the blocked movement.",
            "memory_reasoning": "The failed forward action should be avoided from this pose.",
            "verification": None,
            "decision": "Rotate left several times to search for a new route.",
        },
        "memory_update": {
            "checked": None,
            "ruled_out": None,
            "clue": None,
            "avoid": "Do not repeat move forward from the current blocked pose.",
        },
        "action": {"name": "rotate left*3", "argument": None, "confidence": 0.73},
    },
    {
        "thought": {
            "phase": "completion_check",
            "situation_analysis": "A visible pickupable object appears to match the target description.",
            "spatial_reasoning": None,
            "memory_reasoning": "No memory entry rules out this object.",
            "verification": "The object is visible, reachable, pickupable, and matches the target description.",
            "decision": "Pick up the matching object using its visible ref.",
        },
        "memory_update": {
            "checked": None,
            "ruled_out": None,
            "clue": "A target-like object is visible and reachable.",
            "avoid": None,
        },
        "action": {"name": "pickup", "argument": "Book_1", "confidence": 0.88},
    },
]


def build_prompt(
    task_instruction: str,
    target_object: str | None,
    observation: dict,
    trajectory: list[TrajectoryItem],
    last_feedback: str,
    vision_enabled: bool,
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

    user_payload = {
        "task": task_instruction,
        "target_object": target_object,
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
    if vision_enabled:
        user_payload["vision_enabled"] = True
    return SYSTEM_PROMPT, json.dumps(user_payload, ensure_ascii=False, indent=2)
