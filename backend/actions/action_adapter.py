from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from backend.actions import base_action
from backend.actions.object_resolver import ObjectResolver
from backend.envs.frame_utils import ndarray_to_base64_png
from backend.schemas.action_schema import HighLevelAction
from backend.schemas.agent_schema import AgentActionResult


@dataclass
class AdaptedAction:
    kind: str
    payload: dict[str, Any] | None = None
    message: str = ""


MANUAL_ACTION_PAYLOADS = {
    "MoveAhead": {"action": "MoveAhead", "moveMagnitude": 0.25},
    "MoveBack": {"action": "MoveBack", "moveMagnitude": 0.25},
    "MoveLeft": {"action": "MoveLeft", "moveMagnitude": 0.25},
    "MoveRight": {"action": "MoveRight", "moveMagnitude": 0.25},
    "RotateLeft": {"action": "RotateLeft", "degrees": 30},
    "RotateRight": {"action": "RotateRight", "degrees": 30},
    "LookUp": {"action": "LookUp", "degrees": 15},
    "LookDown": {"action": "LookDown", "degrees": 15},
    "Done": {"action": "Done"},
}


def get_action_payload(action_name: str) -> dict[str, Any]:
    if action_name not in MANUAL_ACTION_PAYLOADS:
        raise ValueError(f"Unsupported action: {action_name}")
    return MANUAL_ACTION_PAYLOADS[action_name]


def adapt_high_level_action(action: HighLevelAction, env: Any) -> AdaptedAction:
    normalized = action.name
    if normalized == "end":
        return AdaptedAction(kind="end")
    if normalized == "move forward":
        return AdaptedAction(kind="controller_step", payload={"action": "MoveAhead", "moveMagnitude": 0.25})
    if normalized == "observe":
        return AdaptedAction(kind="observe")
    if normalized == "navigate to":
        return AdaptedAction(kind="navigate", payload={"argument": action.argument})
    if normalized in {"pickup", "put in", "toggle", "open", "close"}:
        return AdaptedAction(kind="interaction", payload={"name": normalized, "argument": action.argument})
    raise ValueError(f"Unsupported high-level action: {action.name}")


def execute_high_level_action(action: HighLevelAction, env: Any) -> AgentActionResult:
    adapted = adapt_high_level_action(action, env)
    if adapted.kind == "end":
        return _build_result(action=action, env=env, success=True, executed=False, done=True, message="LLM ended the task.")
    if adapted.kind == "controller_step":
        env.perform_controller_action(adapted.payload or {})
        return _result_from_event(action=action, env=env, executed=True, adapted_action=adapted.payload)
    if adapted.kind == "observe":
        return _execute_observe(action, env)
    if adapted.kind == "navigate":
        return _execute_navigate(action, env)
    if adapted.kind == "interaction":
        return _execute_interaction(action, env)
    raise ValueError(f"Unsupported adapted action kind: {adapted.kind}")


def _execute_navigate(action: HighLevelAction, env: Any) -> AgentActionResult:
    controller = env.require_controller()
    metadata = env.require_metadata()
    resolver = ObjectResolver(metadata)
    resolved = resolver.resolve(action.argument)
    if not resolved.success or resolved.resolved is None:
        return _build_result(
            action=action,
            env=env,
            success=False,
            message=resolved.message,
            error=resolved.message,
            error_type="illegal_action",
            executed=False,
        )

    target = resolved.resolved
    for candidate in _candidate_navigation_poses(env, target.metadata)[:5]:
        event = base_action.teleport(
            controller,
            position=candidate["position"],
            rotation={"y": candidate["rotation"]},
            horizon=candidate["horizon"],
            standing=True,
        )
        env.last_event = event
        if event.metadata.get("lastActionSuccess", True):
            env.refresh_room_camera()
            return _result_from_event(
                action=action,
                env=env,
                executed=True,
                adapted_action={"action": "TeleportFull", **candidate},
                selected_object=target.metadata,
                message=f"Navigated to {target.indexed_name}.",
            )
    message = f"Failed to navigate to {target.indexed_name}."
    return _build_result(
        action=action,
        env=env,
        success=False,
        message=env.require_metadata().get("errorMessage") or message,
        error=env.require_metadata().get("errorMessage") or message,
        error_type="action_error",
        executed=True,
        selected_object=target.metadata,
    )


