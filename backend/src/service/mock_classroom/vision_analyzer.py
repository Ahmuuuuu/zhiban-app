"""Camera-frame analysis helpers for mock classroom."""

import asyncio
import json
from typing import Any

from backend.src.models.mock_classroom_model import MockClassroomFrameLog
from backend.src.service.study_room.yolo_detector import StudyRoomYoloDetector


class MockClassroomVisionAnalyzer:
    @staticmethod
    async def analyze_frame(frame_bytes: bytes) -> dict[str, Any]:
        signals = await asyncio.to_thread(StudyRoomYoloDetector.detect, frame_bytes)
        if signals is None:
            return {
                "camera_state": "stable",
                "person_count": 1,
                "face_visible": True,
                "away": False,
                "multiple_people": False,
                "confidence": 0,
                "source": "placeholder",
                "raw": {"reason": "yolo_unavailable"},
            }

        person_count = int(signals.get("person_count") or 0)
        away = bool(signals.get("away", False)) or person_count <= 0
        multiple_people = bool(signals.get("multiple_people", False)) or person_count > 1
        if away:
            camera_state = "away"
        elif multiple_people:
            camera_state = "multiple_people"
        elif person_count == 1:
            camera_state = "stable"
        else:
            camera_state = "unknown"

        return {
            "camera_state": camera_state,
            "person_count": person_count,
            "face_visible": person_count > 0,
            "away": away,
            "multiple_people": multiple_people,
            "confidence": float(signals.get("confidence") or 0),
            "source": signals.get("source", "unknown"),
            "raw": signals.get("raw", {}),
        }

    @staticmethod
    async def summarize_session(session_id: int) -> dict[str, Any]:
        logs = await MockClassroomFrameLog.filter(session_id=session_id).order_by("id")
        total = len(logs)
        if total <= 0:
            return {
                "frame_count": 0,
                "stable_rate": 0,
                "face_visible_rate": 0,
                "away_rate": 0,
                "multiple_people_rate": 0,
                "presentation_score": 60,
                "summary": "没有足够的课堂画面用于表达状态评分。",
            }

        stable_count = sum(1 for log in logs if log.camera_state == "stable")
        face_count = sum(1 for log in logs if log.face_visible)
        away_count = sum(1 for log in logs if log.away)
        multiple_count = sum(1 for log in logs if log.multiple_people)
        stable_rate = stable_count / total
        face_rate = face_count / total
        away_rate = away_count / total
        multiple_rate = multiple_count / total
        presentation_score = round(
            55
            + stable_rate * 30
            + face_rate * 10
            - away_rate * 30
            - multiple_rate * 12
        )
        presentation_score = max(0, min(100, presentation_score))

        if away_rate >= 0.25:
            summary = "讲解过程中多次离开画面，表达状态分会受到影响。"
        elif multiple_rate >= 0.15:
            summary = "讲解过程中出现多次多人入镜，课堂画面稳定性略受影响。"
        elif stable_rate >= 0.8:
            summary = "镜头中人像较稳定，讲解过程中没有明显长时间离开画面。"
        else:
            summary = "课堂画面基本可用，但稳定性还有提升空间。"

        return {
            "frame_count": total,
            "stable_rate": round(stable_rate, 4),
            "face_visible_rate": round(face_rate, 4),
            "away_rate": round(away_rate, 4),
            "multiple_people_rate": round(multiple_rate, 4),
            "presentation_score": presentation_score,
            "summary": summary,
            "sample_states": MockClassroomVisionAnalyzer._sample_states(logs),
        }

    @staticmethod
    def raw_result_payload(signals: dict[str, Any]) -> str:
        return json.dumps(
            {
                "source": signals.get("source", "unknown"),
                "signals": signals,
                "raw": signals.get("raw", {}),
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _sample_states(logs: list[MockClassroomFrameLog]) -> list[dict]:
        sample = logs[:3] + logs[-3:] if len(logs) > 6 else logs
        return [
            {
                "elapsed_seconds": log.client_elapsed_seconds,
                "camera_state": log.camera_state,
                "person_count": log.person_count,
                "face_visible": log.face_visible,
            }
            for log in sample
        ]
