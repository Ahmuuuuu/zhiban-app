import json
import logging

logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

from backend.src.ai_core.graph import resource_graph
from backend.src.utils.prompt_loader import fill_prompt
from backend.src.ai_core.llm_config import llm
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.agent_skill_model import AgentSkill
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User
from backend.src.utils.database import init_db
from backend.src.utils.json_parser import parse_llm_json
from backend.src.utils.mindmap import parse_mindmap_text

# 资源类型 → 文件扩展名映射
def _format_mindmap_content(content: str | None) -> str | dict | None:
    """mindmap 类型将缩进文本转为 JSON 树，其他类型原样返回"""
    if not content:
        return content
    try:
        return parse_mindmap_text(content)
    except Exception:
        logger.exception("思维导图 JSON 转换失败")
        return content


_FILE_EXT_MAP = {
    "document": "md",
    "ppt": "pptx",
    "mindmap": "txt",
    "exercise": "md",
    "case": "md",
    "reading": "md",
    "slide_animation": "json",
}

from backend.src.service.portrait_service import format_portrait
from backend.src.utils.knowledge_base import search as kb_search
from backend.src.utils.prompt_loader import load_prompt


async def _extract_topic_from_chat(user_id: int, chat_group_id: int) -> str:
    """从聊天记录中提取学习主题"""
    records = await ChatHistory.filter(
        user__id=user_id,
        chat_group_id=chat_group_id,
    ).order_by("created_at").all()

    if not records:
        return "通用学习"

    conversation = "\n".join(
        f"用户：{r.req}\nAI：{r.res[:200]}" for r in records
    )
    prompt = fill_prompt(load_prompt("resource/topic_extract"), conversation=conversation)
    response = await llm.ainvoke(prompt)
    return response.content.strip()


async def _next_chat_group_id(user_id: int) -> int:
    latest = await ChatHistory.filter(user_id=user_id).order_by("-chat_group_id").first()
    if not latest or not latest.chat_group_id:
        return 1
    return latest.chat_group_id + 1


async def _ensure_chat_group_id(user_id: int, chat_group_id: int = 0) -> int:
    return chat_group_id if chat_group_id and chat_group_id > 0 else await _next_chat_group_id(user_id)


def _resource_history_response(resources: list[dict]) -> str:
    if not resources:
        return "资源生成完成，但没有生成可保存的文件。"

    lines = ["已生成学习资源："]
    for resource in resources:
        file_type = resource.get("resource_type") or resource.get("file_type") or "resource"
        topic = resource.get("topic") or "学习资源"
        resource_id = resource.get("resource_id")
        ext = _FILE_EXT_MAP.get(file_type, "md")
        filename = f"{topic}_{file_type}.{ext}"
        if resource_id:
            lines.append(f"- [{filename}](/resource/{resource_id}/download)")
        else:
            lines.append(f"- {filename}")
    return "\n".join(lines)


async def _find_cached_resources(topic: str, user_id: int, resource_types: list[str]) -> list[dict] | None:
    """5 分钟内同主题同类型已生成过 → 直接返回缓存，避免重复跑 graph"""
    cutoff = datetime.now() - timedelta(minutes=5)
    existing = await GeneratedResource.filter(
        user_id=user_id,
        topic=topic,
        resource_type__in=resource_types,
        created_at__gte=cutoff,
    ).order_by("-created_at").all()

    if not existing:
        return None

    logger.info("命中缓存资源 user=%s topic=%s types=%s count=%d", user_id, topic, resource_types, len(existing))
    return [
        {
            "resource_id": r.id,
            "topic": r.topic,
            "resource_type": r.resource_type,
            "content": _format_mindmap_content(r.content) if r.resource_type == "mindmap" else r.content,
            "review_passed": r.review_passed,
            "retry_count": r.retry_count,
            "cached": True,
        }
        for r in existing
    ]


