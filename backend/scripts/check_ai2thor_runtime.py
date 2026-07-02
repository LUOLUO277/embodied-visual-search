from __future__ import annotations

import os
import platform as py_platform
import sys
import traceback
from pathlib import Path

from PIL import Image
from ai2thor import __version__ as ai2thor_version
from ai2thor.controller import Controller
from ai2thor.platform import CloudRendering


def main() -> int:
    scene = os.getenv("AI2THOR_CHECK_SCENE", "FloorPlan212")
    width = int(os.getenv("AI2THOR_WIDTH", "640"))
    height = int(os.getenv("AI2THOR_HEIGHT", "480"))
    output_path = Path("backend/tmp/check_ai2thor_frame.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller = None
    try:
        print(f"Python version: {sys.version}")
        print(f"ai2thor version: {ai2thor_version}")
        print(f"platform: {CloudRendering.__name__}")
        print(f"scene: {scene}")

        controller = Controller(
            platform=CloudRendering,
            scene=scene,
            width=width,
            height=height,
        )
        event = controller.step(action="RotateRight", degrees=30)
        Image.fromarray(event.frame).save(output_path)

        print("AI2-THOR runtime check succeeded.")
        print(f"Saved frame: {output_path.resolve()}")
        print(f"Host OS: {py_platform.platform()}")
        return 0
    except Exception:
        print("AI2-THOR runtime check failed.")
        print(f"Python version: {sys.version}")
        print(f"ai2thor version: {ai2thor_version}")
        print(f"platform: {CloudRendering.__name__}")
        print(f"scene: {scene}")
        print("Traceback:")
        traceback.print_exc()
        return 1
    finally:
        if controller is not None:
            controller.stop()


if __name__ == "__main__":
    raise SystemExit(main())
