from __future__ import annotations

from pydantic import BaseModel


class ActionRequest(BaseModel):
    action: str
    thought: str | None = None