async def _save_generation_to_history(user_id: int, chat_group_id: int, req: str, resources: list[dict]) -> None:
    user = await User.filter(id=user_id).first()
    if not user:
        return
    await ChatHistory.create(
        user=user,
        chat_group_id=chat_group_id,
        req=req,
        res=_resource_history_response(resources),
    )


async def _make_state(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "single_choice, multi_choice, true_false", exam_count: int = 5, exam_difficulty: str = "medium") -> dict:
    await init_db()

    # 没传 topic 但有 chat_group_id → 从聊天记录自动提取
    if not topic and chat_group_id > 0:
        topic = await _extract_topic_from_chat(user_id, chat_group_id)

    portrait_context = "暂无画像数据"
    user = await User.filter(id=user_id).first()
    if user:
        picture = await user.picture
        if picture:
            from backend.src.service.portrait_service import PortraitRadarService
            try:
                radar_data = await PortraitRadarService.get(user_id)
            except Exception:
                radar_data = None
            portrait_context = "\n".join(format_portrait(picture, show_missing=False, radar_data=radar_data))

    kb_context = "暂无相关知识库资料"
    try:
        kb_result = await kb_search(topic, top_k=5, user_id=user_id)
        if kb_result and "暂无" not in kb_result:
            kb_context = kb_result
    except Exception:
        logger.exception("知识库搜索失败 topic=%s", topic)

    custom_prompts = {}
    skills = await AgentSkill.filter(user_id=user_id, enabled=True).all()
    for s in skills:
        if s.resource_type in resource_types and s.system_prompt:
            custom_prompts[s.resource_type] = s.system_prompt

    return {
        "user_id": str(user_id),
        "topic": topic,
        "resource_types": resource_types,
        "portrait_context": portrait_context,
        "kb_context": kb_context,
        "custom_prompts": custom_prompts,
        "generated_resources": {},
        "review_feedback": "",
        "review_passed": False,
        "retry_count": 0,
        "exam_question_types": exam_question_types,
        "exam_count": str(exam_count),
        "exam_difficulty": exam_difficulty,
    }


async def _save_resources(topic: str, user_id: int, generated: dict, review_passed: bool, retry_count: int) -> list[dict]:
    """存库并返回记录列表"""
    user = await User.filter(id=user_id).first()
    if not user:
        return []
    saved = []
    for rt, content in generated.items():
        record = await GeneratedResource.create(
            topic=topic,
            resource_type=rt,
            content=content,
            review_passed=review_passed,
            retry_count=retry_count,
            user=user,
        )
        saved.append({
            "resource_id": record.id,
            "topic": record.topic,
            "resource_type": record.resource_type,
            "content": record.content,
            "review_passed": record.review_passed,
            "retry_count": record.retry_count,
        })
    return saved


