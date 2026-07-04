from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image


def ndarray_to_base64_png(frame: Any) -> str:
    image = Image.fromarray(frame)
    return image_to_base64_png(image)


def image_to_base64_png(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def resize_image_longest_side(image: Image.Image, max_side: int) -> Image.Image:
    if max(image.size) <= max_side:
        return image
    scale = max_side / float(max(image.size))
    return image.resize(
        (max(1, int(round(image.width * scale))), max(1, int(round(image.height * scale)))),
        Image.Resampling.LANCZOS,
    )
