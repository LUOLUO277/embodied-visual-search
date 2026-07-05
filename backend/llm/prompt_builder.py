from __future__ import annotations

import json

from backend.actions.action_space import HIGH_LEVEL_ACTIONS
from backend.schemas.agent_schema import TrajectoryItem

SYSTEM_PROMPT = """You are an embodied visual-search agent in an AI2-THOR indoor room.

Complete the human instruction through observation-action interaction.

Use only:
- the current first-person image,
- optional observe multi-view images,
- visible_interactable_objects refs,
- search memory,
- recent trajectory and last action feedback.

Core rules:
- Do not assume a global map, hidden objects, object ids, or simulator metadata.
- For navigation or interaction with objects, use only refs from visible_interactable_objects.
- A target reference image is only a visual hint, not a visible ref or simulator id.
- If the target is visible and reachable, act on it.
- If uncertain, gather more evidence by observing, moving, rotating, looking, navigating to visible objects, or opening relevant visible containers.
- Avoid repeating failed actions or already checked places.
- End only after the task is completed or repeated evidence shows it cannot be completed.

Movement:
- Navigation actions support *N when repeated small steps are clearly needed: move forward*2/*3, move back*2/*3, move left*2/*3, move right*2/*3.
- Turn actions may also use *N when useful: turn left*2, turn right*2.
- When direction is clear, the path is clear, and the goal is only a short continuous adjustment, prefer a single repeated action instead of outputting the same move step-by-step.
- If a move in that direction just failed, or the path is uncertain, do not use multi-step movement in that direction.
- After blocked feedback, do not repeat the same action blindly.

Initial scan:
- At the beginning, if the target is not clearly visible and the current view is insufficient for a confident next action, prefer observe.
- Do not use observe if the target is already clearly visible and reachable, or the next safe action is obvious.

Thought policy:
Return a concise reasoning summary, not a long chain-of-thought.
- phase: one of initial_scan, visual_search, navigation, interaction, recovery, completion_check.
- situation_analysis: summarize current visual and task evidence.
- spatial_reasoning: explain movement or viewpoint choice; mention front, left, back, or right if observe views are useful.
- memory_reasoning: explain how memory or failed feedback affects the decision, or null.
- verification: use before pickup or end, or when target identity is uncertain, or null.
- decision: explain why the selected action is best.
- In initial_scan, say whether observe is needed; if skipped, explain why current evidence is enough.
- If the target is absent from a checked view or place, update memory_update.ruled_out.
- Before pickup or end, include verification or use phase=completion_check.

Return exactly one JSON object. No markdown."""

