import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import ai2thor.controller as controller_mod
import uvicorn

os.environ.setdefault("AI2THOR_PLATFORM", "Linux64")
os.environ.setdefault("AI2THOR_X_DISPLAY", ":0")
os.environ.setdefault("AI2THOR_FORCE_GLCORE", "1")
os.environ.setdefault("DISPLAY", ":0")
os.environ.setdefault("GALLIUM_DRIVER", "d3d12")
os.environ.setdefault("MESA_D3D12_DEFAULT_ADAPTER_NAME", "NVIDIA")

orig = controller_mod.Controller.unity_command


def patched(self, width, height, headless):
    cmd = orig(self, width, height, headless)
    if "-force-glcore" not in cmd:
        cmd.append("-force-glcore")
    return cmd


controller_mod.Controller.unity_command = patched
uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)