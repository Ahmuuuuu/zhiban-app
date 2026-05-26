"""语音旁白服务 — 对文字类资源调用 EdgeTTS 逐段生成旁白 (CRUD)"""

import logging
from pathlib import Path
import shutil

from backend.src.utils.tts_utils import parse_by_type, generate_audio, NARRATABLE_TYPES

logger = logging.getLogger(__name__)


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

    # 按资源 ID 建子文件夹
    base_dir = Path(__file__).parent.parent.parent / "static" / "audio" / str(resource_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, section in enumerate(sections):
        if not section["text"]:
            continue
        filename = f"section{i}_{voice}.mp3"
        output_path = str(base_dir / filename)

        try:
            await generate_audio(section["text"], output_path, voice)
        except Exception:
            logger.exception("EdgeTTS 生成失败 section=%d", i)
            continue

        audio_url = f"/static/audio/{resource_id}/{filename}"
        results.append({
            "index": i,
            "title": section["title"],
            "text": section["text"],
            "audio_url": audio_url,
            "duration_ms": section["duration_ms"],
        })
        logger.info("narration resource=%d section=%d dur=%dms", resource_id, i, section["duration_ms"])

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
