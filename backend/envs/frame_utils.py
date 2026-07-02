from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image


def ndarray_to_base64_png(frame: Any) -> str:
    image = Image.fromarray(frame)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
