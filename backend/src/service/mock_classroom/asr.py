"""ASR adapter for mock classroom lecture audio."""

import logging
import mimetypes
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


ASR_ENABLED = _bool_env("MOCK_CLASSROOM_ASR_ENABLED", True)
ASR_URL = (os.getenv("MOCK_CLASSROOM_ASR_URL") or "").strip()
ASR_API_KEY = (
    os.getenv("MOCK_CLASSROOM_ASR_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or ""
).strip()
ASR_MODEL = (os.getenv("MOCK_CLASSROOM_ASR_MODEL") or "whisper-1").strip()
ASR_TIMEOUT_SECONDS = _float_env("MOCK_CLASSROOM_ASR_TIMEOUT_SECONDS", 120.0)

if not ASR_URL and ASR_API_KEY:
    ASR_URL = "https://api.openai.com/v1/audio/transcriptions"


class MockClassroomASR:
    @staticmethod
    def is_configured() -> bool:
        return bool(ASR_ENABLED and ASR_URL and ASR_API_KEY)

    @staticmethod
    async def transcribe(audio_path: Path | None) -> dict:
        if not audio_path or not audio_path.exists():
            return {
                "status": "missing_audio",
                "text": "",
                "message": "没有找到可转写的讲课音频。",
            }

        if not MockClassroomASR.is_configured():
            return {
                "status": "unconfigured",
                "text": "",
                "message": "未配置 ASR，暂时无法把讲课音频转成文字。",
            }

        content_type = mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"
        headers = {"Authorization": f"Bearer {ASR_API_KEY}"}
        data = {"model": ASR_MODEL, "language": "zh"}
        timeout = httpx.Timeout(ASR_TIMEOUT_SECONDS, connect=30.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                with audio_path.open("rb") as file_obj:
                    response = await client.post(
                        ASR_URL,
                        headers=headers,
                        data=data,
                        files={"file": (audio_path.name, file_obj, content_type)},
                    )
            response.raise_for_status()
            payload = response.json()
            text = str(payload.get("text") or payload.get("transcript") or "").strip()
            return {
                "status": "ready" if text else "empty",
                "text": text,
                "message": "ASR 转写完成。" if text else "ASR 没有返回有效文字。",
                "raw": {key: value for key, value in payload.items() if key != "text"},
            }
        except Exception as exc:
            logger.warning("[MockClassroom] ASR failed: %s", exc, exc_info=True)
            return {
                "status": "failed",
                "text": "",
                "message": "音频转写暂不可用，本次会优先使用实时讲稿或降级生成报告。",
            }
