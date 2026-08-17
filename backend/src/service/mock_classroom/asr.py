"""ASR adapter for mock classroom lecture audio."""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

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
ASR_PROVIDER = (os.getenv("MOCK_CLASSROOM_ASR_PROVIDER") or "funasr").strip().lower()
ASR_URL = (os.getenv("MOCK_CLASSROOM_ASR_URL") or "").strip()
ASR_API_KEY = (
    os.getenv("MOCK_CLASSROOM_ASR_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or ""
).strip()
ASR_MODEL = (os.getenv("MOCK_CLASSROOM_ASR_MODEL") or "whisper-1").strip()
ASR_TIMEOUT_SECONDS = _float_env("MOCK_CLASSROOM_ASR_TIMEOUT_SECONDS", 120.0)
FUNASR_MODEL = (os.getenv("MOCK_CLASSROOM_FUNASR_MODEL") or "paraformer-zh").strip()
FUNASR_VAD_MODEL = (os.getenv("MOCK_CLASSROOM_FUNASR_VAD_MODEL") or "fsmn-vad").strip()
FUNASR_PUNC_MODEL = (os.getenv("MOCK_CLASSROOM_FUNASR_PUNC_MODEL") or "ct-punc").strip()
FUNASR_DEVICE = (os.getenv("MOCK_CLASSROOM_FUNASR_DEVICE") or "cpu").strip()
FUNASR_HUB = (os.getenv("MOCK_CLASSROOM_FUNASR_HUB") or "ms").strip()

if not ASR_URL and ASR_API_KEY:
    ASR_URL = "https://api.openai.com/v1/audio/transcriptions"

_funasr_model = None


class MockClassroomASR:
    @staticmethod
    def is_configured() -> bool:
        if not ASR_ENABLED:
            return False
        if ASR_PROVIDER in {"funasr", "local", "auto"}:
            return True
        if ASR_PROVIDER in {"openai", "remote"}:
            return bool(ASR_URL and ASR_API_KEY)
        return bool(ASR_URL and ASR_API_KEY)

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

        if ASR_PROVIDER in {"funasr", "local", "auto"}:
            result = await MockClassroomASR._transcribe_with_funasr(audio_path)
            if result.get("status") != "failed" or ASR_PROVIDER != "auto":
                return result

        if not ASR_URL or not ASR_API_KEY:
            return {
                "status": "unconfigured",
                "text": "",
                "message": "未配置远程 ASR，暂时无法把讲课音频转成文字。",
            }

        return await MockClassroomASR._transcribe_with_openai(audio_path)

    @staticmethod
    async def _transcribe_with_funasr(audio_path: Path) -> dict:
        try:
            model = await MockClassroomASR._get_funasr_model()
            result = await MockClassroomASR._run_funasr_generate(model, audio_path)
            text = MockClassroomASR._extract_funasr_text(result)
            return {
                "status": "ready" if text else "empty",
                "text": text,
                "message": "本地 ASR 转写完成。" if text else "本地 ASR 没有返回有效文字。",
                "raw": MockClassroomASR._compact_raw_result(result),
            }
        except ImportError:
            logger.warning("[MockClassroom] FunASR is not installed", exc_info=True)
            return {
                "status": "failed",
                "text": "",
                "message": "本地 ASR 依赖未安装，暂时无法把音频转成文字。",
            }
        except Exception as exc:
            logger.warning("[MockClassroom] FunASR failed: %s", exc, exc_info=True)
            return {
                "status": "failed",
                "text": "",
                "message": "本地 ASR 转写暂不可用，本次会优先使用实时讲稿或降级生成报告。",
            }

    @staticmethod
    async def _get_funasr_model():
        global _funasr_model
        if _funasr_model is not None:
            return _funasr_model

        def load_model():
            from funasr import AutoModel

            return AutoModel(
                model=FUNASR_MODEL,
                vad_model=FUNASR_VAD_MODEL,
                vad_kwargs={"max_single_segment_time": 60000},
                punc_model=FUNASR_PUNC_MODEL,
                device=FUNASR_DEVICE,
                hub=FUNASR_HUB,
            )

        import asyncio

        _funasr_model = await asyncio.to_thread(load_model)
        return _funasr_model

    @staticmethod
    async def _run_funasr_generate(model, audio_path: Path):
        import asyncio

        return await asyncio.to_thread(
            model.generate,
            input=str(audio_path),
            batch_size_s=300,
            batch_size_threshold_s=60,
        )

    @staticmethod
    def _extract_funasr_text(result: Any) -> str:
        if isinstance(result, list):
            parts = []
            for item in result:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or "").strip())
            return "".join(part for part in parts if part)
        if isinstance(result, dict):
            return str(result.get("text") or "").strip()
        return ""

    @staticmethod
    def _compact_raw_result(result: Any) -> Any:
        if isinstance(result, list):
            return [
                {key: value for key, value in item.items() if key in {"key", "text", "timestamp"}}
                if isinstance(item, dict)
                else item
                for item in result[:5]
            ]
        if isinstance(result, dict):
            return {key: value for key, value in result.items() if key in {"key", "text", "timestamp"}}
        return None

    @staticmethod
    async def _transcribe_with_openai(audio_path: Path) -> dict:
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
