"""自习室 YOLO 检测器。

这个模块只负责把一张图片转换成业务信号，不直接决定最终自习状态。
"""

import io
import os
import threading
from typing import Any


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


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


YOLO_ENABLED = _bool_env("STUDY_ROOM_YOLO_ENABLED", True)
YOLO_MODEL_NAME = os.getenv("STUDY_ROOM_YOLO_MODEL", "yolo26n.pt")
YOLO_DEVICE = os.getenv("STUDY_ROOM_YOLO_DEVICE", "").strip() or None
YOLO_IMG_SIZE = _int_env("STUDY_ROOM_YOLO_IMG_SIZE", 640)
YOLO_CONF = _float_env("STUDY_ROOM_YOLO_CONF", 0.35)
PERSON_CONF = _float_env("STUDY_ROOM_PERSON_CONF", 0.45)
PHONE_CONF = _float_env("STUDY_ROOM_PHONE_CONF", 0.35)

PERSON_LABELS = {"person"}
PHONE_LABELS = {"cell phone", "phone", "mobile phone", "cellphone"}

_MODEL = None
_MODEL_LOAD_ERROR: str | None = None
_MODEL_LOCK = threading.Lock()


class StudyRoomYoloDetector:
    """Lazy-loaded YOLO detector for study-room frames."""

    @staticmethod
    def is_available() -> bool:
        if not YOLO_ENABLED:
            return False
        model = StudyRoomYoloDetector._model()
        return model is not None

    @staticmethod
    def detect(image_bytes: bytes) -> dict[str, Any] | None:
        """Run YOLO on image bytes and return normalized signals.

        Returns None when YOLO is disabled, missing, or failed to load. The caller
        can then choose a fallback strategy.
        """
        if not image_bytes or not YOLO_ENABLED:
            return None

        model = StudyRoomYoloDetector._model()
        if model is None:
            return None

        try:
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            predict_kwargs: dict[str, Any] = {
                "source": image,
                "imgsz": YOLO_IMG_SIZE,
                "conf": YOLO_CONF,
                "verbose": False,
            }
            if YOLO_DEVICE:
                predict_kwargs["device"] = YOLO_DEVICE
            results = model.predict(**predict_kwargs)
        except Exception as exc:
            return {
                "person_count": 0,
                "phone_detected": False,
                "away": False,
                "multiple_people": False,
                "confidence": 0,
                "source": "yolo_error",
                "raw": {"error": str(exc)},
            }

        if not results:
            return StudyRoomYoloDetector._empty_result()

        result = results[0]
        names = getattr(model, "names", {}) or getattr(result, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        detections: list[dict[str, Any]] = []
        person_count = 0
        phone_detected = False
        max_confidence = 0.0

        if boxes is not None:
            for box in boxes:
                try:
                    cls_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                except Exception:
                    continue
                label = str(names.get(cls_id, cls_id)).lower()
                xyxy = []
                try:
                    xyxy = [round(float(value), 2) for value in box.xyxy[0].tolist()]
                except Exception:
                    xyxy = []

                max_confidence = max(max_confidence, confidence)
                detections.append({
                    "label": label,
                    "confidence": round(confidence, 4),
                    "box": xyxy,
                })

                if label in PERSON_LABELS and confidence >= PERSON_CONF:
                    person_count += 1
                elif label in PHONE_LABELS and confidence >= PHONE_CONF:
                    phone_detected = True

        return {
            "person_count": person_count,
            "phone_detected": phone_detected,
            "away": person_count <= 0,
            "multiple_people": person_count > 1,
            "confidence": round(max_confidence, 4),
            "source": "yolo",
            "raw": {
                "model": YOLO_MODEL_NAME,
                "detections": detections,
                "model_load_error": _MODEL_LOAD_ERROR,
            },
        }

    @staticmethod
    def _model():
        global _MODEL, _MODEL_LOAD_ERROR
        if _MODEL is not None:
            return _MODEL
        if _MODEL_LOAD_ERROR is not None:
            return None

        with _MODEL_LOCK:
            if _MODEL is not None:
                return _MODEL
            if _MODEL_LOAD_ERROR is not None:
                return None
            try:
                from ultralytics import YOLO

                _MODEL = YOLO(YOLO_MODEL_NAME)
                return _MODEL
            except Exception as exc:
                _MODEL_LOAD_ERROR = str(exc)
                return None

    @staticmethod
    def _empty_result() -> dict[str, Any]:
        return {
            "person_count": 0,
            "phone_detected": False,
            "away": True,
            "multiple_people": False,
            "confidence": 0,
            "source": "yolo",
            "raw": {
                "model": YOLO_MODEL_NAME,
                "detections": [],
                "model_load_error": _MODEL_LOAD_ERROR,
            },
        }
