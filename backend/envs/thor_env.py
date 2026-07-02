from __future__ import annotations

import os
from typing import Any
from importlib.metadata import version

import ai2thor.controller as controller_mod
from ai2thor.platform import CloudRendering, Linux64

from backend.actions.action_adapter import get_action_payload
from backend.envs.frame_utils import ndarray_to_base64_png
from backend.schemas.env_schema import AgentPose, EnvMetadata, ObservationResponse


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
        self.last_event = controller.reset(scene=scene)
        self._setup_third_party_camera()
        return self.get_observation(task=task)

    def _setup_third_party_camera(self) -> None:
        if self.controller is None:
            return

        self.last_event = self.controller.step(
            action="AddThirdPartyCamera",
            position={"x": 0.0, "y": 2.2, "z": -2.0},
            rotation={"x": 55.0, "y": 0.0, "z": 0.0},
            fieldOfView=100,
        )

    def step(self, action_name: str) -> ObservationResponse:
        if self.controller is None:
            raise RuntimeError("Environment not loaded. Call /api/env/load first.")

        payload = get_action_payload(action_name)
        self.last_event = self.controller.step(**payload)
        return self.get_observation()

    def get_observation(self, task: str | None = None) -> ObservationResponse:
        if self.last_event is None:
            raise RuntimeError("Environment not loaded. Call /api/env/load first.")

        metadata = self.last_event.metadata
        robot_view = ndarray_to_base64_png(self.last_event.frame)
        room_frame = None
        if getattr(self.last_event, "third_party_camera_frames", None):
            room_frame = ndarray_to_base64_png(self.last_event.third_party_camera_frames[0])

        return ObservationResponse(
            robot_view=robot_view,
            room_view=room_frame,
            metadata=EnvMetadata(
                scene_name=metadata.get("sceneName", self.current_scene or ""),
                agent_pose=self._extract_pose(metadata),
                visible_objects=self._extract_visible_objects(metadata),
                last_action_success=bool(metadata.get("lastActionSuccess", True)),
                error_message=metadata.get("errorMessage", ""),
                task=task,
            ),
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
