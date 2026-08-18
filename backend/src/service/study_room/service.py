"""自习室服务 — 会话管理和 YOLO 检测调度。"""

import asyncio
import json
import logging
import math
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from backend.src.models.study_room_model import StudyRoomAlert, StudyRoomFrameLog, StudyRoomSession
from backend.src.service.study_room.yolo_detector import StudyRoomYoloDetector
from backend.src.utils.constants import STATIC_DIR

STUDY_ROOM_DIR = STATIC_DIR / "study-room"
FRAME_UPLOAD_INTERVAL_SECONDS = 2
ALERT_COOLDOWN_SECONDS = 30
TIMELAPSE_FPS = 24
TIMELAPSE_MAX_SECONDS = 60
TIMELAPSE_TIMEOUT_SECONDS = 180
WINDOW_LOOKBACK_LOGS = 24
PHONE_WINDOW_FRAMES = 4
PHONE_TRIGGER_FRAMES = 2
AWAY_WINDOW_SECONDS = 6
MULTIPLE_PEOPLE_WINDOW_SECONDS = 6

STATE_MESSAGES = {
    "focused": "状态很好，继续保持。",
    "away": "画面中暂时没有检测到你。",
    "phone_detected": "检测到手机使用，先放一放？",
    "multiple_people": "检测到多人入镜，请确认自习环境。",
    "unknown": "正在分析当前学习状态。",
}

ALERT_LEVELS = {
    "away": "warning",
    "phone_detected": "warning",
    "multiple_people": "info",
}

logger = logging.getLogger(__name__)


class StudyRoomNotFound(ValueError):
    """自习室会话不存在或无权访问。"""


