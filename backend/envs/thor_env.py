from __future__ import annotations

import math
import os
from typing import Any
from importlib.metadata import version

import ai2thor.controller as controller_mod
from ai2thor.platform import CloudRendering, Linux64

from backend.actions.action_adapter import get_action_payload
from backend.envs.frame_utils import ndarray_to_base64_png
from backend.schemas.env_schema import (
    AgentPose,
    EnvMetadata,
    ObservationResponse,
    RoomCameraPose,
    RoomObjectInfo,
    RoomViewInspectResponse,
)


class ThorEnv:
    def __init__(self) -> None:
        self.controller: Any | None = None
        self.last_event: Any | None = None
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

    def platform_label(self) -> str:
        return self.platform_name

    @staticmethod
    def ai2thor_version() -> str:
        try:
            return version("ai2thor")
        except Exception:
            return "unknown"

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

    def load_scene(self, scene: str, task: str | None = None) -> ObservationResponse:
        controller = self._ensure_controller()
        self.current_scene = scene
        self.room_camera_added = False
        self.last_event = controller.reset(scene=scene)
        self._initialize_room_camera_state()
        self._setup_third_party_camera()
        return self.get_observation(task=task)

    def _initialize_room_camera_state(self) -> None:
        if self.last_event is None:
            return

        metadata = self.last_event.metadata
        agent = metadata.get("agent", {})
        position = agent.get("position", {})
        rotation = agent.get("rotation", {})
        agent_yaw = float(rotation.get("y", 0.0))
        forward = self._yaw_forward(agent_yaw)
        self.room_camera_target = {
            "x": float(position.get("x", 0.0)) + forward[0] * 0.75,
            "y": float(position.get("y", 0.0)) + 0.95,
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
        rotation = {
            "x": self.room_camera_pitch,
            "y": self.room_camera_yaw,
            "z": 0.0,
        }
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

        self.last_event = self.controller.step(**payload)
        self.room_camera_added = True

    def orbit_room_camera(self, delta_yaw: float, delta_pitch: float) -> ObservationResponse:
        if self.controller is None or self.last_event is None:
            raise RuntimeError("Environment not loaded. Call /api/env/load first.")

        self.room_camera_yaw = (self.room_camera_yaw + delta_yaw) % 360.0
        self.room_camera_pitch = min(42.0, max(6.0, self.room_camera_pitch + delta_pitch))
        self._setup_third_party_camera()
        return self.get_observation()

    def step(self, action_name: str) -> ObservationResponse:
        if self.controller is None:
            raise RuntimeError("Environment not loaded. Call /api/env/load first.")

        payload = get_action_payload(action_name)
        self.last_event = self.controller.step(**payload)
        return self.get_observation()

    def inspect_room_view(self, x: float, y: float) -> RoomViewInspectResponse:
        if self.last_event is None:
            raise RuntimeError("Environment not loaded. Call /api/env/load first.")

        room_frame = self._get_room_frame()
        if room_frame is None:
            return RoomViewInspectResponse(
                hit=False,
                pixel_x=0,
                pixel_y=0,
                normalized_x=x,
                normalized_y=y,
                message="Room view is unavailable.",
            )

        frame_height = int(room_frame.shape[0])
        frame_width = int(room_frame.shape[1])
        pixel_x = min(frame_width - 1, max(0, int(round(x * (frame_width - 1)))))
        pixel_y = min(frame_height - 1, max(0, int(round(y * (frame_height - 1)))))

        object_id = self._lookup_room_object_id(pixel_x=pixel_x, pixel_y=pixel_y)
        if not object_id:
            return RoomViewInspectResponse(
                hit=False,
                pixel_x=pixel_x,
                pixel_y=pixel_y,
                normalized_x=x,
                normalized_y=y,
                message="No object hit at the current cursor position.",
            )

        metadata = self._find_object_metadata(object_id)
        if metadata is None:
            return RoomViewInspectResponse(
                hit=False,
                pixel_x=pixel_x,
                pixel_y=pixel_y,
                normalized_x=x,
                normalized_y=y,
                message=f"Object metadata not found for {object_id}.",
            )

        return RoomViewInspectResponse(
            hit=True,
            pixel_x=pixel_x,
            pixel_y=pixel_y,
            normalized_x=x,
            normalized_y=y,
            object=self._build_room_object_info(metadata),
        )

    def _lookup_room_object_id(self, pixel_x: int, pixel_y: int) -> str | None:
        segmentation_frame = self._get_third_party_segmentation_frame()
        if segmentation_frame is not None:
            color = tuple(int(channel) for channel in segmentation_frame[pixel_y, pixel_x][:3])
            color_mapping = self._get_color_to_object_id_mapping()
            if color_mapping and color in color_mapping:
                return str(color_mapping[color])

        detections = self._get_third_party_instance_detections()
        if detections:
            hit_candidates: list[tuple[float, str]] = []
            for object_id, box in detections.items():
                if not isinstance(box, (list, tuple)) or len(box) < 4:
                    continue
                x1, y1, x2, y2 = [float(value) for value in box[:4]]
                if x1 <= pixel_x <= x2 and y1 <= pixel_y <= y2:
                    area = max(1.0, (x2 - x1) * (y2 - y1))
                    hit_candidates.append((area, str(object_id)))
            if hit_candidates:
                hit_candidates.sort(key=lambda item: item[0])
                return hit_candidates[0][1]

        return self._lookup_room_object_id_by_projection(pixel_x=pixel_x, pixel_y=pixel_y)

    def _lookup_room_object_id_by_projection(self, pixel_x: int, pixel_y: int) -> str | None:
        projection_candidates = []
        frame_width = self.width
        frame_height = self.height
        threshold_px = max(26.0, min(frame_width, frame_height) * 0.08)
        for obj in self.last_event.metadata.get("objects", []):
            position = obj.get("position")
            if not isinstance(position, dict):
                continue
            projection = self._project_point_to_room_view(position)
            if projection is None:
                continue
            projected_x, projected_y, depth = projection
            pixel_distance = math.dist((pixel_x, pixel_y), (projected_x, projected_y))
            if pixel_distance > threshold_px:
                continue
            score = pixel_distance + depth * 6.0
            object_id = obj.get("objectId") or obj.get("name") or obj.get("objectType")
            projection_candidates.append((score, str(object_id)))

        if not projection_candidates:
            return None

        projection_candidates.sort(key=lambda item: item[0])
        return projection_candidates[0][1]

    def _project_point_to_room_view(self, position: dict[str, Any]) -> tuple[float, float, float] | None:
        camera_position, _ = self._room_camera_transform()
        forward = self._room_camera_forward()
        world_up = (0.0, 1.0, 0.0)
        right = self._normalize(self._cross(world_up, forward))
        up = self._normalize(self._cross(forward, right))

        relative = (
            float(position.get("x", 0.0)) - camera_position["x"],
            float(position.get("y", 0.0)) - camera_position["y"],
            float(position.get("z", 0.0)) - camera_position["z"],
        )
        camera_x = self._dot(relative, right)
        camera_y = self._dot(relative, up)
        camera_z = self._dot(relative, forward)
        if camera_z <= 0.05:
            return None

        focal_length = (self.width * 0.5) / math.tan(math.radians(self.room_camera_field_of_view) * 0.5)
        screen_x = (self.width * 0.5) + (camera_x * focal_length / camera_z)
        screen_y = (self.height * 0.5) - (camera_y * focal_length / camera_z)
        if screen_x < 0 or screen_x > self.width or screen_y < 0 or screen_y > self.height:
            return None

        return screen_x, screen_y, camera_z

    def _room_camera_forward(self) -> tuple[float, float, float]:
        yaw_radians = math.radians(self.room_camera_yaw)
        pitch_radians = math.radians(self.room_camera_pitch)
        return self._normalize(
            (
                math.sin(yaw_radians) * math.cos(pitch_radians),
                -math.sin(pitch_radians),
                math.cos(yaw_radians) * math.cos(pitch_radians),
            )
        )

    @staticmethod
    def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    @staticmethod
    def _normalize(vector: tuple[float, float, float]) -> tuple[float, float, float]:
        length = math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
        if length <= 1e-6:
            return (0.0, 0.0, 1.0)
        return (vector[0] / length, vector[1] / length, vector[2] / length)

    def _get_room_frame(self) -> Any | None:
        frames = getattr(self.last_event, "third_party_camera_frames", None)
        if frames:
            return frames[0]
        return None

    def _get_third_party_segmentation_frame(self) -> Any | None:
        candidate_names = [
            "third_party_instance_segmentation_frames",
            "third_party_camera_instance_segmentation_frames",
        ]
        for candidate_name in candidate_names:
            frames = getattr(self.last_event, candidate_name, None)
            if frames:
                return frames[0]
        return None

    def _get_color_to_object_id_mapping(self) -> dict[tuple[int, int, int], Any] | None:
        candidates = [
            getattr(self.last_event, "third_party_camera_color_to_object_id", None),
            getattr(self.last_event, "third_party_color_to_object_id", None),
            getattr(self.last_event, "color_to_object_id", None),
        ]
        for candidate in candidates:
            if isinstance(candidate, list) and candidate:
                mapping = candidate[0]
            else:
                mapping = candidate
            if isinstance(mapping, dict) and mapping:
                normalized: dict[tuple[int, int, int], Any] = {}
                for color, object_id in mapping.items():
                    if isinstance(color, tuple):
                        normalized[tuple(int(channel) for channel in color[:3])] = object_id
                    elif isinstance(color, list):
                        normalized[tuple(int(channel) for channel in color[:3])] = object_id
                if normalized:
                    return normalized
        return None

    def _get_third_party_instance_detections(self) -> dict[str, Any] | None:
        candidate_names = [
            "third_party_instance_detections2D",
            "third_party_camera_instance_detections2D",
        ]
        for candidate_name in candidate_names:
            detections = getattr(self.last_event, candidate_name, None)
            if isinstance(detections, list) and detections:
                detection_map = detections[0]
            else:
                detection_map = detections
            if isinstance(detection_map, dict) and detection_map:
                return detection_map
        return None

    def _find_object_metadata(self, object_id: str) -> dict[str, Any] | None:
        if self.last_event is None:
            return None
        for obj in self.last_event.metadata.get("objects", []):
            current_id = obj.get("objectId") or obj.get("name") or obj.get("objectType")
            if str(current_id) == object_id:
                return obj
        return None

    def _build_room_object_info(self, metadata: dict[str, Any]) -> RoomObjectInfo:
        attributes: dict[str, Any] = {}
        for key in [
            "visible",
            "pickupable",
            "openable",
            "isOpen",
            "toggleable",
            "isToggled",
            "receptacle",
            "moveable",
            "sliceable",
            "isSliced",
            "dirtyable",
            "isDirty",
            "cookable",
            "isCooked",
            "breakable",
            "canFillWithLiquid",
            "isFilledWithLiquid",
        ]:
            if key in metadata:
                attributes[key] = metadata.get(key)

        parent_receptacles = metadata.get("parentReceptacles") or []
        if parent_receptacles:
            attributes["parentReceptacles"] = ", ".join(str(item) for item in parent_receptacles)

        receptacle_object_ids = metadata.get("receptacleObjectIds") or []
        if receptacle_object_ids:
            attributes["containsCount"] = len(receptacle_object_ids)

        salient_materials = metadata.get("salientMaterials") or []
        if salient_materials:
            attributes["materials"] = ", ".join(str(item) for item in salient_materials)

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

    def get_observation(self, task: str | None = None) -> ObservationResponse:
        if self.last_event is None:
            raise RuntimeError("Environment not loaded. Call /api/env/load first.")

        metadata = self.last_event.metadata
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
                last_action_success=bool(metadata.get("lastActionSuccess", True)),
                error_message=metadata.get("errorMessage", ""),
                task=task,
                room_camera=self._extract_room_camera_pose(),
            ),
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
    def _extract_visible_objects(metadata: dict) -> list[str]:
        visible_objects = []
        for obj in metadata.get("objects", []):
            if obj.get("visible"):
                object_id = obj.get("objectId") or obj.get("name") or obj.get("objectType")
                visible_objects.append(str(object_id))
        return visible_objects

    @staticmethod
    def _extract_pose(metadata: dict) -> AgentPose:
        agent = metadata.get("agent", {})
        position = agent.get("position", {})
        rotation = agent.get("rotation", {})
        camera_horizon = agent.get("cameraHorizon", 0.0)
        return AgentPose(
            position=position or {"x": 0.0, "y": 0.0, "z": 0.0},
            rotation=rotation or {"x": 0.0, "y": 0.0, "z": 0.0},
            camera_horizon=float(camera_horizon or 0.0),
        )


thor_env = ThorEnv()
