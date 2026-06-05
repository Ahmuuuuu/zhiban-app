"""动画编排工具 — 对已生成旁白的资源编排逐页动画 JSON"""

import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def generate_slide_animation(resource_id: str, user_id: str, chat_group_id: str = "0"):
    """对已生成 TTS 旁白的学习资源（PPT/文档等）编排动画时间轴。
先确保已调用 narate_resource 生成了旁白，再调用此工具生成播放动画 JSON。
参数：resource_id资源数字ID，user_id用户数字ID，chat_group_id聊天组ID"""

    from backend.src.models.resource_model import GeneratedResource
    from backend.src.models.narration_model import Narration
    from backend.src.models.chat_history_model import ChatHistory
    from backend.src.models.usermodel import User
    from backend.src.ai_core.llm_config import llm
    from backend.src.utils.prompt_loader import load_prompt, fill_prompt

    uid = int(user_id.strip())
    gid = int(chat_group_id) if str(chat_group_id).isdigit() else 0
    rid = int(str(resource_id).strip())

    resource = await GeneratedResource.filter(id=rid, user_id=uid).first()
    if not resource:
        return "资源不存在或无权访问"

    narration = await Narration.filter(resource_id=rid).order_by("-created_at").first()
    if not narration or not narration.slides_json:
        return "请先对该资源生成旁白语音（narrate_resource），再生成动画"

    sections = narration.slides_json
    sections_for_prompt = json.dumps(
        [{"index": s["index"], "title": s.get("title", ""), "text": s.get("text", ""),
          "audio_url": s.get("audio_url", ""), "duration_ms": s.get("duration_ms", 0)}
         for s in sections],
        ensure_ascii=False, indent=2
    )

    prompt = load_prompt("resource/animation")
    filled = fill_prompt(
        prompt,
        topic=resource.topic or "",
        voice=narration.voice,
        sections_json=sections_for_prompt,
    )

    response = await llm.ainvoke(filled)
    raw = response.content if hasattr(response, "content") else str(response)

    # 大括号匹配提取 JSON（LLM 可能输出 ```json 包裹或只输出纯 JSON）
    json_text = raw.strip()
    first_brace = json_text.find("{")
    last_brace = json_text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        json_text = json_text[first_brace:last_brace + 1]

    try:
        animation = json.loads(json_text)
        slides = animation.get("slides", [])
        if not slides:
            return f"动画生成失败：JSON 缺少 slides 字段。原始响应: {raw[:300]}"

    except json.JSONDecodeError:
        logger.exception("动画 JSON 解析失败")
        return f"动画 JSON 解析失败，请重试。原始响应: {raw[:300]}"

    animation_content = json.dumps(animation, ensure_ascii=False)

    # 存为新资源
    user = await User.filter(id=uid).first()
    anim = await GeneratedResource.create(
        user_id=uid,
        topic=f"动画-{resource.topic}",
        resource_type="slide_animation",
        content=animation_content,
        review_passed=True,
    )

    total_slides = len(slides)

    # 关联到聊天组
    if gid > 0 and user:
        await ChatHistory.create(
            user=user,
            chat_group_id=gid,
            req=f"生成动画-{resource.topic}",
            res=f"已生成动画时间轴（资源ID: {anim.id}）：{total_slides} 页幻灯片",
        )
    total_ms = animation.get("config", {}).get("total_duration_ms", 0)
    return (
        f"已生成动画时间轴（资源ID: {anim.id}）："
        f"{total_slides} 页幻灯片，总时长约 {total_ms // 1000} 秒。"
        f"前端可通过 GET /resource/{anim.id} 获取动画 JSON。"
    )