def _candidate_navigation_poses(env: Any, target_object: dict[str, Any]) -> list[dict[str, Any]]:
    presets = env.lookup_agent_position_preset(str(target_object.get("objectId") or ""))
    if presets:
        return [
            {
                "position": presets.get("agent_teleport_position") or {},
                "rotation": float((presets.get("agent_rotation") or {}).get("y", presets.get("agent_rotation", 0.0))),
                "horizon": float(presets.get("agent_cameraHorizon", 60.0)),
            }
        ]

    controller = env.require_controller()
    pose_event = controller.step(
        action="GetInteractablePoses",
        objectId=target_object["objectId"],
        horizons=[60, 30, 0],
        standings=[True],
    )
    poses = pose_event.metadata.get("actionReturn") or []
    candidates: list[dict[str, Any]] = []
    for pose in poses:
        position = {key: float(pose.get(key, 0.0)) for key in ["x", "y", "z"]}
        candidates.append(
            {
                "position": position,
                "rotation": look_at_rotation(position, target_object.get("position") or {}),
                "horizon": float(pose.get("horizon", 60.0) or 60.0),
            }
        )
    if candidates:
        return candidates

    reachable_event = controller.step(action="GetReachablePositions")
    reachable = reachable_event.metadata.get("actionReturn") or []
    ranked = sorted(
        reachable,
        key=lambda pos: math.dist(
            (float(pos.get("x", 0.0)), float(pos.get("y", 0.0)), float(pos.get("z", 0.0))),
            (
                float((target_object.get("position") or {}).get("x", 0.0)),
                float((target_object.get("position") or {}).get("y", 0.0)),
                float((target_object.get("position") or {}).get("z", 0.0)),
            ),
        ),
    )
    for pos in ranked[:5]:
        position = {key: float(pos.get(key, 0.0)) for key in ["x", "y", "z"]}
        candidates.append(
            {
                "position": position,
                "rotation": look_at_rotation(position, target_object.get("position") or {}),
                "horizon": 60.0,
            }
        )
    return candidates


def _execute_observe(action: HighLevelAction, env: Any) -> AgentActionResult:
    controller = env.require_controller()
    frames = []
    sub_paths = []
    for label in ["left", "back", "right"]:
        event = base_action.rotate_left(controller, 90)
        env.last_event = event
        sub_paths.append(env.save_frame(event.frame, prefix=f"observe_{label}"))
        frames.append(event.frame)
    event = base_action.rotate_left(controller, 90)
    env.last_event = event
    env.refresh_room_camera()
    combined_path = env.save_combined_frames(frames, prefix="observe_combined") if frames else ""
    return _result_from_event(
        action=action,
        env=env,
        executed=True,
        adapted_action={"action": "observe"},
        message="Observation captured.",
        image_paths=[path for path in [combined_path, *sub_paths] if path],
    )


def _execute_interaction(action: HighLevelAction, env: Any) -> AgentActionResult:
    controller = env.require_controller()
    metadata = env.require_metadata()
    resolver = ObjectResolver(metadata)
    resolved = resolver.resolve(action.argument)
    if not resolved.success or resolved.resolved is None:
        return _build_result(
            action=action,
            env=env,
            success=False,
            message=resolved.message,
            error=resolved.message,
            error_type="illegal_action",
            executed=False,
        )
    target = resolved.resolved
    target_meta = target.metadata
    name = action.name

    if name == "open":
        if not target_meta.get("openable"):
            return _illegal(action, env, target_meta, "Object is not openable.")
        if not target_meta.get("visible"):
            return _illegal(action, env, target_meta, "Object is not visible; navigate to it first.")
        env.last_event = base_action.open_object(controller, target.object_id)
    elif name == "close":
        if not target_meta.get("openable"):
            return _illegal(action, env, target_meta, "Object is not openable.")
        if not target_meta.get("isOpen"):
            return _illegal(action, env, target_meta, "Object is already closed.")
        env.last_event = base_action.close_object(controller, target.object_id)
    elif name == "pickup":
        if not target_meta.get("pickupable"):
            return _illegal(action, env, target_meta, "Object is not pickupable.")
        env.last_event = base_action.pickup(controller, target.object_id)
    elif name == "put in":
        inventory = metadata.get("inventoryObjects") or []
        if not inventory:
            return _illegal(action, env, target_meta, "Inventory is empty; pickup an object first.")
        if target_meta.get("openable") and not target_meta.get("isOpen"):
            return _illegal(action, env, target_meta, "Target receptacle is closed; open it first.")
        if not target_meta.get("receptacle"):
            return _illegal(action, env, target_meta, "Target object is not a receptacle.")
        env.last_event = base_action.put_in(controller, target.object_id)
    elif name == "toggle":
        if not target_meta.get("toggleable"):
            return _illegal(action, env, target_meta, "Object is not toggleable.")
        env.last_event = base_action.toggle(controller, target.object_id, bool(target_meta.get("isToggled")))
    else:
        raise ValueError(f"Unsupported interaction action: {name}")

    env.refresh_room_camera()
    return _result_from_event(action=action, env=env, executed=True, adapted_action={"action": name, "objectId": target.object_id}, selected_object=target_meta)