class ResourceService:

    @staticmethod
    async def generate_and_save(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "", exam_count: int = 5, exam_difficulty: str = "medium") -> list[dict]:
        chat_group_id = await _ensure_chat_group_id(user_id, chat_group_id)

        # ── 去重：近期已生成过同主题同类型资源 → 直接返回缓存 ──
        if topic:
            cached = await _find_cached_resources(topic, user_id, resource_types)
            if cached:
                await _save_generation_to_history(user_id, chat_group_id, topic, cached)
                return cached

        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, exam_question_types, exam_count, exam_difficulty)
        topic = initial_state["topic"]

        result = await resource_graph.ainvoke(initial_state)
        generated = result.get("generated_resources", {})
        saved = await _save_resources(
            topic, user_id,
            generated,
            result.get("review_passed", False),
            result.get("retry_count", 0),
        )
        await _save_generation_to_history(user_id, chat_group_id, topic, saved)

        # exercise 类型：解析 graph 输出的 JSON 题目 → 按 reviewer 逐题审核过滤 → 存 ExamQuestion 表
        reviewer_questions = result.get("reviewer_questions", [])
        question_quality = {q.get("index"): q.get("passed", True) for q in reviewer_questions} if reviewer_questions else {}

        for i, item in enumerate(saved):
            if item["resource_type"] == "exercise":
                try:
                    from backend.src.service.exam_service import ExamService  # deferred: circular exam<->resource

                    user = await User.filter(id=user_id).first()
                    if user:
                        questions = parse_llm_json(item.get("content", ""))
                        if isinstance(questions, list) and questions:
                            # 用 reviewer 逐题审核结果过滤掉 passed=false 的题
                            if question_quality:
                                questions = [q for idx, q in enumerate(questions) if question_quality.get(idx, True)]
                            if questions:
                                sid, _ = await ExamService._save_questions(questions, user, "medium")
                                if sid:
                                    await GeneratedResource.filter(id=item["resource_id"]).update(session_id=sid)
                                    saved[i]["session_id"] = sid
                                    saved[i]["question_count"] = len(questions)
                except Exception:
                    logger.exception("exercise 题目解析/存库失败 resource_id=%s", item.get("resource_id"))

        # mindmap 类型：缩进文本转为 JSON 树
        for item in saved:
            if item["resource_type"] == "mindmap":
                item["content"] = _format_mindmap_content(item.get("content"))

        return saved

    @staticmethod
    async def generate_stream(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "single_choice, multi_choice, true_false", exam_count: int = 5, exam_difficulty: str = "medium"):
        """节点级流式 — astream 逐节点产出状态，只跑一次 graph，同时推送文件事件"""
        chat_group_id = await _ensure_chat_group_id(user_id, chat_group_id)

        def _make_file_event(for_topic: str, rt: str, content: str) -> str:
            ext = _FILE_EXT_MAP.get(rt, "md")
            filename = f"{for_topic}_{rt}.{ext}"
            event_content = content
            if rt == "mindmap":
                try:
                    event_content = parse_mindmap_text(content)
                except Exception:
                    logger.exception("SSE 思维导图 JSON 转换失败")
            return f"data: {json.dumps({'type': 'file', 'file_type': rt, 'filename': filename, 'content': event_content}, ensure_ascii=False)}\n\n"

        # ── 去重：近期已生成过 → 直接推送缓存结果 ──
        if topic:
            cached = await _find_cached_resources(topic, user_id, resource_types)
            if cached:
                async def _replay_cache():
                    for r in cached:
                        rt = r["resource_type"]
                        content = r["content"]
                        if isinstance(content, dict):
                            content = json.dumps(content, ensure_ascii=False)
                        yield _make_file_event(r["topic"], rt, content)
                        yield f"data: {json.dumps({'resources': [rt], 'review_passed': True}, ensure_ascii=False)}\n\n"
                    done_data = {
                        "done": True,
                        "chat_group_id": chat_group_id,
                        "resources": [
                            {"resource_id": r["resource_id"], "file_type": r["resource_type"],
                             "topic": r["topic"], "download_url": f"/resource/{r['resource_id']}/download"}
                            for r in cached
                        ],
                    }
                    yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                await _save_generation_to_history(user_id, chat_group_id, topic, cached)
                async for item in _replay_cache():
                    yield item
                return

        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, exam_question_types, exam_count, exam_difficulty)
        topic = initial_state["topic"]
        final_resources = {}
        final_passed = False
        final_retry = 0
        yielded_types: set[str] = set()

        async for chunk in resource_graph.astream(initial_state, stream_mode="values"):
            resources = chunk.get("generated_resources", {})
            if resources:
                final_resources = resources
                # 有新产出的资源类型 → 推送文件事件
                for rt, content in resources.items():
                    if rt not in yielded_types:
                        yielded_types.add(rt)
                        yield _make_file_event(topic, rt, content)
            final_passed = chunk.get("review_passed", False)
            final_retry = chunk.get("retry_count", 0)

            yield f"data: {json.dumps({'resources': list(resources.keys()), 'review_passed': final_passed}, ensure_ascii=False)}\n\n"

        # 流式结束后存库
        saved = await _save_resources(topic, user_id, final_resources, final_passed, final_retry)
        await _save_generation_to_history(user_id, chat_group_id, topic, saved)
        # 在 done 事件中附带 download_url
        done_data = {
            "done": True,
            "chat_group_id": chat_group_id,
            "resources": [
                {
                    "resource_id": r["resource_id"],
                    "file_type": r["resource_type"],
                    "topic": r["topic"],
                    "download_url": f"/resource/{r['resource_id']}/download",
                }
                for r in saved
            ],
        }
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    @staticmethod
    async def get_resource(resource_id: int, user_id: int) -> dict | None:
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return None
        content = record.content
        if record.resource_type == "mindmap":
            content = _format_mindmap_content(content)

        result = {
            "resource_id": record.id,
            "topic": record.topic,
            "resource_type": record.resource_type,
            "content": content,
            "review_passed": record.review_passed,
            "retry_count": record.retry_count,
            "created_at": str(record.created_at),
        }

        # PPT 资源 → 按页拆成 slides 预览数组
        if record.resource_type == "ppt" and record.content:
            try:
                from backend.src.utils.tts_utils import parse_slides
                slides_data = parse_slides(record.content)
                result["slides"] = [{"index": i, "title": s["title"], "text": s["text"], "notes": s.get("notes", "")} for i, s in enumerate(slides_data)]
            except Exception:
                pass

        # 附带旁白数据（如有）
        try:
            from backend.src.utils.tts_utils import NARRATABLE_TYPES
            if record.resource_type in NARRATABLE_TYPES:
                from backend.src.models.narration_model import Narration
                narration = await Narration.filter(resource_id=resource_id).order_by("-created_at").first()
                if narration:
                    result["narration"] = {
                        "narration_id": narration.id,
                        "voice": narration.voice,
                        "sections": narration.slides_json,
                        "created_at": str(narration.created_at),
                    }
        except Exception:
            pass  # 旁白查询失败不影响主流程

        return result

    @staticmethod
    async def list_resources(user_id: int) -> list[dict]:
        records = await GeneratedResource.filter(user_id=user_id).order_by("-created_at").all()
        result = []
        for r in records:
            ext = _FILE_EXT_MAP.get(r.resource_type, "md")
            preview = r.content[:200] if r.content else ""
            if r.resource_type == "mindmap" and r.content:
                try:
                    preview = parse_mindmap_text(r.content)
                except Exception:
                    logger.exception("思维导图预览 JSON 转换失败 resource_id=%s", r.id)
            item = {
                "resource_id": r.id,
                "topic": r.topic,
                "resource_type": r.resource_type,
                "filename": f"{r.topic}_{r.resource_type}.{ext}",
                "file_type": ext,
                "preview": preview,
                "download_url": f"/resource/{r.id}/download",
                "review_passed": r.review_passed,
                "created_at": str(r.created_at),
            }
            result.append(item)
        return result

    @staticmethod
    async def download_resource(resource_id: int, user_id: int) -> tuple[bytes, str, str] | None:
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return None
        ext = _FILE_EXT_MAP.get(record.resource_type, "md")
        filename = f"{record.topic}_{record.resource_type}.{ext}"
        if record.resource_type == "ppt":
            try:
                from backend.src.utils.pptx_generator import markdown_to_pptx  # deferred: optional python-pptx dependency
            except ImportError:
                raise ImportError("PPT 导出需要安装 python-pptx 依赖")
            content_bytes = markdown_to_pptx(record.content)
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            return content_bytes, filename, media_type
        else:
            return record.content.encode("utf-8"), filename, "text/markdown; charset=utf-8"

    @staticmethod
    async def delete_resource(resource_id: int, user_id: int) -> bool:
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return False
        await record.delete()
        return True
