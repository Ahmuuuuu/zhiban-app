import asyncio
import json
import logging
import uuid

from tortoise.expressions import F

logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

from backend.src.ai_core.resource_graph import resource_graph
from backend.src.utils.prompt_loader import fill_prompt
from backend.src.ai_core.llm_config import llm
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.agent_skill_model import AgentSkill
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User
from backend.src.models.notification_model import Notification
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
    "audio": "mp3",
    "html": "html",
}


async def _generate_resource_title(topic: str, type_names: list[str]) -> str:
    """为生成的学习资源起一个标题"""
    types_str = "、".join(type_names)
    return f"「{topic}」{types_str}"


# ─── 任务 SSE 通知队列 ───
_task_sse_queues: dict[str, list] = {}


def _subscribe_task_sse(task_id: str):
    """为生成任务 SSE 客户端创建消息队列"""
    q: list = []
    _task_sse_queues.setdefault(task_id, []).append(q)
    return q


def _unsubscribe_task_sse(task_id: str, q: list):
    queues = _task_sse_queues.get(task_id, [])
    if q in queues:
        queues.remove(q)
    if not queues:
        _task_sse_queues.pop(task_id, None)


async def _notify_task_sse(task_id: str, data: dict):
    """通知所有 SSE 客户端"""
    for q in _task_sse_queues.get(task_id, []):
        q.append(data)

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
        review_passed=True,
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


async def _make_state(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "single_choice, multi_choice, true_false", exam_count: int = 5, exam_difficulty: str = "medium", answers: dict | None = None, skip_review: bool = False) -> dict:
    await init_db()

    # 没传 topic 但有 chat_group_id → 从聊天记录自动提取
    if not topic and chat_group_id > 0:
        topic = await _extract_topic_from_chat(user_id, chat_group_id)

    from backend.src.service.portrait_service import PortraitRadarService, build_learning_guidance

    portrait_context = "暂无画像数据"
    learning_guidance = ""

    # 并行：画像/用户查询 + 学习指导 + KB搜索 + Skills
    user_task = User.filter(id=user_id).first()
    guidance_task = build_learning_guidance(user_id)
    kb_task = kb_search(topic, top_k=5, user_id=user_id)
    skills_task = AgentSkill.filter(user_id=user_id, enabled=True).all()

    user, learning_guidance, kb_result, skills = await asyncio.gather(
        user_task, guidance_task, kb_task, skills_task, return_exceptions=True
    )

    if isinstance(learning_guidance, Exception):
        logger.exception("学习指导生成失败 user_id=%s", user_id)
        learning_guidance = ""

    if isinstance(kb_result, Exception):
        logger.exception("知识库搜索失败 topic=%s", topic)
        kb_result = "暂无相关知识库资料"

    if isinstance(skills, Exception):
        logger.exception("Skills 查询失败 user_id=%s", user_id)
        skills = []

    if user and not isinstance(user, Exception):
        picture = await user.picture
        if picture:
            try:
                radar_data = await PortraitRadarService.get(user_id)
            except Exception:
                radar_data = None
            portrait_context = "\n".join(format_portrait(picture, show_missing=False, radar_data=radar_data))

    kb_context = "暂无相关知识库资料"
    if kb_result and not isinstance(kb_result, Exception) and "暂无" not in str(kb_result):
        kb_context = kb_result

    custom_prompts = {}
    for s in skills:
        if s.resource_type in resource_types and s.system_prompt:
            custom_prompts[s.resource_type] = s.system_prompt

    return {
        "user_id": str(user_id),
        "topic": topic,
        "resource_types": resource_types,
        "portrait_context": portrait_context,
        "kb_context": kb_context,
        "learning_guidance": learning_guidance,
        "custom_prompts": custom_prompts,
        "generated_resources": {},
        "review_feedback": "",
        "review_passed": False,
        "retry_count": 0,
        "exam_question_types": exam_question_types,
        "exam_count": str(exam_count),
        "exam_difficulty": exam_difficulty,
        "answers": answers or {},
        "skip_review": skip_review,
    }


