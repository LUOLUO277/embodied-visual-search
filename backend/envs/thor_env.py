from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

import ai2thor.controller as controller_mod
from ai2thor.platform import CloudRendering, Linux64
from PIL import Image

from backend.actions.action_adapter import get_action_payload
from backend.envs.frame_utils import image_to_base64_png, ndarray_to_base64_png, resize_image_longest_side
from backend.schemas.env_schema import (
    AgentPose,
    EnvMetadata,
    ObservationResponse,
    RoomCameraPose,
    RoomHitCandidate,
    RoomObjectInfo,
    RoomObjectSelectResponse,
    RoomViewInspectResponse,
    VisibleObject,
)


class ThorEnv:
    ROOM_CAMERA_MIN_DISTANCE = 1.0
    ROOM_CAMERA_MAX_DISTANCE = 3.5
    ROOM_CAMERA_MIN_PITCH = 8.0
    ROOM_CAMERA_MAX_PITCH = 35.0
    ROOM_CAMERA_TARGET_HEIGHT = 0.95
    TARGET_SNAPSHOT_MAX_SIDE = 384
    TARGET_SNAPSHOT_PADDING = 0.2
    BACKGROUND_TYPES = {"Floor", "Wall", "Ceiling", "Rug", "RoomDecor", "Window", "Blinds", "LightFixture"}
    INTERACTABLE_KEYS = ("pickupable", "openable", "receptacle", "toggleable", "moveable")

    def __init__(self) -> None:
        self.controller: Any | None = None
        self.last_event: Any | None = None
        self.room_camera_event: Any | None = None
        self.current_scene: str | None = None
        self.width = int(os.getenv("AI2THOR_WIDTH", "640"))
        self.height = int(os.getenv("AI2THOR_HEIGHT", "480"))
        self.field_of_view = int(os.getenv("AI2THOR_FIELD_OF_VIEW", "90"))
        self.quality = os.getenv("AI2THOR_QUALITY", "Low")
        self.platform_name = os.getenv("AI2THOR_PLATFORM", "CloudRendering")
        self.x_display = os.getenv("AI2THOR_X_DISPLAY")
        self.force_glcore = os.getenv("AI2THOR_FORCE_GLCORE", "0") == "1"
        self.third_party_camera_id = 0
        self.room_camera_distance = 2.15
        self.room_camera_yaw = 0.0
        self.room_camera_pitch = 18.0
        self.room_camera_field_of_view = 100.0
        self.room_camera_target = {"x": 0.0, "y": 1.0, "z": 0.0}
        self.room_camera_added = False
        self.agent_positions_path = Path("backend/data/agent_positions.json")
        self.media_dir = Path("data/observations")
        self.target_media_dir = Path("data/targets")
        self._agent_positions_cache: dict[str, Any] | None = None

    def platform_label(self) -> str:
        return self.platform_name

    @staticmethod
    def ai2thor_version() -> str:
        try:
            return version("ai2thor")
        except Exception:
            return "unknown"

    def require_controller(self) -> Any:
        if self.controller is None:
            raise RuntimeError("Environment not loaded. Call /api/env/load first.")
        return self.controller

    def require_metadata(self) -> dict[str, Any]:
        if self.last_event is None:
            raise RuntimeError("Environment not loaded. Call /api/env/load first.")
        return self.last_event.metadata

    def _resolve_platform(self) -> Any:
        if self.platform_name == "CloudRendering":
            return CloudRendering
        if self.platform_name == "Linux64":
            return Linux64
        raise ValueError(f"Unsupported AI2THOR_PLATFORM: {self.platform_name}")

    def _patch_unity_command_if_needed(self) -> None:
        if not self.force_glcore:
            return
        if getattr(controller_mod.Controller, "_evs_force_glcore_patched", False):
            return
        original_unity_command = controller_mod.Controller.unity_command

        def patched_unity_command(controller: Any, width: int, height: int, headless: bool) -> list[str]:
            command = original_unity_command(controller, width, height, headless)
            if "-force-glcore" not in command:
                command.append("-force-glcore")
            return command

        controller_mod.Controller.unity_command = patched_unity_command
        controller_mod.Controller._evs_force_glcore_patched = True

    def _ensure_controller(self) -> Any:
        if self.controller is None:
            from ai2thor.controller import Controller

            self._patch_unity_command_if_needed()
            controller_kwargs = {
                "width": self.width,
                "height": self.height,
                "fieldOfView": self.field_of_view,
                "quality": self.quality,
                "renderInstanceSegmentation": True,
            }
            platform_cls = self._resolve_platform()
            if platform_cls is not None:
                controller_kwargs["platform"] = platform_cls
            if self.x_display:
                controller_kwargs["x_display"] = self.x_display
            self.controller = Controller(**controller_kwargs)
        return self.controller

    def _invalidate_controller(self) -> None:
        self.controller = None
        self.last_event = None
        self.room_camera_event = None
        self.room_camera_added = False

    @staticmethod
    def _is_closed_file_error(exc: Exception) -> bool:
        return "write to closed file" in str(exc).lower()

    def load_scene(self, scene: str, task: str | None = None) -> ObservationResponse:
        self.current_scene = scene
        last_error: Exception | None = None
        for attempt in range(2):
            controller = self._ensure_controller()
            self.room_camera_added = False
            self.room_camera_event = None
            try:
                self.last_event = controller.reset(scene=scene)
                self._initialize_room_camera_state()
                self._setup_third_party_camera()
                return self.get_observation(task=task)
            except Exception as exc:
                if self._is_closed_file_error(exc) and attempt == 0:
                    last_error = exc
                    self._invalidate_controller()
                    continue
                raise
        if last_error is not None:
            raise RuntimeError(
                "AI2-THOR controller connection was closed while loading the scene. "
                "The simulator process likely exited or crashed. Reload the scene and try again."
            ) from last_error
        raise RuntimeError("Failed to load scene for an unknown reason.")

    def step(self, action_name: str) -> ObservationResponse:
        payload = get_action_payload(action_name)
        self.perform_controller_action(payload)
        return self.get_observation()

    def perform_controller_action(self, payload: dict[str, Any]) -> ObservationResponse:
        controller = self.require_controller()
        try:
            self.last_event = controller.step(**payload)
        except Exception as exc:
            message = str(exc)
            if "write to closed file" in message.lower():
                self._invalidate_controller()
                raise RuntimeError(
                    "AI2-THOR controller connection was closed while executing the action. "
                    "The simulator process likely exited or crashed. Reload the scene with /api/env/load and try again."
                ) from exc
            raise RuntimeError(f"Failed to execute controller action {payload.get('action')}: {message}") from exc
        return self.get_observation()

    def refresh_room_camera(self) -> None:
        if self.controller is None or self.last_event is None:
            return
        try:
            self._setup_third_party_camera()
        except Exception as exc:
            if self._is_closed_file_error(exc):
                self._invalidate_controller()
                raise RuntimeError(
                    "AI2-THOR controller connection was closed while refreshing the room camera. "
                    "Reload the scene with /api/env/load and try again."
                ) from exc
            raise

    def lookup_agent_position_preset(self, object_id: str) -> dict[str, Any] | None:
        if self._agent_positions_cache is None:
            if self.agent_positions_path.exists():
                self._agent_positions_cache = json.loads(self.agent_positions_path.read_text(encoding="utf-8"))
            else:
                self._agent_positions_cache = {}
        payload = self._agent_positions_cache.get(object_id)
        return payload if isinstance(payload, dict) else None

    def get_observation(self, task: str | None = None) -> ObservationResponse:
        metadata = self.require_metadata()
        self.refresh_room_camera()
        robot_view = ndarray_to_base64_png(self.last_event.frame)
        room_frame = self._get_room_frame()
        room_view = ndarray_to_base64_png(room_frame) if room_frame is not None else None
        return ObservationResponse(
            robot_view=robot_view,
            room_view=room_view,
            metadata=EnvMetadata(
                scene_name=metadata.get("sceneName", self.current_scene or ""),
                agent_pose=self._extract_pose(metadata),
                visible_objects=self._extract_visible_objects(metadata),
                last_action=str(metadata.get("lastAction", "")),
                last_action_success=bool(metadata.get("lastActionSuccess", True)),
                error_message=str(metadata.get("errorMessage", "")),
                inventory_objects=self.get_inventory_object_ids(),
                task=task,
                room_camera=self._extract_room_camera_pose(),
            ),
        )

    def get_visible_object_summaries(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in self._extract_visible_objects(self.require_metadata())]

    def get_inventory_object_ids(self) -> list[str]:
        inventory = self.require_metadata().get("inventoryObjects") or []
        object_ids = []
        for item in inventory:
            object_id = item.get("objectId") or item.get("objectType") or item.get("name")
            if object_id:
                object_ids.append(str(object_id))
        return object_ids

    def find_object_metadata(self, object_id: str) -> dict[str, Any] | None:
        for obj in self.require_metadata().get("objects", []):
            current_id = obj.get("objectId") or obj.get("name") or obj.get("objectType")
            if str(current_id) == str(object_id):
                return obj
        return None

    def resolve_object_candidates(self, argument: str) -> list[dict[str, Any]]:
        normalized = argument.strip().lower()
        current_visible = []
        historical = []
        for obj in self.require_metadata().get("objects", []):
            object_id = str(obj.get("objectId") or obj.get("name") or obj.get("objectType") or "")
            object_type = str(obj.get("objectType") or "")
            name = str(obj.get("name") or "")
            candidate = {
                "objectId": object_id,
                "objectType": object_type,
                "name": name,
                "visible": bool(obj.get("visible")),
            }
            if object_id.lower() == normalized:
                return [candidate]
            matched = object_type.lower() == normalized or name.lower() == normalized
            if matched and candidate["visible"]:
                current_visible.append(candidate)
            elif matched:
                historical.append(candidate)
        return current_visible or historical

    def save_frame(self, frame: Any, prefix: str) -> str:
        self.media_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.media_dir / f"{prefix}_{timestamp}.png"
        Image.fromarray(frame).save(path)
        return str(path.resolve())

    def save_combined_frames(self, frames: list[Any], prefix: str) -> str:
        if not frames:
            return ""
        images = [Image.fromarray(frame) for frame in frames]
        total_width = sum(image.width for image in images)
        max_height = max(image.height for image in images)
        canvas = Image.new("RGB", (total_width, max_height))
        offset_x = 0
        for image in images:
            canvas.paste(image, (offset_x, 0))
            offset_x += image.width
        self.media_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.media_dir / f"{prefix}_{timestamp}.png"
        canvas.save(path)
        return str(path.resolve())

    def orbit_room_camera(self, delta_yaw: float, delta_pitch: float, delta_distance: float = 0.0) -> ObservationResponse:
        self.require_controller()
        self.require_metadata()
        self.room_camera_yaw = (self.room_camera_yaw + delta_yaw) % 360.0
        self.room_camera_pitch = self._clamp(self.room_camera_pitch + delta_pitch, self.ROOM_CAMERA_MIN_PITCH, self.ROOM_CAMERA_MAX_PITCH)
        self.room_camera_distance = self._clamp(self.room_camera_distance + delta_distance, self.ROOM_CAMERA_MIN_DISTANCE, self.ROOM_CAMERA_MAX_DISTANCE)
        self._setup_third_party_camera()
        return self.get_observation()

    def inspect_room_view(self, x: float, y: float) -> RoomViewInspectResponse:
        self.require_metadata()
        room_frame = self._get_room_frame()
        if room_frame is None:
            return RoomViewInspectResponse(hit=False, pixel_x=0, pixel_y=0, normalized_x=x, normalized_y=y, message="Room view is unavailable.")
        pixel_x, pixel_y = self._normalize_pixels(x=x, y=y, frame=room_frame)
        candidates = self._rank_room_hit_candidates(pixel_x=pixel_x, pixel_y=pixel_y)
        selected = candidates[0] if candidates else None
        if not selected:
            return RoomViewInspectResponse(
                hit=False,
                pixel_x=pixel_x,
                pixel_y=pixel_y,
                normalized_x=x,
                normalized_y=y,
                message="No object hit at the current cursor position.",
            )
        metadata = self.find_object_metadata(selected[1])
        if metadata is None:
            return RoomViewInspectResponse(
                hit=False,
                pixel_x=pixel_x,
                pixel_y=pixel_y,
                normalized_x=x,
                normalized_y=y,
                message=f"Object metadata not found for {selected[1]}.",
            )
        return RoomViewInspectResponse(
            hit=True,
            pixel_x=pixel_x,
            pixel_y=pixel_y,
            normalized_x=x,
            normalized_y=y,
            object=self._build_room_object_info(metadata),
            hit_reason=selected[2],
            candidates=[RoomHitCandidate(object_id=item[1], score=round(item[0], 2), reason=item[2]) for item in candidates[:5]],
        )

    def select_room_object(self, x: float, y: float, focus: bool = True, make_snapshot: bool = True) -> RoomObjectSelectResponse:
        inspect_result = self.inspect_room_view(x=x, y=y)
        if not inspect_result.hit or inspect_result.object is None:
            return RoomObjectSelectResponse(
                hit=False,
                pixel_x=inspect_result.pixel_x,
                pixel_y=inspect_result.pixel_y,
                normalized_x=x,
                normalized_y=y,
                message=inspect_result.message or "No object selected.",
                hit_reason=inspect_result.hit_reason,
                candidates=inspect_result.candidates,
                room_view=self.get_observation().room_view,
                room_camera=self._extract_room_camera_pose(),
            )

        object_id = inspect_result.object.object_id
        if focus:
            self.focus_room_camera_on_object(object_id)
        room_view = self.get_observation().room_view
        target_snapshot = None
        target_snapshot_path = None
        if make_snapshot:
            target_snapshot, target_snapshot_path = self._build_target_snapshot(object_id)

        return RoomObjectSelectResponse(
            hit=True,
            pixel_x=inspect_result.pixel_x,
            pixel_y=inspect_result.pixel_y,
            normalized_x=x,
            normalized_y=y,
            object=inspect_result.object,
            room_view=room_view,
            room_camera=self._extract_room_camera_pose(),
            target_snapshot=target_snapshot,
            target_snapshot_path=target_snapshot_path,
            message=f"Selected {inspect_result.object.object_type}.",
            hit_reason=inspect_result.hit_reason,
            candidates=inspect_result.candidates,
        )

    def focus_room_camera_on_object(self, object_id: str) -> ObservationResponse:
        metadata = self.find_object_metadata(object_id)
        if metadata is None:
            raise RuntimeError(f"Object metadata not found for {object_id}.")
        center = self._object_focus_center(metadata)
        size = self._estimate_object_size(metadata)
        self.room_camera_target = center
        if size < 0.35:
            distance = 1.2
        elif size < 0.9:
            distance = 1.7
        else:
            distance = 2.4
        self.room_camera_distance = self._clamp(distance, self.ROOM_CAMERA_MIN_DISTANCE, 3.0)
        self.room_camera_pitch = self._clamp(22.0 if center["y"] < 1.2 else 18.0, self.ROOM_CAMERA_MIN_PITCH, 28.0)
        self._setup_third_party_camera()
        return self.get_observation()

    def reset_room_camera_to_agent(self) -> ObservationResponse:
        self._initialize_room_camera_state()
        self._setup_third_party_camera()
        return self.get_observation()

    def _initialize_room_camera_state(self) -> None:
        metadata = self.require_metadata()
        agent = metadata.get("agent", {})
        position = agent.get("position", {})
        rotation = agent.get("rotation", {})
        agent_yaw = float(rotation.get("y", 0.0))
        forward = self._yaw_forward(agent_yaw)
        self.room_camera_target = {
            "x": float(position.get("x", 0.0)) + forward[0] * 0.75,
            "y": float(position.get("y", 0.0)) + self.ROOM_CAMERA_TARGET_HEIGHT,
            "z": float(position.get("z", 0.0)) + forward[2] * 0.75,
        }
        self.room_camera_distance = 2.15
        self.room_camera_yaw = agent_yaw
        self.room_camera_pitch = 18.0
        self.room_camera_field_of_view = 100.0

    @staticmethod
    def _yaw_forward(yaw_degrees: float) -> tuple[float, float, float]:
        yaw_radians = math.radians(yaw_degrees)
        return (math.sin(yaw_radians), 0.0, math.cos(yaw_radians))

    def _room_camera_transform(self) -> tuple[dict[str, float], dict[str, float]]:
        yaw_radians = math.radians(self.room_camera_yaw)
        pitch_radians = math.radians(self.room_camera_pitch)
        horizontal_distance = self.room_camera_distance * math.cos(pitch_radians)
        vertical_distance = self.room_camera_distance * math.sin(pitch_radians)
        position = {
            "x": self.room_camera_target["x"] - horizontal_distance * math.sin(yaw_radians),
            "y": self.room_camera_target["y"] + vertical_distance,
            "z": self.room_camera_target["z"] - horizontal_distance * math.cos(yaw_radians),
        }
        rotation = self._look_at_rotation(position=position, target=self.room_camera_target)
        return position, rotation

    def _setup_third_party_camera(self) -> None:
        if self.controller is None:
            return
        position, rotation = self._room_camera_transform()
        action = "UpdateThirdPartyCamera" if self.room_camera_added else "AddThirdPartyCamera"
        payload: dict[str, Any] = {
            "action": action,
            "position": position,
            "rotation": rotation,
            "fieldOfView": self.room_camera_field_of_view,
        }
        if self.room_camera_added:
            payload["thirdPartyCameraId"] = self.third_party_camera_id
        try:
            self.room_camera_event = self.controller.step(**payload)
        except Exception as exc:
            if self._is_closed_file_error(exc):
                self._invalidate_controller()
            raise
        self.room_camera_added = True

    def _rank_room_hit_candidates(self, pixel_x: int, pixel_y: int) -> list[tuple[float, str, str]]:
        scores: dict[str, float] = defaultdict(float)
        reasons: dict[str, list[str]] = defaultdict(list)
        segmentation_frame = self._get_third_party_segmentation_frame()
        color_mapping = self._get_color_to_object_id_mapping() or {}
        frame_height = int(segmentation_frame.shape[0]) if segmentation_frame is not None else 0
        frame_width = int(segmentation_frame.shape[1]) if segmentation_frame is not None else 0

        if segmentation_frame is not None:
            exact_object_id = self._segmentation_object_id_at(segmentation_frame, color_mapping, pixel_x, pixel_y)
            if exact_object_id:
                scores[exact_object_id] += 50.0
                reasons[exact_object_id].append("exact segmentation pixel")
            for radius in (0, 2, 4, 6):
                frequency: dict[str, int] = defaultdict(int)
                for sample_x in range(max(0, pixel_x - radius), min(frame_width, pixel_x + radius + 1)):
                    for sample_y in range(max(0, pixel_y - radius), min(frame_height, pixel_y + radius + 1)):
                        object_id = self._segmentation_object_id_at(segmentation_frame, color_mapping, sample_x, sample_y)
                        if object_id:
                            frequency[object_id] += 1
                for object_id, count in frequency.items():
                    scores[object_id] += float(count)
                    reasons[object_id].append(f"segmentation neighborhood r={radius} count={count}")

        detections = self._get_third_party_instance_detections() or {}
        room_frame = self._get_room_frame()
        room_area = float(room_frame.shape[0] * room_frame.shape[1]) if room_frame is not None else 1.0
        for object_id, box in detections.items():
            bbox = self._normalize_bbox(box)
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            if not (x1 <= pixel_x <= x2 and y1 <= pixel_y <= y2):
                continue
            scores[str(object_id)] += 30.0
            reasons[str(object_id)].append("cursor inside detection bbox")
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            distance = math.dist((pixel_x, pixel_y), (center_x, center_y))
            bbox_diagonal = max(1.0, math.dist((x1, y1), (x2, y2)))
            scores[str(object_id)] += max(0.0, 20.0 - (distance / bbox_diagonal) * 20.0)
            area_ratio = max(1.0, (x2 - x1) * (y2 - y1)) / room_area
            if area_ratio > 0.45:
                penalty = 30.0
            elif area_ratio > 0.2:
                penalty = 18.0
            elif area_ratio > 0.08:
                penalty = 10.0
            else:
                penalty = 0.0
            scores[str(object_id)] -= penalty
            if penalty:
                reasons[str(object_id)].append(f"large bbox penalty={penalty:.1f}")

        for object_id in list(scores.keys()):
            metadata = self.find_object_metadata(object_id)
            if metadata is None:
                continue
            object_type = str(metadata.get("objectType") or "")
            if bool(metadata.get("visible")):
                scores[object_id] += 5.0
                reasons[object_id].append("visible object")
            interactable_bonus = sum(1 for key in self.INTERACTABLE_KEYS if bool(metadata.get(key))) * 7.5
            if interactable_bonus:
                scores[object_id] += interactable_bonus
                reasons[object_id].append(f"interactable bonus={interactable_bonus:.1f}")
            if object_type in self.BACKGROUND_TYPES:
                scores[object_id] -= 40.0
                reasons[object_id].append("background type penalty")

        ranked = sorted(((score, object_id, "; ".join(reasons[object_id])) for object_id, score in scores.items()), key=lambda item: (-item[0], item[1]))
        if ranked and self._is_background_object(ranked[0][1]):
            for candidate in ranked[1:]:
                if not self._is_background_object(candidate[1]) and candidate[0] >= ranked[0][0] - 35.0:
                    ranked.insert(0, ranked.pop(ranked.index(candidate)))
                    break
        return ranked

    def _build_target_snapshot(self, object_id: str) -> tuple[str | None, str | None]:
        room_frame = self._get_room_frame()
        if room_frame is None:
            return None, None
        bbox = self._lookup_object_bbox(object_id)
        if bbox is None:
            return None, None
        image = Image.fromarray(room_frame)
        crop = image.crop(bbox)
        crop = resize_image_longest_side(crop, self.TARGET_SNAPSHOT_MAX_SIDE)
        self.target_media_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.target_media_dir / f"target_{timestamp}.png"
        crop.save(path)
        return image_to_base64_png(crop), str(path.resolve())

    def _lookup_object_bbox(self, object_id: str) -> tuple[int, int, int, int] | None:
        detections = self._get_third_party_instance_detections() or {}
        bbox = self._normalize_bbox(detections.get(object_id))
        if bbox is not None:
            return self._pad_bbox(bbox)
        segmentation_frame = self._get_third_party_segmentation_frame()
        color_mapping = self._get_color_to_object_id_mapping() or {}
        if segmentation_frame is None or not color_mapping:
            return None
        color = None
        for candidate_color, candidate_object_id in color_mapping.items():
            if str(candidate_object_id) == str(object_id):
                color = candidate_color
                break
        if color is None:
            return None
        xs: list[int] = []
        ys: list[int] = []
        for y_index in range(int(segmentation_frame.shape[0])):
            for x_index in range(int(segmentation_frame.shape[1])):
                pixel = tuple(int(channel) for channel in segmentation_frame[y_index, x_index][:3])
                if pixel == color:
                    xs.append(x_index)
                    ys.append(y_index)
        if not xs or not ys:
            return None
        return self._pad_bbox((min(xs), min(ys), max(xs), max(ys)))

    def _pad_bbox(self, bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        room_frame = self._get_room_frame()
        if room_frame is None:
            return bbox
        x1, y1, x2, y2 = bbox
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        pad_x = int(round(width * self.TARGET_SNAPSHOT_PADDING))
        pad_y = int(round(height * self.TARGET_SNAPSHOT_PADDING))
        max_width = int(room_frame.shape[1])
        max_height = int(room_frame.shape[0])
        return (
            max(0, x1 - pad_x),
            max(0, y1 - pad_y),
            min(max_width, x2 + pad_x + 1),
            min(max_height, y2 + pad_y + 1),
        )

    def _normalize_pixels(self, x: float, y: float, frame: Any) -> tuple[int, int]:
        frame_height = int(frame.shape[0])
        frame_width = int(frame.shape[1])
        pixel_x = min(frame_width - 1, max(0, int(round(x * (frame_width - 1)))))
        pixel_y = min(frame_height - 1, max(0, int(round(y * (frame_height - 1)))))
        return pixel_x, pixel_y

    def _look_at_rotation(self, position: dict[str, float], target: dict[str, float]) -> dict[str, float]:
        dx = float(target["x"] - position["x"])
        dy = float(target["y"] - position["y"])
        dz = float(target["z"] - position["z"])
        horizontal_distance = max(1e-6, math.hypot(dx, dz))
        yaw = math.degrees(math.atan2(dx, dz)) % 360.0
        pitch = math.degrees(math.atan2(-dy, horizontal_distance))
        return {"x": self._clamp(pitch, self.ROOM_CAMERA_MIN_PITCH, self.ROOM_CAMERA_MAX_PITCH), "y": yaw, "z": 0.0}

    def _object_focus_center(self, metadata: dict[str, Any]) -> dict[str, float]:
        center = self._extract_axis_aligned_center(metadata)
        if center is not None:
            return center
        position = metadata.get("position") or {}
        return {
            "x": float(position.get("x", 0.0)),
            "y": float(position.get("y", 0.0)) + 0.25,
            "z": float(position.get("z", 0.0)),
        }

    def _estimate_object_size(self, metadata: dict[str, Any]) -> float:
        bounds = metadata.get("axisAlignedBoundingBox") or {}
        size = bounds.get("size") or {}
        try:
            return max(float(size.get("x", 0.0)), float(size.get("y", 0.0)), float(size.get("z", 0.0)))
        except (TypeError, ValueError):
            return 0.6

    def _extract_axis_aligned_center(self, metadata: dict[str, Any]) -> dict[str, float] | None:
        bounds = metadata.get("axisAlignedBoundingBox") or {}
        center = bounds.get("center") or {}
        if not center:
            return None
        return {
            "x": float(center.get("x", 0.0)),
            "y": float(center.get("y", 0.0)),
            "z": float(center.get("z", 0.0)),
        }

    def _segmentation_object_id_at(self, segmentation_frame: Any, color_mapping: dict[tuple[int, int, int], Any], pixel_x: int, pixel_y: int) -> str | None:
        color = tuple(int(channel) for channel in segmentation_frame[pixel_y, pixel_x][:3])
        object_id = color_mapping.get(color)
        return str(object_id) if object_id else None

    def _normalize_bbox(self, box: Any) -> tuple[int, int, int, int] | None:
        if not isinstance(box, (list, tuple)) or len(box) < 4:
            return None
        x1, y1, x2, y2 = [int(round(float(value))) for value in box[:4]]
        if x2 <= x1 or y2 <= y1:
            return None
        return x1, y1, x2, y2

    def _is_background_object(self, object_id: str) -> bool:
        metadata = self.find_object_metadata(object_id)
        if metadata is None:
            return False
        return str(metadata.get("objectType") or "") in self.BACKGROUND_TYPES

    def _get_room_frame(self) -> Any | None:
        frames = getattr(self.room_camera_event, "third_party_camera_frames", None)
        if frames:
            return frames[0]
        return None

    def _get_third_party_segmentation_frame(self) -> Any | None:
        event = self.room_camera_event
        for candidate_name in ["third_party_instance_segmentation_frames", "third_party_camera_instance_segmentation_frames"]:
            frames = getattr(event, candidate_name, None)
            if frames:
                return frames[0]
        return None

    def _get_color_to_object_id_mapping(self) -> dict[tuple[int, int, int], Any] | None:
        event = self.room_camera_event
        candidates = [
            getattr(event, "third_party_camera_color_to_object_id", None),
            getattr(event, "third_party_color_to_object_id", None),
            getattr(event, "color_to_object_id", None),
        ]
        for candidate in candidates:
            if isinstance(candidate, list) and candidate:
                mapping = candidate[0]
            else:
                mapping = candidate
            if isinstance(mapping, dict) and mapping:
                normalized: dict[tuple[int, int, int], Any] = {}
                for color, object_id in mapping.items():
                    if isinstance(color, (tuple, list)):
                        normalized[tuple(int(channel) for channel in color[:3])] = object_id
                if normalized:
                    return normalized
        return None

    def _get_third_party_instance_detections(self) -> dict[str, Any] | None:
        event = self.room_camera_event
        for candidate_name in ["third_party_instance_detections2D", "third_party_camera_instance_detections2D"]:
            detections = getattr(event, candidate_name, None)
            if isinstance(detections, list) and detections:
                detection_map = detections[0]
            else:
                detection_map = detections
            if isinstance(detection_map, dict) and detection_map:
                return detection_map
        return None

    def _build_room_object_info(self, metadata: dict[str, Any]) -> RoomObjectInfo:
        attributes: dict[str, Any] = {}
        for key in ["visible", "pickupable", "openable", "isOpen", "toggleable", "isToggled", "receptacle", "moveable"]:
            if key in metadata:
                attributes[key] = metadata.get(key)
        parent_receptacles = metadata.get("parentReceptacles") or []
        if parent_receptacles:
            attributes["parentReceptacles"] = ", ".join(str(item) for item in parent_receptacles)
        distance = metadata.get("distance")
        position = metadata.get("position")
        return RoomObjectInfo(
            object_id=str(metadata.get("objectId") or metadata.get("name") or metadata.get("objectType") or "unknown"),
            object_type=str(metadata.get("objectType") or "Unknown"),
            name=str(metadata.get("name") or metadata.get("objectType") or "Unknown"),
            distance=round(float(distance), 3) if distance is not None else None,
            position=position if isinstance(position, dict) else None,
            attributes=attributes,
        )

    def _extract_room_camera_pose(self) -> RoomCameraPose | None:
        if not self.room_camera_added:
            return None
        position, rotation = self._room_camera_transform()
        return RoomCameraPose(
            position=position,
            rotation=rotation,
            target=self.room_camera_target,
            field_of_view=self.room_camera_field_of_view,
            distance=self.room_camera_distance,
            yaw=self.room_camera_yaw,
            pitch=self.room_camera_pitch,
        )

    @staticmethod
    def _extract_visible_objects(metadata: dict[str, Any]) -> list[VisibleObject]:
        visible_objects = []
        for obj in metadata.get("objects", []):
            if not obj.get("visible"):
                continue
            visible_objects.append(
                VisibleObject(
                    objectId=str(obj.get("objectId") or obj.get("name") or obj.get("objectType") or "unknown"),
                    objectType=str(obj.get("objectType") or "Unknown"),
                    name=str(obj.get("name") or obj.get("objectType") or "Unknown"),
                    visible=True,
                    distance=round(float(obj.get("distance")), 3) if obj.get("distance") is not None else None,
                    pickupable=bool(obj.get("pickupable", False)),
                    receptacle=bool(obj.get("receptacle", False)),
                    openable=bool(obj.get("openable", False)),
                    isOpen=obj.get("isOpen"),
                    toggleable=bool(obj.get("toggleable", False)),
                    isToggled=obj.get("isToggled"),
                    parentReceptacles=[str(item) for item in (obj.get("parentReceptacles") or [])],
                )
            )
        return visible_objects

    @staticmethod
    def _extract_pose(metadata: dict[str, Any]) -> AgentPose:
        agent = metadata.get("agent", {})
        position = agent.get("position", {})
        rotation = agent.get("rotation", {})
        camera_horizon = agent.get("cameraHorizon", 0.0)
        return AgentPose(
            position=position or {"x": 0.0, "y": 0.0, "z": 0.0},
            rotation=rotation or {"x": 0.0, "y": 0.0, "z": 0.0},
            camera_horizon=float(camera_horizon or 0.0),
        )

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return min(maximum, max(minimum, value))


thor_env = ThorEnv()