def _illegal(action: HighLevelAction, env: Any, selected_object: dict[str, Any] | None, message: str) -> AgentActionResult:
    return _build_result(
        action=action,
        env=env,
        success=False,
        message=message,
        error=message,
        error_type="illegal_action",
        executed=False,
        selected_object=selected_object,
    )


def _result_from_event(
    action: HighLevelAction,
    env: Any,
    executed: bool,
    adapted_action: dict[str, Any] | None,
    selected_object: dict[str, Any] | None = None,
    message: str | None = None,
    image_paths: list[str] | None = None,
) -> AgentActionResult:
    metadata = env.require_metadata()
    success = bool(metadata.get("lastActionSuccess", True))
    error_message = str(metadata.get("errorMessage") or "")
    return _build_result(
        action=action,
        env=env,
        success=success,
        message=message or error_message or ("success" if success else "failed"),
        error=error_message or None,
        error_type=None if success else "action_error",
        executed=executed,
        selected_object=selected_object,
        adapted_action=adapted_action,
        image_paths=image_paths or [],
    )


def _build_result(
    action: HighLevelAction,
    env: Any,
    success: bool,
    message: str,
    executed: bool,
    done: bool = False,
    error: str | None = None,
    error_type: str | None = None,
    selected_object: dict[str, Any] | None = None,
    adapted_action: dict[str, Any] | None = None,
    image_paths: list[str] | None = None,
) -> AgentActionResult:
    metadata = env.require_metadata()
    resolver = ObjectResolver(metadata)
    selected_object_id = None if selected_object is None else str(selected_object.get("objectId") or "")
    selected_object_type = None if selected_object is None else str(selected_object.get("objectType") or "")
    return AgentActionResult(
        success=success,
        action_name=action.name,
        argument=action.argument,
        normalized_action=action.name,
        selected_object_id=selected_object_id,
        selected_object_type=selected_object_type,
        message=message,
        error_type=error_type,
        error=error,
        executed=executed,
        done=done,
        adapted_action=adapted_action,
        image_paths=image_paths or [],
        frame_available=bool(getattr(env.last_event, "frame", None) is not None),
        legal_navigations=resolver.legal_navigations(),
        legal_interactions=resolver.legal_interactions(),
        metadata_summary=resolver.metadata_summary(),
    )


def look_at_rotation(agent_pos: dict[str, Any], object_pos: dict[str, Any]) -> float:
    dx = float(object_pos.get("x", 0.0)) - float(agent_pos.get("x", 0.0))
    dz = float(object_pos.get("z", 0.0)) - float(agent_pos.get("z", 0.0))
    return (math.degrees(math.atan2(dx, dz)) + 360.0) % 360.0


def summarize_visible_objects(env: Any) -> list[dict[str, Any]]:
    metadata = env.require_metadata()
    return [
        {
            "objectId": str(obj.get("objectId") or ""),
            "objectType": str(obj.get("objectType") or ""),
            "visible": bool(obj.get("visible")),
            "distance": obj.get("distance"),
        }
        for obj in metadata.get("objects") or []
        if obj.get("visible")
    ]