EXAMPLES = [
    {
        "thought": {
            "phase": "initial_scan",
            "situation_analysis": "The current first-person view is narrow, the target is not clearly visible, and there is not enough evidence to commit to a route yet.",
            "spatial_reasoning": "A four-direction observe from the current position can reveal whether the useful path or target-like clue is in front, left, back, or right before moving.",
            "memory_reasoning": "No area has been checked yet, so collecting directional evidence is more useful than a blind first move.",
            "verification": None,
            "decision": "Use observe first to collect four-direction views before choosing a route.",
        },
        "memory_update": {
            "checked": None,
            "ruled_out": None,
            "clue": "Initial view is limited; collect four-direction views before committing to a route.",
            "avoid": None,
        },
        "action": {"name": "observe", "argument": None, "confidence": 0.81},
    },
    {
        "thought": {
            "phase": "initial_scan",
            "situation_analysis": "The robot is facing a shelf or counter area. The target is not clearly visible yet, but the visible area may be relevant to the instruction.",
            "spatial_reasoning": "The open path ahead can reveal more of the shelf or counter area if the robot moves forward several steps.",
            "memory_reasoning": "No area has been checked yet, so there is no ruled-out region to avoid.",
            "verification": None,
            "decision": "Move forward efficiently to inspect the likely search area because the current view already suggests a promising route.",
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

OBSERVE_VIEWS_NOTE = (
    "The attached environment images are ordered as: current robot view/front, observe-left, observe-back, observe-right. "
    "The current robot view is the front direction after observe returned to the original heading. "
    "The observe-left, observe-back, and observe-right images were captured from the same position after rotating left 90, 180, and 270 degrees. "
    "Use these images to decide which direction to rotate or move next. "
    "Objects seen only in observe-left, observe-back, or observe-right are directional visual clues; rotate toward that direction before interacting with them using visible refs. "
    "If a target-like object appears in one of these views, record that direction in memory_update.clue, for example 'target-like object appears in left view'."
)


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

    observation_payload = {
        "image": observation.get("current_visual_observation", "attached first-person robot image"),
        "visible_interactable_objects": observation.get("visible_interactable_objects", []),
        "holding": observation.get("holding_objects", []),
        "last_feedback": observation.get("last_action_feedback", {"success": None, "message": last_feedback}),
    }
    if observation.get("observe_views"):
        observe_views = observation.get("observe_views") or {}
        observation_payload["observe_views"] = {
            "note": observe_views.get("note") or OBSERVE_VIEWS_NOTE,
            "views": observe_views.get("views") or [],
        }

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
            "default": "Prefer *2 to *3 for clear repeated navigation or turn adjustments instead of repeating the same action line by line.",
            "cautious": "Use a single step when a direction just failed, the path is uncertain, the robot is near obstacles, or re-observation is needed.",
            "examples": ["move forward*3", "move back*2", "move left*2", "move right*3", "turn left*2", "turn right*2"],
        },
        "observation": observation_payload,
        "memory": {
            "summary": observation.get("memory", {}).get("summary", "Search has not started yet."),
            "checked": observation.get("memory", {}).get("checked", []),
            "ruled_out": observation.get("memory", {}).get("ruled_out", []),
            "avoid": observation.get("memory", {}).get("avoid", []),
            "recent_clues": observation.get("memory", {}).get("recent_clues", []),
        },
        "search_policy": {
            "initial_scan_observe": "In the first step or early search phase, if the target is not clearly visible and the current view does not support a high-confidence move or interaction, prefer observe. Do not force observe when the target is already clearly visible and reachable or the next safe action is obvious.",
            "visual_absence": "If the target is clearly absent from the current viewed area, mark that area as ruled_out and avoid returning there.",
            "container_search": "After opening or inspecting a visible container and not finding the target, mark it as ruled_out.",
            "anti_loop": "Before moving or navigating, compare the destination with memory.ruled_out and memory.avoid.",
            "revisit_rule": "Only revisit a ruled-out area if the viewpoint changed, a container was opened, or new evidence suggests it is useful.",
            "observe_views": "When observe multi-view images are attached, use them to infer which direction is promising, mention that direction in spatial_reasoning, and record directional clues in memory_update.clue or negative directions in memory_update.ruled_out.",
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
                "ruled_out": "place, object, view, or direction that likely does not contain the target, or null",
                "clue": "useful clue found this step; mention left/right/front/back when observe views provide directional evidence, or null",
                "avoid": "what to avoid repeating next, or null",
            },
            "action": {
                "name": "one action from actions; when direction and path are clear, prefer repeated navigation actions such as move forward*3, move right*3, move left*2, move back*2, or turn left*2 instead of repeating one-step moves; avoid multi-step repeats after a failed move or when uncertain",
                "argument": "visible object ref when required, else null",
                "confidence": "number in [0, 1] or null",
            },
        },
    }
    if observation.get("target_reference"):
        user_payload["target_reference"] = {
            "image": "attached target reference image",
            "type_hint": target_reference_type,
            "note": target_reference_note or "The user selected this object from the room view. Use it as the visual target reference. It may not be visible in the current first-person image.",
        }
    elif target_object:
        user_payload["target_object"] = target_object
    if vision_enabled:
        user_payload["vision_enabled"] = True
    return SYSTEM_PROMPT, json.dumps(user_payload, ensure_ascii=False, indent=2)
