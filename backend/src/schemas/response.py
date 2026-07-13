"""Shared API response envelopes.

Routers should use these helpers for ordinary JSON responses. Streaming and
file-download endpoints can still return FastAPI response objects directly.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = Field(default=200)
    msg: str = Field(default="success")
    data: Any | None = Field(default=None)


def ok(data: Any = None, msg: str = "success", code: int = 200) -> dict:
    payload = {"code": code, "msg": msg}
    if data is not None:
        payload["data"] = data
    return payload


def fail(msg: str, code: int = 400, data: Any = None) -> dict:
    payload = {"code": code, "msg": msg}
    if data is not None:
        payload["data"] = data
    return payload
