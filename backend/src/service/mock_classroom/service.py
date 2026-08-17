"""Mock classroom service for sessions and uploaded media."""

import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from backend.src.models.mock_classroom_model import (
    MockClassroomFrameLog,
    MockClassroomReport,
    MockClassroomSession,
)
from backend.src.service.mock_classroom.asr import MockClassroomASR
from backend.src.service.mock_classroom.scoring import MockClassroomScoring
from backend.src.service.mock_classroom.vision_analyzer import MockClassroomVisionAnalyzer
from backend.src.utils.constants import STATIC_DIR

MOCK_CLASSROOM_DIR = STATIC_DIR / "mock-classroom"
FRAME_UPLOAD_INTERVAL_SECONDS = 2

logger = logging.getLogger(__name__)


class MockClassroomNotFound(ValueError):
    """Mock classroom session is missing or inaccessible."""


class MockClassroomService:
    @staticmethod
    async def start_session(
        user_id: int,
        topic: str,
        planned_minutes: int,
    ) -> dict:
        normalized_topic = (topic or "").strip()[:128] or "完成一次模拟讲课"
        normalized_minutes = max(3, min(30, int(planned_minutes or 5)))
        session_key = await MockClassroomService._new_session_key()
        now = datetime.now()

        session = await MockClassroomSession.create(
            user_id=user_id,
            session_key=session_key,
            topic=normalized_topic,
            reference_text=None,
            planned_minutes=normalized_minutes,
            state="running",
            report_status="pending",
            started_at=now,
        )

        MockClassroomService._frames_dir(session.session_key).mkdir(parents=True, exist_ok=True)

        return {
            "session_id": session.session_key,
            "state": session.state,
            "started_at": MockClassroomService._dt(session.started_at),
            "frame_upload_interval_seconds": FRAME_UPLOAD_INTERVAL_SECONDS,
        }

    @staticmethod
    async def process_frame(
        user_id: int,
        session_key: str,
        frame: UploadFile,
        client_elapsed_seconds: int = 0,
    ) -> dict:
        session = await MockClassroomService._get_session(user_id, session_key)
        if session.state != "running":
            raise ValueError("模拟课堂会话不是进行中状态")

        frame_bytes = await frame.read()
        if not frame_bytes:
            raise ValueError("上传图片为空")

        client_elapsed = max(0, int(client_elapsed_seconds or 0))
        frame_path = await MockClassroomService._save_frame_bytes(session, frame, frame_bytes)
        signals = await MockClassroomVisionAnalyzer.analyze_frame(frame_bytes)

        await MockClassroomFrameLog.create(
            session_id=session.id,
            client_elapsed_seconds=client_elapsed,
            camera_state=signals["camera_state"],
            person_count=signals["person_count"],
            face_visible=signals["face_visible"],
            away=signals["away"],
            multiple_people=signals["multiple_people"],
            frame_path=frame_path,
            raw_result=MockClassroomVisionAnalyzer.raw_result_payload(signals),
        )

        session.frame_count += 1
        session.elapsed_seconds = max(session.elapsed_seconds, client_elapsed)
        await session.save(update_fields=["frame_count", "elapsed_seconds", "updated_at"])

        return {
            "session_id": session.session_key,
            "camera_state": signals["camera_state"],
            "signals": {
                "person_count": signals["person_count"],
                "face_visible": signals["face_visible"],
                "away": signals["away"],
                "multiple_people": signals["multiple_people"],
            },
            "metrics": MockClassroomService._metrics(session),
        }

    @staticmethod
    async def upload_audio(
        user_id: int,
        session_key: str,
        audio: UploadFile,
        client_elapsed_seconds: int = 0,
    ) -> dict:
        session = await MockClassroomService._get_session(user_id, session_key)
        if session.state not in {"running", "finished"}:
            raise ValueError("模拟课堂会话状态不可上传音频")

        audio_bytes = await audio.read()
        if not audio_bytes:
            raise ValueError("上传音频为空")

        client_elapsed = max(0, int(client_elapsed_seconds or 0))
        audio_url = await MockClassroomService._save_audio_bytes(session, audio, audio_bytes)

        session.audio_url = audio_url
        session.audio_duration_seconds = max(session.audio_duration_seconds, client_elapsed)
        session.elapsed_seconds = max(session.elapsed_seconds, client_elapsed)
        if session.state == "finished" and session.report_status == "pending":
            session.report_status = "generating"
        await session.save(update_fields=[
            "audio_url",
            "audio_duration_seconds",
            "elapsed_seconds",
            "report_status",
            "updated_at",
        ])

        return {
            "session_id": session.session_key,
            "audio_url": session.audio_url,
            "duration_seconds": session.audio_duration_seconds,
            "status": "stored",
        }

    @staticmethod
    async def finish_session(
        user_id: int,
        session_key: str,
        client_elapsed_seconds: int | None = None,
        client_transcript: str | None = None,
    ) -> dict:
        session = await MockClassroomService._get_session(user_id, session_key)
        if session.state == "finished":
            return MockClassroomService._finish_payload(session)

        client_elapsed = max(0, int(client_elapsed_seconds or 0))
        normalized_transcript = (client_transcript or "").strip()[:20000] or None
        session.state = "finished"
        session.ended_at = datetime.now()
        session.elapsed_seconds = max(session.elapsed_seconds, client_elapsed)
        if normalized_transcript:
            session.transcript = normalized_transcript
        session.report_status = "generating"
        await session.save(update_fields=["state", "ended_at", "elapsed_seconds", "transcript", "report_status", "updated_at"])

        return MockClassroomService._finish_payload(session)

    @staticmethod
    async def get_report(user_id: int, session_key: str) -> dict:
        session = await MockClassroomService._get_session(user_id, session_key)
        report = await MockClassroomReport.filter(session_id=session.id).order_by("-id").first()
        if report:
            return MockClassroomService._report_payload(session, report)

        return {
            "session_id": session.session_key,
            "status": session.report_status,
            "overall_score": session.overall_score,
            "knowledge_score": session.knowledge_score,
            "fluency_score": session.fluency_score,
            "presentation_score": session.presentation_score,
            "transcript": session.transcript,
            "strengths": [],
            "gaps": [],
            "suggestions": ["课堂数据已保存，报告正在生成或等待音频转写配置。"],
            "metrics": MockClassroomService._metrics(session),
        }

    @staticmethod
    async def generate_report_for_session(user_id: int, session_key: str) -> None:
        try:
            session = await MockClassroomService._get_session(user_id, session_key)
        except MockClassroomNotFound:
            logger.warning("[MockClassroom] report skipped, session not found: %s", session_key)
            return

        existing_report = await MockClassroomReport.filter(session_id=session.id).order_by("-id").first()
        if existing_report and session.report_status == "ready":
            return

        try:
            session.report_status = "generating"
            await session.save(update_fields=["report_status", "updated_at"])

            transcript = (session.transcript or "").strip()
            if transcript:
                asr_result = {
                    "status": "client_transcript",
                    "text": transcript,
                    "message": "已使用课堂实时讲稿生成报告。",
                }
            else:
                audio_path = MockClassroomService._audio_path(session)
                asr_result = await MockClassroomASR.transcribe(audio_path)
                transcript = (asr_result.get("text") or "").strip()
            vision_summary = await MockClassroomVisionAnalyzer.summarize_session(session.id)
            reference_text = await MockClassroomService._resolve_reference_text(session, user_id)
            if reference_text != (session.reference_text or None):
                session.reference_text = reference_text
                await session.save(update_fields=["reference_text", "updated_at"])
            score_result = await MockClassroomScoring.score(
                session=session,
                transcript=transcript,
                vision_summary=vision_summary,
                asr_result=asr_result,
                user_id=user_id,
            )

            session.transcript = transcript or None
            session.overall_score = int(score_result["overall_score"])
            session.knowledge_score = int(score_result["knowledge_score"])
            session.fluency_score = int(score_result["fluency_score"])
            session.presentation_score = int(score_result["presentation_score"])
            session.report_status = "ready"
            await session.save(update_fields=[
                "transcript",
                "overall_score",
                "knowledge_score",
                "fluency_score",
                "presentation_score",
                "report_status",
                "updated_at",
            ])

            await MockClassroomService._save_report(session, score_result, asr_result, vision_summary, existing_report)
        except Exception:
            logger.warning("[MockClassroom] report generation failed session=%s", session_key, exc_info=True)
            session.report_status = "failed"
            await session.save(update_fields=["report_status", "updated_at"])

    @staticmethod
    async def _resolve_reference_text(session: MockClassroomSession, user_id: int) -> str | None:
        query = (session.topic or "").strip()
        if not query:
            return None

        try:
            from backend.src.utils.knowledge_base import search as kb_search

            result = (await kb_search(query, top_k=5, user_id=user_id)) or ""
        except Exception:
            logger.warning("[MockClassroom] knowledge reference search failed topic=%s", query, exc_info=True)
            return None

        normalized = result.strip()
        if not normalized:
            return None

        empty_markers = ("知识库中暂无相关内容", "知识库检索失败")
        if any(marker in normalized for marker in empty_markers):
            return None

        return normalized[:8000]

    @staticmethod
    async def delete_media(user_id: int, session_key: str) -> None:
        session = await MockClassroomService._get_session(user_id, session_key)
        session_dir = MockClassroomService._session_dir(session.session_key).resolve()
        base_dir = MOCK_CLASSROOM_DIR.resolve()
        try:
            session_dir.relative_to(base_dir)
        except ValueError as exc:
            raise ValueError("模拟课堂文件路径异常") from exc

        shutil.rmtree(session_dir, ignore_errors=True)
        session.audio_url = None
        session.frame_count = 0
        await session.save(update_fields=["audio_url", "frame_count", "updated_at"])

    @staticmethod
    async def _get_session(user_id: int, session_key: str) -> MockClassroomSession:
        session = await MockClassroomSession.filter(session_key=session_key, user_id=user_id).first()
        if not session:
            raise MockClassroomNotFound("模拟课堂会话不存在")
        return session

    @staticmethod
    async def _new_session_key() -> str:
        while True:
            key = f"mc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            exists = await MockClassroomSession.filter(session_key=key).exists()
            if not exists:
                return key

    @staticmethod
    def _placeholder_camera_signals() -> dict[str, Any]:
        return {
            "camera_state": "stable",
            "person_count": 1,
            "face_visible": True,
            "away": False,
            "multiple_people": False,
        }

    @staticmethod
    async def _save_frame_bytes(session: MockClassroomSession, frame: UploadFile, frame_bytes: bytes) -> str:
        frames_dir = MockClassroomService._frames_dir(session.session_key)
        frames_dir.mkdir(parents=True, exist_ok=True)
        next_index = session.frame_count + 1
        suffix = MockClassroomService._safe_image_suffix(frame.filename)
        filename = f"frame_{next_index:06d}{suffix}"
        file_path = frames_dir / filename
        file_path.write_bytes(frame_bytes)
        return f"/static/mock-classroom/{session.session_key}/frames/{filename}"

    @staticmethod
    async def _save_audio_bytes(session: MockClassroomSession, audio: UploadFile, audio_bytes: bytes) -> str:
        session_dir = MockClassroomService._session_dir(session.session_key)
        session_dir.mkdir(parents=True, exist_ok=True)
        suffix = MockClassroomService._safe_audio_suffix(audio.filename)
        filename = f"audio{suffix}"
        file_path = session_dir / filename
        file_path.write_bytes(audio_bytes)
        return f"/static/mock-classroom/{session.session_key}/{filename}"

    @staticmethod
    async def _save_report(
        session: MockClassroomSession,
        score_result: dict,
        asr_result: dict,
        vision_summary: dict,
        report: MockClassroomReport | None = None,
    ) -> MockClassroomReport:
        rubric = score_result.get("rubric") if isinstance(score_result.get("rubric"), dict) else {}
        rubric.update({
            "asr": {
                "status": asr_result.get("status"),
                "message": asr_result.get("message"),
            },
            "vision_summary": vision_summary,
            "generated_at": datetime.now().isoformat(),
        })
        payload = {
            "overall_score": int(score_result["overall_score"]),
            "knowledge_score": int(score_result["knowledge_score"]),
            "fluency_score": int(score_result["fluency_score"]),
            "presentation_score": int(score_result["presentation_score"]),
            "strengths": json.dumps(score_result.get("strengths", []), ensure_ascii=False),
            "gaps": json.dumps(score_result.get("gaps", []), ensure_ascii=False),
            "suggestions": json.dumps(score_result.get("suggestions", []), ensure_ascii=False),
            "rubric_json": json.dumps(rubric, ensure_ascii=False),
        }

        if report:
            for key, value in payload.items():
                setattr(report, key, value)
            await report.save()
            return report

        return await MockClassroomReport.create(session_id=session.id, **payload)

    @staticmethod
    def _audio_path(session: MockClassroomSession) -> Path | None:
        if not session.audio_url:
            return None

        filename = Path(str(session.audio_url).split("?", 1)[0]).name
        if not filename:
            return None

        candidate = (MockClassroomService._session_dir(session.session_key) / filename).resolve()
        base_dir = MockClassroomService._session_dir(session.session_key).resolve()
        try:
            candidate.relative_to(base_dir)
        except ValueError:
            return None
        return candidate if candidate.exists() else None

    @staticmethod
    def _safe_image_suffix(filename: str | None) -> str:
        suffix = Path(filename or "").suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return ".jpg" if suffix == ".jpeg" else suffix
        return ".jpg"

    @staticmethod
    def _safe_audio_suffix(filename: str | None) -> str:
        suffix = Path(filename or "").suffix.lower()
        if suffix in {".webm", ".mp3", ".wav", ".m4a", ".mp4", ".ogg"}:
            return suffix
        return ".webm"

    @staticmethod
    def _session_dir(session_key: str) -> Path:
        return MOCK_CLASSROOM_DIR / session_key

    @staticmethod
    def _frames_dir(session_key: str) -> Path:
        return MockClassroomService._session_dir(session_key) / "frames"

    @staticmethod
    def _metrics(session: MockClassroomSession) -> dict:
        return {
            "elapsed_seconds": session.elapsed_seconds,
            "planned_minutes": session.planned_minutes,
            "frame_count": session.frame_count,
            "audio_duration_seconds": session.audio_duration_seconds,
        }

    @staticmethod
    def _finish_payload(session: MockClassroomSession) -> dict:
        return {
            "session_id": session.session_key,
            "state": session.state,
            "report_status": session.report_status,
            "summary": {
                "topic": session.topic,
                "elapsed_seconds": session.elapsed_seconds,
                "planned_minutes": session.planned_minutes,
                "frame_count": session.frame_count,
                "audio_url": session.audio_url,
            },
        }

    @staticmethod
    def _report_payload(session: MockClassroomSession, report: MockClassroomReport) -> dict:
        return {
            "session_id": session.session_key,
            "status": session.report_status,
            "overall_score": report.overall_score,
            "knowledge_score": report.knowledge_score,
            "fluency_score": report.fluency_score,
            "presentation_score": report.presentation_score,
            "transcript": session.transcript,
            "strengths": MockClassroomService._json_list(report.strengths),
            "gaps": MockClassroomService._json_list(report.gaps),
            "suggestions": MockClassroomService._json_list(report.suggestions),
            "rubric": MockClassroomService._json_dict(report.rubric_json),
            "metrics": MockClassroomService._metrics(session),
        }

    @staticmethod
    def _json_list(value: str | None) -> list:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    @staticmethod
    def _json_dict(value: str | None) -> dict:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _dt(value) -> str | None:
        return value.isoformat() if value else None
