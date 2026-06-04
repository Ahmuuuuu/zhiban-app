"""语音旁白服务 — 对文字类资源调用 EdgeTTS 逐段生成旁白 (CRUD)"""

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil

from backend.src.utils.tts_utils import parse_by_type, generate_audio_with_timestamps, NARRATABLE_TYPES

logger = logging.getLogger(__name__)

# EdgeTTS 并发限制，避免触发云端限流
_TTS_SEMAPHORE = asyncio.Semaphore(5)


async def narrate_content(content: str, resource_type: str, voice: str, resource_id: int) -> dict:
    """从原始内容字符串直接生成旁白（不查 DB，不写 Narration 表），用于裁剪后的内容

    Returns:
        {"sections": [...]}  与 narrate_resource 返回的 sections 格式一致
    """
    sections = parse_by_type(content, resource_type or "document")
    if not sections:
        return {"sections": []}

    base_dir = Path(__file__).parent.parent.parent / "static" / "audio" / str(resource_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    results = await _generate_sections_audio(sections, voice, base_dir, resource_id)
    return {"sections": results}


async def narrate_resource(resource_id: int, voice: str = "zh-CN-XiaoxiaoNeural", force_regenerate: bool = False):
    """对某个文字类资源逐段生成旁白，已有则直接返回，无则生成写入 DB

    Args:
        resource_id: 资源 ID
        voice: EdgeTTS 语音名称
        force_regenerate: 是否强制重新生成（删除旧音频 + 旧记录）

    Returns:
        {"sections": [...], "narration_id": int, "resource_id": int, "voice": str, "cached": bool}
    """
    from backend.src.models.resource_model import GeneratedResource
    from backend.src.models.narration_model import Narration

    resource = await GeneratedResource.filter(id=resource_id).first()
    if not resource:
        return {"error": "资源不存在"}
    if resource.resource_type not in NARRATABLE_TYPES:
        return {"error": f"资源类型 {resource.resource_type} 不支持旁白，仅支持：{', '.join(sorted(NARRATABLE_TYPES))}"}

    # 强制重生成 → 删旧记录和音频文件
    if force_regenerate:
        existing = await Narration.filter(resource_id=resource_id, voice=voice).first()
        if existing:
            audio_dir = Path(__file__).parent.parent.parent / "static" / "audio" / str(resource_id)
            if audio_dir.exists():
                shutil.rmtree(audio_dir)
            await existing.delete()

    # 已有旁白 → 直接返回
    existing = await Narration.filter(resource_id=resource_id, voice=voice).first()
    if existing:
        return {
            "sections": existing.slides_json,
            "narration_id": existing.id,
            "resource_id": resource_id,
            "voice": voice,
            "cached": True,
        }

    sections = parse_by_type(resource.content or "", resource.resource_type or "document")
    if not sections:
        return {"error": "无法解析内容，资源可能为空"}

    base_dir = Path(__file__).parent.parent.parent / "static" / "audio" / str(resource_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    results = await _generate_sections_audio(sections, voice, base_dir, resource_id)

    # 入库
    record = await Narration.create(
        resource=resource,
        voice=voice,
        slides_json=results,
    )

    return {
        "narration_id": record.id,
        "sections": results,
        "resource_id": resource_id,
        "voice": voice,
        "cached": False,
    }


async def _generate_sections_audio(sections: list[dict], voice: str, base_dir: Path, resource_id: int) -> list[dict]:
    """并行生成所有段落的 TTS 音频，复用内容哈希缓存"""

    async def _tts_one(i: int, section: dict) -> dict | None:
        text = section.get("text", "")
        if not text:
            return None

        cache_key = hashlib.md5(f"{text}_{voice}".encode()).hexdigest()[:12]
        output_path = str(base_dir / f"{cache_key}.mp3")
        json_path = str(base_dir / f"{cache_key}.json")
        audio_url = f"/static/audio/{resource_id}/{cache_key}.mp3"

        if os.path.exists(output_path) and os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    word_timestamps = json.load(f)
                real_dur = _real_duration_from_timestamps(word_timestamps, section["duration_ms"])
                return {
                    "index": i,
                    "title": section["title"],
                    "text": text,
                    "audio_url": audio_url,
                    "duration_ms": real_dur,
                    "word_timestamps": word_timestamps,
                }
            except (json.JSONDecodeError, IOError):
                pass

        async with _TTS_SEMAPHORE:
            try:
                _, word_timestamps = await generate_audio_with_timestamps(text, output_path, voice)
            except Exception:
                logger.exception("EdgeTTS 生成失败 section=%d", i)
                return None

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(word_timestamps, f, ensure_ascii=False)
        except IOError:
            pass

        real_dur = _real_duration_from_timestamps(word_timestamps, section["duration_ms"])
        logger.info("narration resource=%d section=%d dur=%dms words=%d", resource_id, i, real_dur, len(word_timestamps))
        return {
            "index": i,
            "title": section["title"],
            "text": text,
            "audio_url": audio_url,
            "duration_ms": real_dur,
            "word_timestamps": word_timestamps,
        }

    tasks = [_tts_one(i, s) for i, s in enumerate(sections)]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for r in raw_results:
        if isinstance(r, dict) and r is not None:
            results.append(r)
        elif isinstance(r, Exception):
            logger.exception("TTS 任务异常: %s", r)

    results.sort(key=lambda x: x["index"])
    return results


def _real_duration_from_timestamps(word_timestamps: list[dict], fallback_ms: int) -> int:
    """从词级时间戳计算真实音频时长（最后一个词的 offset + duration），无时间戳时回退到估算值"""
    if word_timestamps:
        last = word_timestamps[-1]
        real = last.get("offset_ms", 0) + last.get("duration_ms", 0)
        if real > 0:
            return real
    return fallback_ms


async def list_narrations(user_id: int) -> list[dict]:
    """列出某个用户的所有旁白记录"""
    from backend.src.models.narration_model import Narration

    records = await Narration.filter(resource__user_id=user_id).prefetch_related("resource").order_by("-created_at").all()
    return [
        {
            "narration_id": r.id,
            "resource_id": r.resource_id,
            "resource_topic": r.resource.topic if r.resource else "",
            "resource_type": r.resource.resource_type if r.resource else "",
            "voice": r.voice,
            "sections_count": len(r.slides_json) if r.slides_json else 0,
            "total_duration_ms": sum(s.get("duration_ms", 0) for s in (r.slides_json or [])),
            "created_at": str(r.created_at),
        }
        for r in records
    ]


async def get_narration(narration_id: int, user_id: int) -> dict | None:
    """获取单个旁白详情"""
    from backend.src.models.narration_model import Narration

    record = await Narration.filter(id=narration_id, resource__user_id=user_id).prefetch_related("resource").first()
    if not record:
        return None
    return {
        "narration_id": record.id,
        "resource_id": record.resource_id,
        "resource_topic": record.resource.topic if record.resource else "",
        "resource_type": record.resource.resource_type if record.resource else "",
        "voice": record.voice,
        "sections": record.slides_json,
        "created_at": str(record.created_at),
    }


async def delete_narration(narration_id: int, user_id: int) -> bool:
    """删除旁白记录及对应音频文件夹"""
    from backend.src.models.narration_model import Narration

    record = await Narration.filter(id=narration_id, resource__user_id=user_id).first()
    if not record:
        return False

    resource_id = record.resource_id

    # 检查该 resource 是否有其他 voice 的旁白，没有才删文件夹
    others = await Narration.filter(resource_id=resource_id).exclude(id=narration_id).count()
    if others == 0:
        audio_dir = Path(__file__).parent.parent.parent / "static" / "audio" / str(resource_id)
        if audio_dir.exists():
            shutil.rmtree(audio_dir)

    await record.delete()
    return True