class StudyRoomService:
    @staticmethod
    async def start_session(
        user_id: int,
        goal: str,
        planned_minutes: int,
        vlog_enabled: bool = False,
        timelapse_interval_seconds: int = 5,
        timelapse_target_seconds: int | None = None,
    ) -> dict:
        """创建一次自习室会话。"""
        normalized_goal = (goal or "").strip()[:80] or "完成一次专注自习"
        normalized_minutes = max(10, min(240, int(planned_minutes or 45)))
        normalized_interval = StudyRoomService._normalize_interval(timelapse_interval_seconds)
        normalized_target = StudyRoomService._normalize_timelapse_target(timelapse_target_seconds)
        session_key = await StudyRoomService._new_session_key()
        now = datetime.now()

        session = await StudyRoomSession.create(
            user_id=user_id,
            session_key=session_key,
            goal=normalized_goal,
            planned_minutes=normalized_minutes,
            state="running",
            vlog_enabled=bool(vlog_enabled),
            timelapse_interval=normalized_interval,
            timelapse_target=normalized_target,
            timelapse_status="capturing" if vlog_enabled else "disabled",
            started_at=now,
        )

        StudyRoomService._session_dir(session.session_key).mkdir(parents=True, exist_ok=True)
        if session.vlog_enabled:
            StudyRoomService._frames_dir(session.session_key).mkdir(parents=True, exist_ok=True)

        return {
            "session_id": session.session_key,
            "state": session.state,
            "started_at": StudyRoomService._dt(session.started_at),
            "frame_upload_interval_seconds": FRAME_UPLOAD_INTERVAL_SECONDS,
            "vlog_enabled": session.vlog_enabled,
        }

    @staticmethod
    async def process_frame(
        user_id: int,
        session_key: str,
        frame: UploadFile,
        client_elapsed_seconds: int = 0,
        save_for_vlog: bool = False,
    ) -> dict:
        """处理一帧图片，优先使用 YOLO，依赖缺失时退回 mock。"""
        session = await StudyRoomService._get_session(user_id, session_key)
        if session.state != "running":
            raise ValueError("自习会话不是进行中状态")

        client_elapsed = max(0, int(client_elapsed_seconds or 0))
        log_index = await StudyRoomFrameLog.filter(session_id=session.id).count() + 1
        frame_bytes = await frame.read()
        if not frame_bytes:
            raise ValueError("上传图片为空")

        signals = await StudyRoomService._detect_frame(frame_bytes, log_index)
        frame_path = None

        should_save_frame = bool(session.vlog_enabled and save_for_vlog)
        if should_save_frame:
            frame_path = await StudyRoomService._save_frame_bytes(session, frame, frame_bytes)

        previous_log = await StudyRoomFrameLog.filter(session_id=session.id).order_by("-id").first()
        recent_logs = await StudyRoomService._recent_frame_logs(session.id)
        state = StudyRoomService._state_from_window(signals, recent_logs, client_elapsed)
        raw_result = {
            "source": signals.get("source", "unknown"),
            "frame_index": log_index,
            "stable_state": state,
            "signals": signals,
            "raw": signals.get("raw", {}),
        }
        log = await StudyRoomFrameLog.create(
            session_id=session.id,
            client_elapsed_seconds=client_elapsed,
            state=state,
            confidence=float(signals.get("confidence", 0)),
            person_count=int(signals.get("person_count", 0)),
            phone_detected=bool(signals.get("phone_detected", False)),
            away=bool(signals.get("away", False)),
            multiple_people=bool(signals.get("multiple_people", False)),
            saved_for_vlog=should_save_frame,
            frame_path=frame_path,
            raw_result=json.dumps(raw_result, ensure_ascii=False),
        )

        await StudyRoomService._apply_frame_metrics(session, state, client_elapsed, previous_log, should_save_frame)
        reminder = await StudyRoomService._maybe_create_alert(session, state, client_elapsed, previous_log)

        return {
            "session_id": session.session_key,
            "state": state,
            "message": STATE_MESSAGES.get(state, STATE_MESSAGES["unknown"]),
            "confidence": log.confidence,
            "reminder": reminder,
            "signals": {
                "person_count": log.person_count,
                "phone_detected": log.phone_detected,
                "away": log.away,
                "multiple_people": log.multiple_people,
            },
            "metrics": StudyRoomService._metrics(session),
        }

    @staticmethod
    async def get_session(user_id: int, session_key: str) -> dict:
        """查询自习室会话详情。"""
        session = await StudyRoomService._get_session(user_id, session_key)
        alerts = await StudyRoomAlert.filter(session_id=session.id).order_by("-triggered_at").limit(8)

        return {
            "session_id": session.session_key,
            "state": session.state,
            "goal": session.goal,
            "planned_minutes": session.planned_minutes,
            "started_at": StudyRoomService._dt(session.started_at),
            "ended_at": StudyRoomService._dt(session.ended_at),
            "vlog_enabled": session.vlog_enabled,
            "timelapse": StudyRoomService._timelapse_payload(session),
            "metrics": StudyRoomService._metrics(session),
            "recent_alerts": [StudyRoomService._alert_payload(alert) for alert in alerts],
        }

    @staticmethod
    async def finish_session(user_id: int, session_key: str, client_elapsed_seconds: int | None = None) -> dict:
        """结束自习室会话并返回总结。"""
        session = await StudyRoomService._get_session(user_id, session_key)
        if session.state == "finished":
            return StudyRoomService._finish_payload(session)

        client_elapsed = max(0, int(client_elapsed_seconds or 0))
        if client_elapsed > session.elapsed_seconds:
            last_log = await StudyRoomFrameLog.filter(session_id=session.id).order_by("-id").first()
            last_state = last_log.state if last_log else "focused"
            StudyRoomService._apply_elapsed_delta(session, last_state, client_elapsed)

        session.state = "finished"
        session.ended_at = datetime.now()
        if session.vlog_enabled:
            session.timelapse_status = "generating" if session.frame_count > 0 else "failed"
        else:
            session.timelapse_status = "disabled"
        StudyRoomService._refresh_focus_rate(session)
        await session.save()

        return StudyRoomService._finish_payload(session)

    @staticmethod
    async def get_timelapse(user_id: int, session_key: str) -> dict:
        """查询延时摄影状态。"""
        session = await StudyRoomService._get_session(user_id, session_key)
        await StudyRoomService._refresh_timelapse_ready_file(session)
        return StudyRoomService._timelapse_payload(session)

    @staticmethod
    async def delete_timelapse(user_id: int, session_key: str) -> None:
        """删除延时摄影相关文件。"""
        session = await StudyRoomService._get_session(user_id, session_key)
        session_dir = StudyRoomService._session_dir(session.session_key).resolve()
        base_dir = STUDY_ROOM_DIR.resolve()
        try:
            session_dir.relative_to(base_dir)
        except ValueError:
            raise ValueError("自习室文件路径异常")

        shutil.rmtree(session_dir, ignore_errors=True)
        session.frame_count = 0
        session.timelapse_url = None
        session.timelapse_status = "disabled"
        await session.save(update_fields=["frame_count", "timelapse_url", "timelapse_status", "updated_at"])

    @staticmethod
    async def generate_timelapse_for_session(user_id: int, session_key: str) -> None:
        """后台生成学习 Vlog 延时摄影。"""
        try:
            session = await StudyRoomService._get_session(user_id, session_key)
        except StudyRoomNotFound:
            logger.warning("[StudyRoom] timelapse skipped, session not found: %s", session_key)
            return

        if not session.vlog_enabled:
            await StudyRoomService._mark_timelapse(session, "disabled", None)
            return

        frames = StudyRoomService._vlog_frame_paths(session.session_key)
        if not frames:
            session.frame_count = 0
            await StudyRoomService._mark_timelapse(session, "failed", None, update_frame_count=True)
            return

        session.frame_count = len(frames)
        await StudyRoomService._mark_timelapse(session, "generating", None, update_frame_count=True)

        ffmpeg_bin = StudyRoomService._ffmpeg_bin()
        if not ffmpeg_bin:
            logger.warning("[StudyRoom] ffmpeg not found, timelapse failed session=%s", session.session_key)
            await StudyRoomService._mark_timelapse(session, "failed", None)
            return

        session_dir = StudyRoomService._session_dir(session.session_key)
        manifest_path = session_dir / "timelapse_frames.txt"
        output_path = session_dir / "timelapse.mp4"
        tmp_output_path = session_dir / "timelapse.tmp.mp4"

        try:
            StudyRoomService._write_timelapse_manifest(session, frames, manifest_path)
            if tmp_output_path.exists():
                tmp_output_path.unlink()
            command = StudyRoomService._ffmpeg_command(ffmpeg_bin, manifest_path, tmp_output_path)
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMELAPSE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                raise RuntimeError("ffmpeg timed out")

            if proc.returncode != 0:
                error_text = (stderr or stdout or b"").decode("utf-8", errors="ignore")[-1200:]
                raise RuntimeError(error_text or f"ffmpeg exited with code {proc.returncode}")

            if output_path.exists():
                output_path.unlink()
            tmp_output_path.replace(output_path)
            await StudyRoomService._mark_timelapse(
                session,
                "ready",
                f"/static/study-room/{session.session_key}/timelapse.mp4",
            )
        except Exception:
            logger.warning("[StudyRoom] timelapse generation failed session=%s", session.session_key, exc_info=True)
            if tmp_output_path.exists():
                try:
                    tmp_output_path.unlink()
                except OSError:
                    logger.debug("[StudyRoom] cleanup tmp timelapse failed", exc_info=True)
            await StudyRoomService._mark_timelapse(session, "failed", None)

    @staticmethod
    async def _get_session(user_id: int, session_key: str) -> StudyRoomSession:
        session = await StudyRoomSession.filter(session_key=session_key, user_id=user_id).first()
        if not session:
            raise StudyRoomNotFound("自习室会话不存在")
        return session

    @staticmethod
    async def _new_session_key() -> str:
        while True:
            key = f"sr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            exists = await StudyRoomSession.filter(session_key=key).exists()
            if not exists:
                return key

    @staticmethod
    def _mock_detect(frame_index: int) -> dict[str, Any]:
        # mock 仅用于 YOLO 不可用时的流程兜底。用周期短爆发代替单帧命中，
        # 保证窗口判定（手机 4 帧内 2 帧、离席/多人持续约 6 秒）能真正触发告警态。
        cycle = frame_index % 40
        if 6 <= cycle <= 9:
            return {
                "person_count": 1,
                "phone_detected": True,
                "away": False,
                "multiple_people": False,
                "confidence": 0.8,
            }
        if 20 <= cycle <= 23:
            return {
                "person_count": 0,
                "phone_detected": False,
                "away": True,
                "multiple_people": False,
                "confidence": 0.78,
            }
        if 34 <= cycle <= 37:
            return {
                "person_count": 2,
                "phone_detected": False,
                "away": False,
                "multiple_people": True,
                "confidence": 0.82,
            }
        return {
            "person_count": 1,
            "phone_detected": False,
            "away": False,
            "multiple_people": False,
            "confidence": 0.92,
        }

    @staticmethod
    async def _recent_frame_logs(session_id: int) -> list[StudyRoomFrameLog]:
        logs = await StudyRoomFrameLog.filter(session_id=session_id).order_by("-id").limit(WINDOW_LOOKBACK_LOGS)
        return list(reversed(logs))

    @staticmethod
    def _state_from_window(
        signals: dict[str, Any],
        recent_logs: list[StudyRoomFrameLog],
        client_elapsed_seconds: int,
    ) -> str:
        entries = [
            StudyRoomService._entry_from_log(log)
            for log in recent_logs
        ]
        entries.append(StudyRoomService._entry_from_signals(signals, client_elapsed_seconds))

        if StudyRoomService._is_sustained(
            entries,
            client_elapsed_seconds,
            AWAY_WINDOW_SECONDS,
            lambda entry: entry["person_count"] <= 0 or entry["away"],
        ):
            return "away"

        recent_phone_entries = entries[-PHONE_WINDOW_FRAMES:]
        if len(recent_phone_entries) >= PHONE_TRIGGER_FRAMES:
            phone_hits = sum(1 for entry in recent_phone_entries if entry["phone_detected"])
            if phone_hits >= PHONE_TRIGGER_FRAMES:
                return "phone_detected"

        if StudyRoomService._is_sustained(
            entries,
            client_elapsed_seconds,
            MULTIPLE_PEOPLE_WINDOW_SECONDS,
            lambda entry: entry["person_count"] > 1 or entry["multiple_people"],
        ):
            return "multiple_people"

        if any(entry["person_count"] > 0 for entry in entries[-PHONE_WINDOW_FRAMES:]):
            return "focused"

        return "unknown"

    @staticmethod
    def _entry_from_log(log: StudyRoomFrameLog) -> dict[str, Any]:
        return {
            "elapsed": max(0, int(log.client_elapsed_seconds or 0)),
            "person_count": int(log.person_count or 0),
            "phone_detected": bool(log.phone_detected),
            "away": bool(log.away),
            "multiple_people": bool(log.multiple_people),
        }

    @staticmethod
    def _entry_from_signals(signals: dict[str, Any], client_elapsed_seconds: int) -> dict[str, Any]:
        person_count = int(signals.get("person_count") or 0)
        return {
            "elapsed": max(0, int(client_elapsed_seconds or 0)),
            "person_count": person_count,
            "phone_detected": bool(signals.get("phone_detected", False)),
            "away": bool(signals.get("away", False)) or person_count <= 0,
            "multiple_people": bool(signals.get("multiple_people", False)) or person_count > 1,
        }

    @staticmethod
    def _is_sustained(entries: list[dict[str, Any]], current_elapsed: int, window_seconds: int, predicate) -> bool:
        if not entries:
            return False

        frames_needed = max(2, math.floor(window_seconds / FRAME_UPLOAD_INTERVAL_SECONDS) + 1)
        if current_elapsed > 0:
            window_entries = [
                entry
                for entry in entries
                if current_elapsed - entry["elapsed"] <= window_seconds
            ]
        else:
            window_entries = entries[-frames_needed:]

        if len(window_entries) < frames_needed:
            return False

        selected = window_entries[-frames_needed:]
        if current_elapsed > 0 and selected[0]["elapsed"] > current_elapsed - window_seconds:
            return False

        return all(predicate(entry) for entry in selected)

    @staticmethod
    def _state_from_signals(signals: dict[str, Any]) -> str:
        if signals.get("away") or int(signals.get("person_count") or 0) <= 0:
            return "away"
        if signals.get("phone_detected"):
            return "phone_detected"
        if signals.get("multiple_people") or int(signals.get("person_count") or 0) > 1:
            return "multiple_people"
        if int(signals.get("person_count") or 0) == 1:
            return "focused"
        return "unknown"

    @staticmethod
    async def _detect_frame(frame_bytes: bytes, frame_index: int) -> dict[str, Any]:
        signals = await asyncio.to_thread(StudyRoomYoloDetector.detect, frame_bytes)
        if signals is not None and signals.get("source") != "yolo_error":
            return signals

        mock_signals = StudyRoomService._mock_detect(frame_index)
        mock_signals["source"] = "mock"
        mock_signals["raw"] = {
            "reason": "yolo_unavailable",
            "yolo_error": signals.get("raw", {}).get("error") if signals else None,
        }
        return mock_signals

    @staticmethod
    async def _apply_frame_metrics(
        session: StudyRoomSession,
        state: str,
        client_elapsed_seconds: int,
        previous_log: StudyRoomFrameLog | None,
        saved_for_vlog: bool,
    ) -> None:
        if client_elapsed_seconds > session.elapsed_seconds:
            StudyRoomService._apply_elapsed_delta(session, state, client_elapsed_seconds)

        if state == "away" and (not previous_log or previous_log.state != "away"):
            session.away_count += 1
        if saved_for_vlog:
            session.frame_count += 1
        StudyRoomService._refresh_focus_rate(session)
        await session.save()

    @staticmethod
    def _apply_elapsed_delta(session: StudyRoomSession, state: str, target_elapsed_seconds: int) -> None:
        delta = max(0, target_elapsed_seconds - session.elapsed_seconds)
        session.elapsed_seconds = max(session.elapsed_seconds, target_elapsed_seconds)
        if state == "focused":
            session.focus_seconds += delta
        elif state == "away":
            session.away_seconds += delta

    @staticmethod
    async def _maybe_create_alert(
        session: StudyRoomSession,
        state: str,
        client_elapsed_seconds: int,
        previous_log: StudyRoomFrameLog | None,
    ) -> dict | None:
        if state not in ALERT_LEVELS:
            return None
        if previous_log and previous_log.state == state:
            return None

        last_alert = await StudyRoomAlert.filter(session_id=session.id, alert_type=state).order_by("-triggered_at").first()
        if last_alert and client_elapsed_seconds - last_alert.client_elapsed_seconds < ALERT_COOLDOWN_SECONDS:
            return None

        alert = await StudyRoomAlert.create(
            session_id=session.id,
            alert_type=state,
            level=ALERT_LEVELS[state],
            message=STATE_MESSAGES[state],
            client_elapsed_seconds=client_elapsed_seconds,
        )
        session.alert_count += 1
        if state == "phone_detected":
            session.phone_alert_count += 1
        elif state == "multiple_people":
            session.multiple_people_alert_count += 1
        await session.save(update_fields=[
            "alert_count",
            "phone_alert_count",
            "multiple_people_alert_count",
            "updated_at",
        ])

        return StudyRoomService._alert_payload(alert)

    @staticmethod
    async def _save_frame_bytes(session: StudyRoomSession, frame: UploadFile, frame_bytes: bytes) -> str:
        frames_dir = StudyRoomService._frames_dir(session.session_key)
        frames_dir.mkdir(parents=True, exist_ok=True)
        next_index = session.frame_count + 1
        suffix = StudyRoomService._safe_suffix(frame.filename)
        filename = f"frame_{next_index:06d}{suffix}"
        file_path = frames_dir / filename
        file_path.write_bytes(frame_bytes)
        return f"/static/study-room/{session.session_key}/frames/{filename}"

    @staticmethod
    def _safe_suffix(filename: str | None) -> str:
        suffix = Path(filename or "").suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return ".jpg" if suffix == ".jpeg" else suffix
        return ".jpg"

    @staticmethod
    def _vlog_frame_paths(session_key: str) -> list[Path]:
        frames_dir = StudyRoomService._frames_dir(session_key)
        if not frames_dir.exists():
            return []
        allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
        return sorted(
            path
            for path in frames_dir.iterdir()
            if path.is_file() and path.suffix.lower() in allowed_suffixes
        )

    @staticmethod
    def _write_timelapse_manifest(session: StudyRoomSession, frames: list[Path], manifest_path: Path) -> None:
        target_seconds = StudyRoomService._timelapse_target_seconds(session, len(frames))
        frame_duration = max(1 / TIMELAPSE_FPS, target_seconds / max(len(frames), 1))
        lines: list[str] = []
        for frame in frames:
            lines.append(f"file '{StudyRoomService._ffmpeg_escape_path(frame)}'")
            lines.append(f"duration {frame_duration:.6f}")
        if frames:
            lines.append(f"file '{StudyRoomService._ffmpeg_escape_path(frames[-1])}'")
        manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _ffmpeg_escape_path(path: Path) -> str:
        return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")

    @staticmethod
    def _timelapse_target_seconds(session: StudyRoomSession, frame_count: int) -> int:
        if session.timelapse_target:
            return max(10, min(TIMELAPSE_MAX_SECONDS, int(session.timelapse_target)))
        automatic = math.ceil(frame_count / 12)
        return max(10, min(45, automatic))

    @staticmethod
    def _ffmpeg_bin() -> str | None:
        configured = os.getenv("FFMPEG_BIN") or os.getenv("STUDY_ROOM_FFMPEG_BIN")
        if configured:
            return configured
        return shutil.which("ffmpeg")

    @staticmethod
    def _ffmpeg_command(ffmpeg_bin: str, manifest_path: Path, output_path: Path) -> list[str]:
        return [
            ffmpeg_bin,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest_path),
            "-vf",
            f"scale=1280:-2:flags=lanczos,fps={TIMELAPSE_FPS},format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    @staticmethod
    async def _mark_timelapse(
        session: StudyRoomSession,
        status: str,
        url: str | None,
        update_frame_count: bool = False,
    ) -> None:
        session.timelapse_status = status
        session.timelapse_url = url
        update_fields = ["timelapse_status", "timelapse_url", "updated_at"]
        if update_frame_count:
            update_fields.append("frame_count")
        await session.save(update_fields=update_fields)

    @staticmethod
    async def _refresh_timelapse_ready_file(session: StudyRoomSession) -> None:
        if not session.vlog_enabled or session.timelapse_status == "ready":
            return
        output_path = StudyRoomService._session_dir(session.session_key) / "timelapse.mp4"
        if output_path.exists():
            session.timelapse_status = "ready"
            session.timelapse_url = f"/static/study-room/{session.session_key}/timelapse.mp4"
            await session.save(update_fields=["timelapse_status", "timelapse_url", "updated_at"])

    @staticmethod
    def _session_dir(session_key: str) -> Path:
        return STUDY_ROOM_DIR / session_key

    @staticmethod
    def _frames_dir(session_key: str) -> Path:
        return StudyRoomService._session_dir(session_key) / "frames"

    @staticmethod
    def _normalize_interval(value: int | None) -> int:
        number = int(value or 5)
        if number in {3, 5, 8}:
            return number
        return 5

    @staticmethod
    def _normalize_timelapse_target(value: int | None) -> int | None:
        if value is None:
            return None
        number = int(value or 0)
        if number <= 0:
            return None
        return max(10, min(60, number))

    @staticmethod
    def _refresh_focus_rate(session: StudyRoomSession) -> None:
        if session.elapsed_seconds <= 0:
            session.focus_rate = 100
            return
        session.focus_rate = round(session.focus_seconds / max(session.elapsed_seconds, 1) * 100)

    @staticmethod
    def _metrics(session: StudyRoomSession) -> dict:
        return {
            "elapsed_seconds": session.elapsed_seconds,
            "focus_seconds": session.focus_seconds,
            "focus_rate": session.focus_rate,
            "away_count": session.away_count,
            "alert_count": session.alert_count,
        }

    @staticmethod
    def _summary(session: StudyRoomSession) -> dict:
        return {
            "goal": session.goal,
            "elapsed_seconds": session.elapsed_seconds,
            "focus_seconds": session.focus_seconds,
            "focus_rate": session.focus_rate,
            "away_count": session.away_count,
            "alert_count": session.alert_count,
            "phone_alert_count": session.phone_alert_count,
            "multiple_people_alert_count": session.multiple_people_alert_count,
        }

    @staticmethod
    def _timelapse_payload(session: StudyRoomSession) -> dict:
        return {
            "enabled": session.vlog_enabled,
            "status": session.timelapse_status,
            "url": session.timelapse_url,
            "frame_count": session.frame_count,
        }

    @staticmethod
    def _finish_payload(session: StudyRoomSession) -> dict:
        return {
            "session_id": session.session_key,
            "state": session.state,
            "summary": StudyRoomService._summary(session),
            "timelapse": StudyRoomService._timelapse_payload(session),
        }

    @staticmethod
    def _alert_payload(alert: StudyRoomAlert) -> dict:
        return {
            "type": alert.alert_type,
            "message": alert.message,
            "level": alert.level,
            "client_elapsed_seconds": alert.client_elapsed_seconds,
            "triggered_at": StudyRoomService._dt(alert.triggered_at),
        }

    @staticmethod
    def _dt(value) -> str | None:
        return value.isoformat() if value else None