def build_cover_url(resource_type: str, file_url: str | None, resource_id: int) -> str | None:
    """根据资源类型和文件URL生成封面图URL"""
    if resource_type == "image" and file_url:
        return file_url
    return f"/static/covers/default_{resource_type}.svg"


async def _save_resources(topic: str, user_id: int, generated: dict, review_passed: bool, retry_count: int,
                          file_urls: dict | None = None) -> list[dict]:
    """存库并返回记录列表"""
    user = await User.filter(id=user_id).first()
    if not user:
        return []
    file_urls = file_urls or {}
    saved = []
    for rt, content in generated.items():
        record = await GeneratedResource.create(
            topic=topic,
            resource_type=rt,
            content=content,
            review_passed=review_passed,
            retry_count=retry_count,
            file_url=file_urls.get(rt),
            user=user,
        )
        # 设置封面
        cover_url = build_cover_url(rt, file_urls.get(rt), record.id)
        if cover_url:
            await GeneratedResource.filter(id=record.id).update(cover_url=cover_url)
        saved.append({
            "resource_id": record.id,
            "topic": record.topic,
            "resource_type": record.resource_type,
            "content": record.content,
            "review_passed": record.review_passed,
            "retry_count": record.retry_count,
            "file_url": record.file_url,
            "cover_url": cover_url,
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
            file_urls=result.get("file_urls"),
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
    async def generate_stream(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "single_choice, multi_choice, true_false", exam_count: int = 5, exam_difficulty: str = "medium", skip_review: bool = False):
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

        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, exam_question_types, exam_count, exam_difficulty, skip_review=skip_review)
        topic = initial_state["topic"]
        final_resources = {}
        final_passed = False
        final_retry = 0
        final_file_urls = {}
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
            # 追踪 file_urls（image 类型在 executor 产出）
            chunk_file_urls = chunk.get("file_urls", {})
            if chunk_file_urls:
                final_file_urls.update(chunk_file_urls)
            final_passed = chunk.get("review_passed", False)
            final_retry = chunk.get("retry_count", 0)

            yield f"data: {json.dumps({'resources': list(resources.keys()), 'review_passed': final_passed}, ensure_ascii=False)}\n\n"

        # 流式结束后存库
        saved = await _save_resources(topic, user_id, final_resources, final_passed, final_retry,
                                      file_urls=final_file_urls)
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
    async def toggle_like(resource_id: int, user_id: int) -> dict:
        """切换点赞状态，返回当前是否点赞和点赞总数"""
        from backend.src.models.study_model import ResourceLike
        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError("用户不存在")
        resource = await GeneratedResource.filter(id=resource_id).first()
        if not resource:
            raise ValueError("资源不存在")

        existing = await ResourceLike.filter(user_id=user_id, resource_id=resource_id).first()
        if existing:
            await existing.delete()
            await GeneratedResource.filter(id=resource_id).update(like_count=F('like_count') - 1)
            await resource.refresh_from_db()
            return {"liked": False, "like_count": resource.like_count}
        else:
            await ResourceLike.create(user=user, resource=resource)
            await GeneratedResource.filter(id=resource_id).update(like_count=F('like_count') + 1)
            await resource.refresh_from_db()
            return {"liked": True, "like_count": resource.like_count}

    @staticmethod
    async def toggle_favorite(resource_id: int, user_id: int) -> dict:
        """切换收藏状态，返回当前是否收藏和收藏总数"""
        from backend.src.models.study_model import ResourceCollection
        user = await User.filter(id=user_id).first()
        if not user:
            raise ValueError("用户不存在")
        resource = await GeneratedResource.filter(id=resource_id).first()
        if not resource:
            raise ValueError("资源不存在")

        existing = await ResourceCollection.filter(user_id=user_id, resource_id=resource_id).first()
        if existing:
            await existing.delete()
            await GeneratedResource.filter(id=resource_id).update(favorite_count=F('favorite_count') - 1)
            await resource.refresh_from_db()
            return {"favorited": False, "favorite_count": resource.favorite_count}
        else:
            await ResourceCollection.create(user=user, resource=resource)
            await GeneratedResource.filter(id=resource_id).update(favorite_count=F('favorite_count') + 1)
            await resource.refresh_from_db()
            return {"favorited": True, "favorite_count": resource.favorite_count}

    @staticmethod
    async def get_resource(resource_id: int, user_id: int) -> dict | None:
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return None
        # 原子递增查看计数
        await GeneratedResource.filter(id=resource_id, user_id=user_id).update(
            view_count=F('view_count') + 1, last_viewed_at=datetime.now()
        )
        await record.refresh_from_db()
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
            "view_count": record.view_count,
            "download_count": record.download_count,
            "like_count": record.like_count,
            "favorite_count": record.favorite_count,
            "cover_url": record.cover_url,
        }

        # 当前用户的交互状态
        from backend.src.models.study_model import ResourceLike, ResourceCollection
        liked = await ResourceLike.filter(user_id=user_id, resource_id=resource_id).exists()
        favorited = await ResourceCollection.filter(user_id=user_id, resource_id=resource_id).exists()
        result["liked"] = liked
        result["favorited"] = favorited

        # PPT 资源 → 按页拆成 slides 预览数组（仅 LLM 生成的 markdown 可解析）
        if record.resource_type == "ppt" and record.content and record.content.startswith("#"):
            try:
                from backend.src.utils.tts_utils import parse_slides
                slides_data = parse_slides(record.content)

                result["slides"] = [
                    {"index": i, "title": s["title"], "text": s["text"], "notes": s.get("notes", "")}
                    for i, s in enumerate(slides_data)
                ]
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
                "view_count": r.view_count,
                "download_count": r.download_count,
                "like_count": r.like_count,
                "favorite_count": r.favorite_count,
                "cover_url": r.cover_url,
            }
            # 附带当前用户的交互状态
            from backend.src.models.study_model import ResourceLike, ResourceCollection
            item["liked"] = await ResourceLike.filter(user_id=user_id, resource_id=r.id).exists()
            item["favorited"] = await ResourceCollection.filter(user_id=user_id, resource_id=r.id).exists()
            result.append(item)
        return result

    @staticmethod
    async def download_resource(resource_id: int, user_id: int) -> tuple[bytes, str, str] | None:
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return None
        record.download_count += 1
        await record.save()
        ext = _FILE_EXT_MAP.get(record.resource_type, "md")
        filename = f"{record.topic}_{record.resource_type}.{ext}"
        if record.resource_type == "ppt":
            # LLM 生成的 markdown → python-pptx
            try:
                from backend.src.utils.pptx_generator import markdown_to_pptx
            except ImportError:
                raise ImportError("PPT 导出需要安装 python-pptx 依赖")

            content_bytes = markdown_to_pptx(record.content)
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            return content_bytes, f"{record.topic}_ppt.pptx", media_type
        else:
            return record.content.encode("utf-8"), filename, "text/markdown; charset=utf-8"

    @staticmethod
    async def delete_resource(resource_id: int, user_id: int) -> bool:
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return False
        await record.delete()
        return True

    # ═══════════════════════════════════════════
    #  任务管理
    # ═══════════════════════════════════════════

    @staticmethod
    async def create_task(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, answers: dict | None = None) -> dict:
        """创建生成任务，启动后台运行，立即返回 task_id"""
        from backend.src.models.task_model import GenerationTask

        tid = uuid.uuid4().hex
        task = await GenerationTask.create(
            task_id=tid,
            user_id=user_id,
            topic=topic or "",
            resource_types=json.dumps(resource_types, ensure_ascii=False),
            chat_group_id=chat_group_id or None,
            status="pending",
        )
        asyncio.ensure_future(_run_generation_task(task.id, tid, answers))
        return {"task_id": tid, "status": "pending"}

    @staticmethod
    async def get_task(task_id: str, user_id: int) -> dict | None:
        """查询任务状态"""
        from backend.src.models.task_model import GenerationTask

        task = await GenerationTask.filter(task_id=task_id, user_id=user_id).first()
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "topic": task.topic,
            "resource_types": json.loads(task.resource_types) if task.resource_types else [],
            "chat_group_id": task.chat_group_id,
            "status": task.status,
            "progress": task.progress,
            "progress_msg": task.progress_msg,
            "result": json.loads(task.result) if task.result else None,
            "error": task.error,
            "created_at": str(task.created_at),
            "updated_at": str(task.updated_at),
        }

    @staticmethod
    async def list_tasks(user_id: int) -> list[dict]:
        """列出该用户最近的任务"""
        from backend.src.models.task_model import GenerationTask

        tasks = await GenerationTask.filter(user_id=user_id).order_by("-created_at").limit(20).all()
        return [
            {
                "task_id": t.task_id,
                "topic": t.topic,
                "resource_types": json.loads(t.resource_types) if t.resource_types else [],
                "status": t.status,
                "progress": t.progress,
                "progress_msg": t.progress_msg,
                "error": t.error,
                "created_at": str(t.created_at),
            }
            for t in tasks
        ]

    @staticmethod
    async def init_tasks():
        """启动时清理未完成任务（进程重启后未完成的任务标记为失败）"""
        from backend.src.models.task_model import GenerationTask

        abandoned = await GenerationTask.filter(status__in=["pending", "running"]).all()
        for t in abandoned:
            t.status = "failed"
            t.error = "服务重启，任务已中止"
            await t.save()


