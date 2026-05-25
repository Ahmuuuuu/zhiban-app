"""语音旁白服务 — 对 PPT 资源调用 EdgeTTS 逐页生成旁白"""

import logging
from pathlib import Path

from backend.src.utils.tts_utils import parse_slides, generate_audio

logger = logging.getLogger(__name__)


async def narrate_resource(resource_id: int, voice: str = "zh-CN-XiaoxiaoNeural"):
    """对某个 PPT 资源逐页生成旁白，已有则直接返回，无则生成写入 DB

    Returns:
        {"slides": [...], "resource_id": int, "voice": str, "cached": bool}
    """
    from backend.src.models.resource_model import GeneratedResource
    from backend.src.models.narration_model import Narration

    resource = await GeneratedResource.filter(id=resource_id).first()
    if not resource:
        return {"error": "资源不存在"}
    if resource.resource_type != "ppt":
        return {"error": f"资源类型为 {resource.resource_type}，仅支持 ppt"}

    # 已有旁白 → 直接返回
    existing = await Narration.filter(resource_id=resource_id, voice=voice).first()
    if existing:
        return {
            "slides": existing.slides_json,
            "resource_id": resource_id,
            "voice": voice,
            "cached": True,
        }

    slides = parse_slides(resource.content or "")
    if not slides:
        return {"error": "无法解析幻灯片内容"}

    # 按资源 ID 建子文件夹
    base_dir = Path(__file__).parent.parent.parent / "static" / "audio" / str(resource_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, slide in enumerate(slides):
        if not slide["text"]:
            continue
        filename = f"slide{i}_{voice}.mp3"
        output_path = str(base_dir / filename)

        try:
            await generate_audio(slide["text"], output_path, voice)
        except Exception:
            logger.exception("EdgeTTS 生成失败 slide=%d", i)
            continue

        audio_url = f"/static/audio/{resource_id}/{filename}"
        results.append({
            "index": i,
            "title": slide["title"],
            "text": slide["text"],
            "audio_url": audio_url,
            "duration_ms": slide["duration_ms"],
        })
        logger.info("narration resource=%d slide=%d dur=%dms", resource_id, i, slide["duration_ms"])

    # 入库
    await Narration.create(
        resource=resource,
        voice=voice,
        slides_json=results,
    )

    return {
        "slides": results,
        "resource_id": resource_id,
        "voice": voice,
        "cached": False,
    }