# ═══════════════════════════════════════════════
#  后台任务执行
# ═══════════════════════════════════════════════

async def _run_generation_task(db_id: int, task_id: str, answers: dict | None = None):
    """后台运行资源生成任务，更新 DB 进度并推送 SSE"""
    from backend.src.models.task_model import GenerationTask

    try:
        task = await GenerationTask.filter(id=db_id).first()
        if not task:
            return

        user_id = task.user_id
        resource_types = json.loads(task.resource_types) if task.resource_types else ["document"]
        chat_group_id = await _ensure_chat_group_id(user_id, task.chat_group_id or 0)
        if chat_group_id != (task.chat_group_id or 0):
            task.chat_group_id = chat_group_id
            await task.save()
        topic = task.topic

        task.status = "running"
        task.progress = 5
        task.progress_msg = "正在初始化…"
        await task.save()
        await _notify_task_sse(task_id, {"type": "status", "status": "running", "progress": 5, "progress_msg": "正在初始化…"})

        # 构建 graph 初始状态
        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, answers=answers)
        topic = initial_state["topic"]

        # 更新 topic（可能从聊天记录提取）
        if topic != task.topic:
            task.topic = topic
            await task.save()

        final_resources: dict = {}
        final_passed = False
        final_retry = 0
        final_file_urls: dict = {}
        yielded_types: set[str] = set()
        total_types = len(resource_types)

        task.progress = 10
        task.progress_msg = "AI 规划中…"
        await task.save()
        await _notify_task_sse(task_id, {"type": "status", "status": "running", "progress": 10, "progress_msg": "AI 规划中…"})

        async for chunk in resource_graph.astream(initial_state, stream_mode="values"):
            resources = chunk.get("generated_resources", {})
            if resources:
                final_resources = resources
                # 统计已产出的类型数
                for rt in resources.keys():
                    if rt not in yielded_types:
                        yielded_types.add(rt)
                        done = len(yielded_types)
                        pct = 20 + int((done / max(total_types, 1)) * 40)  # 20-60%
                        task.progress = min(pct, 85)
                        task.progress_msg = f"正在生成「{rt}」…"
                        await task.save()
                        await _notify_task_sse(task_id, {
                            "type": "progress",
                            "resource_type": rt,
                            "progress": task.progress,
                            "progress_msg": task.progress_msg,
                        })

            chunk_file_urls = chunk.get("file_urls", {})
            if chunk_file_urls:
                final_file_urls.update(chunk_file_urls)
            final_passed = chunk.get("review_passed", False)
            final_retry = chunk.get("retry_count", 0)

        # 审核阶段
        task.progress = 70
        task.progress_msg = "AI 审核中…"
        await task.save()
        await _notify_task_sse(task_id, {"type": "status", "progress": 70, "progress_msg": "AI 审核中…"})

        # 保存到 DB
        task.progress = 85
        task.progress_msg = "正在保存…"
        await task.save()
        await _notify_task_sse(task_id, {"type": "status", "progress": 85, "progress_msg": "正在保存…"})

        saved = await _save_resources(topic, user_id, final_resources, final_passed, final_retry,
                                      file_urls=final_file_urls)

        # 保存到聊天历史
        await _save_generation_to_history(user_id, chat_group_id, topic, saved)

        # 记录结果
        result_data = [
            {
                "resource_id": r["resource_id"],
                "file_type": r["resource_type"],
                "topic": r["topic"],
                "download_url": f"/resource/{r['resource_id']}/download",
            }
            for r in saved
        ]

        task.status = "success"
        task.progress = 100
        task.progress_msg = "生成完成"
        task.result = json.dumps(result_data, ensure_ascii=False)
        await task.save()

        # 生成标题
        type_labels = {"document": "文献", "exercise": "习题", "mindmap": "思维导图", "ppt": "PPT", "image": "图片"}
        type_names = [type_labels.get(r["resource_type"], r["resource_type"]) for r in saved]
        gen_title = await _generate_resource_title(task.topic, type_names)

        await _notify_task_sse(task_id, {
            "type": "done",
            "status": "success",
            "progress": 100,
            "title": gen_title,
            "result": result_data,
        })
        await _notify_task_sse(task_id, {"type": "__close__"})

        await Notification.create(
            type="resource",
            title=gen_title,
            content=f"「{task.topic}」的{'、'.join(type_names)}已生成，共 {len(saved)} 份",
            target_url="/resource",
            target_user_id=user_id,
        )

        # 阶段2优化：后台预生成旁白音频，用户作答追问期间音频已缓存好
        for r in saved:
            if r["resource_type"] in ("document", "ppt"):
                asyncio.ensure_future(_pre_generate_narration(r["resource_id"]))

    except Exception as e:
        logger.exception("生成任务失败 task_id=%s", task_id)
        try:
            task = await GenerationTask.filter(id=db_id).first()
            if task:
                task.status = "failed"
                task.error = str(e)
                await task.save()
                await _notify_task_sse(task_id, {
                    "type": "done",
                    "status": "failed",
                    "error": str(e),
                })
                await _notify_task_sse(task_id, {"type": "__close__"})
                await Notification.create(
                    type="resource",
                    title="资源生成失败",
                    content=f"「{task.topic}」生成失败：{str(e)[:100]}",
                    target_url="/resource",
                    target_user_id=task.user_id,
                )
        except Exception:
            logger.exception("更新失败任务状态出错 task_id=%s", task_id)


async def _pre_generate_narration(resource_id: int, voice: str = "zh-CN-XiaoxiaoNeural"):
    """后台预生成旁白音频，后续课件构建时可复用缓存"""
    try:
        from backend.src.service.narration_service import narrate_resource
        await narrate_resource(resource_id, voice)
    except Exception:
        logger.exception("预生成旁白音频失败 resource_id=%s", resource_id)
