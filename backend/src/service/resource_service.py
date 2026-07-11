import asyncio
import hashlib
import json
import logging
import time
import uuid

from tortoise.expressions import F, Q

logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

from backend.src.ai_core.resource_graph import resource_graph
from backend.src.utils.prompt_loader import fill_prompt
from backend.src.utils.chat_utils import allocate_chat_group_id
from backend.src.utils.redis_client import subscribe_sse, unsubscribe_sse, notify_sse, replay_sse, get_redis as _get_redis
from backend.src.utils.constants import TASK_CACHE_TTL_RUNNING, TASK_CACHE_TTL_DONE
from backend.src.ai_core.llm_config import llm
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.agent_skill_model import AgentSkill
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User
from backend.src.models.notification_model import Notification

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
    "video": "html",
    "external_video": "url",
}


async def _generate_resource_title(topic: str, type_names: list[str]) -> str:
    """为生成的学习资源起一个标题"""
    types_str = "、".join(type_names)
    return f"「{topic}」{types_str}"


# ─── 任务 SSE 通知队列（基于 Redis Pub/Sub + Stream，兼容多进程）───
# 使用 redis_client 的统一 SSE 机制：本地进程走内存队列，跨进程走 Redis


def _subscribe_task_sse(task_id: str):
    """为生成任务 SSE 客户端创建消息队列"""
    return subscribe_sse(f"task:{task_id}")


def _unsubscribe_task_sse(task_id: str, q: list):
    """取消 SSE 订阅"""
    unsubscribe_sse(f"task:{task_id}", q)


async def _notify_task_sse(task_id: str, data: dict):
    """通知所有 SSE 客户端（本地内存 + Redis Pub/Sub + Stream）"""
    await notify_sse(f"task:{task_id}", data)


# ─── Task 状态 Redis 缓存 ───
# key: task:{task_id}:state → JSON, TTL: 30s（生成中）/ 300s（已完成）


async def _cache_task_state(task_id: str, state: dict):
    """写 Task 状态到 Redis 缓存（非关键，异常静默降级）"""
    try:
        r = await _get_redis()
        ttl = TASK_CACHE_TTL_DONE if state.get("status") in ("success", "failed") else TASK_CACHE_TTL_RUNNING
        await r.setex(f"task:{task_id}:state", ttl, json.dumps(state, ensure_ascii=False))
    except Exception:
        logger.debug("Task 状态缓存失败 task_id=%s status=%s（降级运行）", task_id, state.get("status"))

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


async def _ensure_chat_group_id(user_id: int, chat_group_id: int = 0) -> int:
    """返回有效的 chat_group_id；为 0 时不再自动分配（学习路径等场景不需要聊天组）"""
    return chat_group_id if chat_group_id and chat_group_id > 0 else 0




async def _ensure_generation_chat_group_id(user_id: int, chat_group_id: int = 0, bind_chat_history: bool = False) -> int:
    if chat_group_id and chat_group_id > 0:
        return chat_group_id
    if bind_chat_history:
        return await allocate_chat_group_id(user_id)
    return 0


def _resource_history_response(resources: list[dict]) -> str:
    if not resources:
        return json.dumps({
            "type": "resource_list",
            "resources": [],
            "message": "资源生成完成，但没有生成可保存的文件。",
        }, ensure_ascii=False)

    items = []
    for resource in resources:
        file_type = resource.get("resource_type") or resource.get("file_type") or "resource"
        topic = resource.get("topic") or "学习资源"
        resource_id = resource.get("resource_id")
        ext = _FILE_EXT_MAP.get(file_type, "md")
        # 优先使用资源自带的 filename（外部视频有自定义标题）
        filename = resource.get("filename") or f"{topic}_{file_type}.{ext}"
        item = {
            "type": "resource",
            "file_type": file_type,
            "filename": filename,
            "file_id": resource_id,
            "resource_id": resource_id,
            "download_url": f"/resource/{resource_id}/download" if resource_id else None,
            "topic": topic,
        }
        # 外部视频：保留封面、嵌入地址等展示字段，刷新后仍能正常渲染卡片
        if file_type == "external_video":
            for k in ("cover_url", "embed_url", "title", "author", "duration_text",
                      "view_count_text", "source", "source_label", "description", "file_url", "preview_url"):
                if resource.get(k):
                    item[k] = resource[k]
        items.append(item)

    return json.dumps({
        "type": "resource_list",
        "resources": items,
    }, ensure_ascii=False)



async def _save_generation_to_history(user_id: int, chat_group_id: int, req: str, resources: list[dict]) -> None:
    if not chat_group_id or chat_group_id <= 0:
        logger.warning("跳过历史保存：chat_group_id=%s user_id=%s", chat_group_id, user_id)
        return
    try:
        res_json = _resource_history_response(resources)
        await ChatHistory.create(
            user_id=user_id,
            chat_group_id=chat_group_id,
            req=req,
            res=res_json,
        )
        logger.info("资源生成历史已保存 user_id=%s chat_group_id=%s resources=%d", user_id, chat_group_id, len(resources) if resources else 0)
    except Exception:
        logger.exception("保存资源生成历史失败 user_id=%s chat_group_id=%s", user_id, chat_group_id)


async def _make_state(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "single_choice, multi_choice, true_false", exam_count: int = 5, exam_difficulty: str = "medium", answers: dict | None = None, skip_review: bool = False, user_notes: str = "", ppt_prompt_key: str = "ppt", llm_priority: str = "high") -> dict:
    t0 = time.perf_counter()
    chat_group_id = await _ensure_chat_group_id(user_id, chat_group_id)
    t_init = time.perf_counter()

    # 没传 topic 但有 chat_group_id → 从聊天记录自动提取
    if not topic and chat_group_id > 0:
        topic = await _extract_topic_from_chat(user_id, chat_group_id)

    from backend.src.service.portrait_service import PortraitRadarService, build_learning_guidance

    portrait_context = "暂无画像数据"
    learning_guidance = ""

    # 并行：画像/用户查询 + 学习指导 + KB搜索 + Skills
    user_task = User.filter(id=user_id).first()
    guidance_task = build_learning_guidance(user_id)
    kb_task = kb_search(topic, top_k=3, user_id=user_id)
    skills_task = AgentSkill.filter(user_id=user_id, enabled=True).all()

    user, learning_guidance, kb_result, skills = await asyncio.gather(
        user_task, guidance_task, kb_task, skills_task, return_exceptions=True
    )
    t_gather = time.perf_counter()

    if isinstance(learning_guidance, Exception):
        logger.exception("学习指导生成失败 user_id=%s", user_id)
        learning_guidance = ""

    if isinstance(kb_result, Exception):
        logger.exception("知识库搜索失败 topic=%s", topic)
        kb_result = "暂无相关知识库资料"

    if isinstance(skills, Exception):
        logger.exception("Skills 查询失败 user_id=%s", user_id)
        skills = []

    # 基础画像：专业/年级（无需画像测评）
    base_portrait_parts = []
    if user and not isinstance(user, Exception):
        if user.major:
            base_portrait_parts.append(f"专业：{user.major}")
        if user.grade:
            base_portrait_parts.append(f"年级：{user.grade}")

    if user and not isinstance(user, Exception):
        picture = await user.picture
        if picture:
            try:
                radar_data = await PortraitRadarService.get(user_id)
            except Exception:
                radar_data = None
            portrait_context = "\n".join(format_portrait(picture, show_missing=False, radar_data=radar_data))
        elif base_portrait_parts:
            portrait_context = "【用户画像】\n" + "；".join(base_portrait_parts)
    elif base_portrait_parts:
        portrait_context = "【用户画像】\n" + "；".join(base_portrait_parts)
    t_portrait = time.perf_counter()

    kb_context = "暂无相关知识库资料"
    if kb_result and not isinstance(kb_result, Exception) and "暂无" not in str(kb_result):
        kb_context = kb_result

    custom_prompts = {}
    for s in skills:
        if s.resource_type in resource_types and s.system_prompt:
            custom_prompts[s.resource_type] = s.system_prompt

    t_total = time.perf_counter() - t0
    logger.info(
        "_make_state 耗时 total=%.2fs chat=%.2fs gather=%.2fs portrait=%.2fs topic=%s types=%s",
        t_total, t_init - t0, t_gather - t_init, t_portrait - t_gather, topic, resource_types,
    )

    return {
        "user_id": str(user_id),
        "topic": topic,
        "resource_types": resource_types,
        "chat_group_id": chat_group_id,
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
        "user_notes": user_notes,
        "ppt_prompt_key": ppt_prompt_key,
        "llm_priority": llm_priority,
    }


def build_cover_url(resource_type: str, file_url: str | None, resource_id: int) -> str | None:
    """根据资源类型和文件URL生成封面图URL"""
    if resource_type == "image" and file_url:
        return file_url
    return f"/static/covers/default_{resource_type}.svg"


async def _resource_to_dict(record: GeneratedResource, current_user_id: int | None = None, include_content: bool = False) -> dict:
    ext = _FILE_EXT_MAP.get(record.resource_type, "md")
    content = record.content
    preview = content[:200] if content else ""
    if record.resource_type == "mindmap" and content:
        try:
            preview = parse_mindmap_text(content)
            if include_content:
                content = _format_mindmap_content(content)
        except Exception:
            logger.exception("思维导图 JSON 转换失败 resource_id=%s", record.id)

    item = {
        "resource_id": record.id,
        "topic": record.topic,
        "title": record.topic,
        "resource_type": record.resource_type,
        "filename": f"{record.topic}_{record.resource_type}.{ext}",
        "file_type": ext,
        "preview": preview,
        "download_url": f"/resource/{record.id}/download",
        "review_passed": record.review_passed,
        "created_at": str(record.created_at),
        "updated_at": str(record.updated_at),
        "view_count": record.view_count,
        "download_count": record.download_count,
        "like_count": record.like_count,
        "favorite_count": record.favorite_count,
        "cover_url": record.cover_url,
        "visibility": record.visibility or "private",
        "owner_user_id": record.user_id,
        "is_owner": bool(current_user_id and record.user_id == current_user_id),
    }
    if include_content:
        item["content"] = content
        item["retry_count"] = record.retry_count
    if record.file_url:
        item["file_url"] = record.file_url
        item["url"] = record.file_url
        item["preview_url"] = record.file_url if record.resource_type in ("html", "video", "external_video") else ""

    if current_user_id:
        from backend.src.models.study_model import ResourceLike, ResourceCollection
        item["liked"] = await ResourceLike.filter(user_id=current_user_id, resource_id=record.id).exists()
        item["favorited"] = await ResourceCollection.filter(user_id=current_user_id, resource_id=record.id).exists()
    else:
        item["liked"] = False
        item["favorited"] = False
    return item


async def _save_resources(topic: str, user_id: int, generated: dict, review_passed: bool, retry_count: int,
                          file_urls: dict | None = None) -> list[dict]:
    """存库并返回记录列表（事务包裹，一条失败则全部回滚）"""
    from tortoise.transactions import in_transaction

    user = await User.filter(id=user_id).first()
    if not user:
        return []
    file_urls = file_urls or {}
    saved: list[dict] = []

    async with in_transaction():
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
                "visibility": record.visibility or "private",
            })
    return saved


class ResourceService:

    @staticmethod
    async def generate_and_save(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "", exam_count: int = 5, exam_difficulty: str = "medium", user_notes: str = "", ppt_prompt_key: str = "ppt", llm_priority: str = "high", skip_review: bool = False, bind_chat_history: bool = False) -> list[dict]:
        import time as _time
        _t_total = _time.perf_counter()
        chat_group_id = await _ensure_generation_chat_group_id(user_id, chat_group_id, bind_chat_history)

        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, exam_question_types, exam_count, exam_difficulty, user_notes=user_notes, ppt_prompt_key=ppt_prompt_key, llm_priority=llm_priority, skip_review=skip_review)
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
        if chat_group_id > 0:
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

        # 后台预生成旁白（播放时秒开）
        for item in saved:
            if item["resource_type"] in ("ppt", "document"):
                asyncio.ensure_future(_pre_generate_narration(item["resource_id"]))

        logger.info("[Resource] generate_and_save 完成 topic=%s types=%s 全程耗时=%.1fs",
                    topic, resource_types, _time.perf_counter() - _t_total)
        return saved

    @staticmethod
    async def generate_stream(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "single_choice, multi_choice, true_false", exam_count: int = 5, exam_difficulty: str = "medium", skip_review: bool = False, user_notes: str = "", ppt_prompt_key: str = "ppt", llm_priority: str = "high", bind_chat_history: bool = False, answers: dict | None = None):
        """astream(stream_mode=["values", "custom"]) — PPT 通过 custom 事件逐页推送，其他类型通过 values 事件推送"""
        import time as _time
        _t_total = _time.perf_counter()
        chat_group_id = await _ensure_generation_chat_group_id(user_id, chat_group_id, bind_chat_history)
        yield f"data: {json.dumps({'type': 'stream_progress', 'message': '资源生成已开始', 'chat_group_id': chat_group_id}, ensure_ascii=False)}\n\n"

        def _make_file_event(for_topic: str, rt: str, content: str, resource_id: int = 0, download_url: str = "") -> str:
            ext = _FILE_EXT_MAP.get(rt, "md")
            filename = f"{for_topic}_{rt}.{ext}"
            event_content = content
            if rt == "mindmap":
                try:
                    event_content = parse_mindmap_text(content)
                except Exception:
                    logger.exception("SSE 思维导图 JSON 转换失败")
            return f"data: {json.dumps({'type': 'file', 'file_type': rt, 'filename': filename, 'content': event_content, 'resource_id': resource_id, 'download_url': download_url}, ensure_ascii=False)}\n\n"

        user = await User.filter(id=user_id).first()

        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, exam_question_types, exam_count, exam_difficulty, answers=answers, skip_review=skip_review, user_notes=user_notes, ppt_prompt_key=ppt_prompt_key, llm_priority=llm_priority)
        topic = initial_state["topic"]

        final_passed = False
        final_retry = 0
        yielded_types: set[str] = set()
        saved_resources: list[dict] = []

        async for mode, chunk in resource_graph.astream(initial_state, stream_mode=["values", "custom"]):
            if mode == "custom":
                # PPT 逐页流式事件（stream_start / stream_slide），直接转发
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            elif mode == "values":
                resources = chunk.get("generated_resources", {})
                if resources:
                    for rt, content in resources.items():
                        if rt not in yielded_types and user:
                            record = await GeneratedResource.create(
                                topic=topic, resource_type=rt, content=content,
                                review_passed=False, retry_count=0,
                                file_url=chunk.get("file_urls", {}).get(rt),
                                user=user,
                            )
                            cover_url = build_cover_url(rt, record.file_url, record.id)
                            if cover_url:
                                await GeneratedResource.filter(id=record.id).update(cover_url=cover_url)
                            saved_resources.append({
                                "resource_id": record.id, "topic": topic,
                                "resource_type": rt, "content": content,
                                "review_passed": False, "retry_count": 0,
                                "visibility": record.visibility or "private",
                            })
                            logger.info("[SSE] 即时存库 %s id=%s topic=%s", rt, record.id, topic)
                            yielded_types.add(rt)
                            yield _make_file_event(topic, rt, content, resource_id=record.id, download_url=f"/resource/{record.id}/download")
                final_passed = chunk.get("review_passed", False)
                final_retry = chunk.get("retry_count", 0)

                yield f"data: {json.dumps({'resources': list(resources.keys()), 'review_passed': final_passed}, ensure_ascii=False)}\n\n"

        # 更新审核状态
        for r in saved_resources:
            await GeneratedResource.filter(id=r["resource_id"]).update(
                review_passed=final_passed, retry_count=final_retry,
            )
            r["review_passed"] = final_passed
            r["retry_count"] = final_retry
        if chat_group_id > 0:
            await _save_generation_to_history(user_id, chat_group_id, topic, saved_resources)

        # 后台预生成旁白（播放时秒开）
        for r in saved_resources:
            if r["resource_type"] in ("ppt", "document"):
                asyncio.ensure_future(_pre_generate_narration(r["resource_id"]))

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
                for r in saved_resources
            ],
        }
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        logger.info("[Resource] generate_stream 完成 topic=%s types=%s 全程耗时=%.1fs",
                    topic, resource_types, _time.perf_counter() - _t_total)
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
        record = await GeneratedResource.filter(Q(id=resource_id), Q(user_id=user_id) | Q(visibility="public")).first()
        if not record:
            return None
        # 原子递增查看计数
        await GeneratedResource.filter(id=resource_id).update(
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
            "visibility": record.visibility or "private",
            "owner_user_id": record.user_id,
            "is_owner": record.user_id == user_id,
        }
        if record.file_url:
            result["file_url"] = record.file_url
            result["url"] = record.file_url
            result["preview_url"] = record.file_url if record.resource_type in ("html", "video", "external_video") else ""

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
                    {
                        **s,
                        "index": i,
                        "title": s.get("title", ""),
                        "text": s.get("text", ""),
                        "notes": s.get("notes", ""),
                    }
                    for i, s in enumerate(slides_data)
                ]
            except Exception:
                logger.warning("PPT 幻灯片元数据解析失败 resource_id=%s", resource_id)

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
            logger.warning("旁白查询失败 resource_id=%s", resource_id)

        return result

    @staticmethod
    async def list_resources(user_id: int, visibility: str | None = None) -> list[dict]:
        if visibility == "public":
            records = await GeneratedResource.filter(visibility="public").order_by("-created_at").all()
        else:
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
                "visibility": r.visibility or "private",
                "owner_user_id": r.user_id,
                "is_owner": r.user_id == user_id,
            }
            if r.file_url:
                item["file_url"] = r.file_url
                item["url"] = r.file_url
                item["preview_url"] = r.file_url if r.resource_type in ("html", "video", "external_video") else ""
            # 附带当前用户的交互状态
            from backend.src.models.study_model import ResourceLike, ResourceCollection
            item["liked"] = await ResourceLike.filter(user_id=user_id, resource_id=r.id).exists()
            item["favorited"] = await ResourceCollection.filter(user_id=user_id, resource_id=r.id).exists()
            result.append(item)
        return result

    @staticmethod
    async def admin_list_resources(visibility: str | None = None, include_content: bool = False) -> list[dict]:
        query = GeneratedResource.all()
        if visibility:
            query = query.filter(visibility=visibility)
        records = await query.order_by("-updated_at", "-created_at").all()
        return [await _resource_to_dict(r, None, include_content=include_content) for r in records]

    @staticmethod
    async def admin_update_resource(resource_id: int, data: dict) -> dict | None:
        record = await GeneratedResource.filter(id=resource_id).first()
        if not record:
            return None

        title = data.get("title") or data.get("topic")
        resource_type = data.get("resource_type") or data.get("resourceType")
        content = data.get("content")
        visibility = data.get("visibility")
        cover_url = data.get("cover_url") or data.get("coverUrl")
        file_url = data.get("file_url") or data.get("fileUrl")

        update_fields = ["updated_at"]
        if title is not None:
            record.topic = str(title).strip() or record.topic
            update_fields.append("topic")
        if resource_type is not None:
            record.resource_type = str(resource_type).strip() or record.resource_type
            update_fields.append("resource_type")
        if content is not None:
            record.content = str(content)
            update_fields.append("content")
        if visibility is not None:
            value = str(visibility).strip()
            if value in ("public", "private", "pending", "rejected"):
                record.visibility = value
                update_fields.append("visibility")
        if cover_url is not None:
            record.cover_url = str(cover_url).strip() or None
            update_fields.append("cover_url")
        if file_url is not None:
            record.file_url = str(file_url).strip() or None
            update_fields.append("file_url")

        await record.save(update_fields=list(dict.fromkeys(update_fields)))
        return await _resource_to_dict(record, None, include_content=True)

    @staticmethod
    async def admin_delete_resource(resource_id: int) -> bool:
        record = await GeneratedResource.filter(id=resource_id).first()
        if not record:
            return False
        await record.delete()
        return True

    @staticmethod
    async def admin_approve_resource(resource_id: int) -> dict | None:
        return await ResourceService.admin_update_resource(resource_id, {"visibility": "public"})

    @staticmethod
    async def admin_reject_resource(resource_id: int) -> dict | None:
        return await ResourceService.admin_update_resource(resource_id, {"visibility": "rejected"})

    @staticmethod
    async def admin_import_base_resource(admin_id: int, data: dict) -> dict | None:
        user = await User.filter(id=admin_id).first()
        if not user:
            return None

        title = str(data.get("title") or data.get("topic") or "基础资源").strip()
        resource_type = str(data.get("resource_type") or data.get("resourceType") or "document").strip() or "document"
        content = str(data.get("content") or data.get("preview") or "").strip()
        file_url = str(data.get("file_url") or data.get("fileUrl") or "").strip() or None
        cover_url = str(data.get("cover_url") or data.get("coverUrl") or "").strip() or None

        if not content:
            content = f"{title}\n\n该资源由管理员导入。"

        record = await GeneratedResource.create(
            topic=title,
            resource_type=resource_type,
            content=content,
            review_passed=True,
            retry_count=0,
            visibility="public",
            file_url=file_url,
            cover_url=cover_url,
            user=user,
        )
        if not record.cover_url:
            cover = build_cover_url(resource_type, file_url, record.id)
            if cover:
                record.cover_url = cover
                await record.save(update_fields=["cover_url", "updated_at"])
        return await _resource_to_dict(record, admin_id, include_content=True)

    @staticmethod
    async def publish_resource(resource_id: int, user_id: int, visibility: str = "public") -> dict | None:
        if visibility not in ("public", "private", "pending", "rejected"):
            visibility = "private"
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return None
        record.visibility = visibility
        await record.save(update_fields=["visibility", "updated_at"])
        return await _resource_to_dict(record, user_id, include_content=True)

    @staticmethod
    async def download_resource(resource_id: int, user_id: int) -> tuple[bytes, str, str] | None:
        record = await GeneratedResource.filter(Q(id=resource_id), Q(user_id=user_id) | Q(visibility="public")).first()
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
    async def create_task(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, answers: dict | None = None, bind_chat_history: bool = False, skip_review: bool = False) -> dict:
        """创建生成任务（带 Redis 并发锁，防止重复提交）"""
        from backend.src.models.task_model import GenerationTask

        # Redis 并发锁：同一用户同一话题 30s 内不重复创建
        if topic and user_id:
            try:
                _lk = f"lock:task:{user_id}:{hashlib.md5(topic.strip().lower().encode()).hexdigest()}"
                r = await _get_redis()
                locked = await r.setnx(_lk, "1")
                if not locked:
                    # 锁被占用 → 查找是否已有正在运行的任务
                    existing = await GenerationTask.filter(
                        user_id=user_id, topic=topic.strip(),
                        status__in=["pending", "running"],
                    ).order_by("-created_at").first()
                    if existing:
                        return {"task_id": existing.task_id, "status": existing.status, "chat_group_id": existing.chat_group_id, "duplicated": True}
                else:
                    await r.expire(_lk, 30)
            except Exception:
                logger.debug("Redis 并发锁不可用，跳过（不阻塞任务创建）")

        chat_group_id = await _ensure_generation_chat_group_id(user_id, chat_group_id, bind_chat_history)
        tid = uuid.uuid4().hex
        task = await GenerationTask.create(
            task_id=tid,
            user_id=user_id,
            topic=topic or "",
            resource_types=json.dumps(resource_types, ensure_ascii=False),
            chat_group_id=chat_group_id,
            status="pending",
        )
        asyncio.ensure_future(_run_generation_task(task.id, tid, answers, skip_review=skip_review))
        return {"task_id": tid, "status": "pending", "chat_group_id": chat_group_id}

    @staticmethod
    async def get_task(task_id: str, user_id: int) -> dict | None:
        """查询任务状态（Redis 缓存仅信任终态，running 状态直查 MySQL）"""
        _redis_cache_key = f"task:{task_id}:state"
        # 1) 尝试 Redis 缓存（仅终态可信任，running 状态可能过期）
        try:
            r = await _get_redis()
            cached = await r.get(_redis_cache_key)
            if cached:
                state = json.loads(cached)
                if state.get("user_id") == user_id and state.get("status") in ("success", "failed"):
                    return state
        except Exception:
            logger.debug("Task 缓存读取失败 task_id=%s，回退 MySQL", task_id)

        # 2) 回退 MySQL
        from backend.src.models.task_model import GenerationTask

        task = await GenerationTask.filter(task_id=task_id, user_id=user_id).first()
        if not task:
            return None
        state = {
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
            "user_id": user_id,
        }
        # 3) 回填缓存
        asyncio.ensure_future(_cache_task_state(task_id, state))
        return state

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
                "chat_group_id": t.chat_group_id,
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

async def _run_generation_task(db_id: int, task_id: str, answers: dict | None = None, skip_review: bool = False):
    """后台运行资源生成任务，更新 DB 进度并推送 SSE"""
    import time as _time
    _t_total = _time.perf_counter()
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
        _t_init = _time.perf_counter()
        await _notify_task_sse(task_id, {"type": "status", "status": "running", "progress": 5, "progress_msg": "正在初始化…"})
        asyncio.ensure_future(_cache_task_state(task_id, {"task_id": task_id, "status": "running", "progress": 5, "progress_msg": "正在初始化…", "user_id": user_id}))

        # 提前搜索外部视频（仅用户请求了视频资源时才搜索，避免思维导图等也弹出）
        if topic and len(topic) > 1 and "video" in resource_types:
            asyncio.ensure_future(_search_external_videos_early(
                task_id, topic, user_id, chat_group_id,
            ))

        # 构建 graph 初始状态
        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, answers=answers, ppt_prompt_key="ppt", skip_review=skip_review)
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
        _t_per_type: dict[str, float] = {}
        _t_stream_start = _time.perf_counter()

        task.progress = 10
        task.progress_msg = "AI 规划中…"
        await task.save()
        await _notify_task_sse(task_id, {"type": "status", "status": "running", "progress": 10, "progress_msg": "AI 规划中…", "elapsed_ms": int((_time.perf_counter() - _t_init) * 1000)})
        asyncio.ensure_future(_cache_task_state(task_id, {"task_id": task_id, "status": "running", "progress": 10, "progress_msg": "AI 规划中…", "user_id": user_id}))

        _custom_count = 0
        async for mode, chunk in resource_graph.astream(initial_state, stream_mode=["values", "custom"]):
            if mode == "custom":
                _custom_count += 1
                if _custom_count <= 3 or chunk.get("type") in ("stream_slide", "stream_section_replace", "stream_start"):
                    logger.info("[TaskStream] custom event #%d mode=%s type=%s keys=%s",
                                _custom_count, mode, chunk.get("type", "?"), list(chunk.keys())[:5])
                await _notify_task_sse(task_id, chunk)
                continue

            resources = chunk.get("generated_resources", {})
            if resources:
                final_resources = resources
                for rt in resources.keys():
                    if rt not in yielded_types:
                        yielded_types.add(rt)
                        done = len(yielded_types)
                        pct = 20 + int((done / max(total_types, 1)) * 40)
                        rt_elapsed = int((_time.perf_counter() - _t_stream_start) * 1000)
                        _t_per_type[rt] = _time.perf_counter()
                        task.progress = min(pct, 85)
                        task.progress_msg = f"「{rt}」生成完毕，耗时 {rt_elapsed / 1000:.1f}s"
                        await task.save()
                        await _notify_task_sse(task_id, {
                            "type": "progress",
                            "resource_type": rt,
                            "progress": task.progress,
                            "progress_msg": task.progress_msg,
                            "elapsed_ms": rt_elapsed,
                        })
                        asyncio.ensure_future(_cache_task_state(task_id, {"task_id": task_id, "status": "running", "progress": task.progress, "progress_msg": task.progress_msg, "user_id": user_id}))

            chunk_file_urls = chunk.get("file_urls", {})
            if chunk_file_urls:
                final_file_urls.update(chunk_file_urls)
            final_passed = chunk.get("review_passed", False)
            final_retry = chunk.get("retry_count", 0)

        # 审核阶段
        _t_review = _time.perf_counter()
        task.progress = 70
        task.progress_msg = "AI 审核中…"
        await task.save()
        await _notify_task_sse(task_id, {"type": "status", "progress": 70, "progress_msg": "AI 审核中…"})
        asyncio.ensure_future(_cache_task_state(task_id, {"task_id": task_id, "status": "running", "progress": 70, "progress_msg": "AI 审核中…", "user_id": user_id}))

        # 保存到 DB
        task.progress = 85
        task.progress_msg = "正在保存…"
        await task.save()
        await _notify_task_sse(task_id, {"type": "status", "progress": 85, "progress_msg": "正在保存…"})
        asyncio.ensure_future(_cache_task_state(task_id, {"task_id": task_id, "status": "running", "progress": 85, "progress_msg": "正在保存…", "user_id": user_id}))

        saved = await _save_resources(topic, user_id, final_resources, final_passed, final_retry,
                                      file_urls=final_file_urls)

        # 后台预生成旁白音频（PPT/文档等文字类资源），播放时秒开
        for r in saved:
            if r["resource_type"] in ("ppt", "document"):
                asyncio.ensure_future(_pre_generate_narration(r["resource_id"]))

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

        logger.info("[Task] 后台任务完成 task_id=%s topic=%s types=%s 全程耗时=%.1fs",
                    task_id, topic, resource_types, _time.perf_counter() - _t_total)

        task.status = "success"
        task.progress = 100
        task.progress_msg = "生成完成"
        task.result = json.dumps(result_data, ensure_ascii=False)
        await task.save()

        # 生成标题
        type_labels = {"document": "文献", "exercise": "习题", "mindmap": "思维导图", "ppt": "PPT", "image": "图片"}
        type_names = [type_labels.get(r["resource_type"], r["resource_type"]) for r in saved]
        gen_title = await _generate_resource_title(task.topic, type_names)

        total_ms = int((_time.perf_counter() - _t_total) * 1000)
        await _notify_task_sse(task_id, {
            "type": "done",
            "status": "success",
            "progress": 100,
            "title": gen_title,
            "result": result_data,
            "elapsed_ms": total_ms,
            "progress_msg": f"全部生成完毕，总耗时 {total_ms / 1000:.1f}s",
        })
        await _notify_task_sse(task_id, {"type": "__close__"})
        asyncio.ensure_future(_cache_task_state(task_id, {"task_id": task_id, "status": "success", "progress": 100, "progress_msg": "生成完成", "result": json.dumps(result_data), "user_id": user_id}))

        await Notification.create(
            type="resource",
            title=gen_title,
            content=f"「{task.topic}」的{'、'.join(type_names)}已生成，共 {len(saved)} 份",
            target_url="/resource",
            target_user_id=user_id,
        )


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
                asyncio.ensure_future(_cache_task_state(task_id, {"task_id": task_id, "status": "failed", "error": str(e)[:200], "user_id": task.user_id}))
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
    """后台预生成旁白音频，后续视频构建时可复用缓存"""
    try:
        from backend.src.service.narration_service import narrate_resource
        await narrate_resource(resource_id, voice)
    except Exception:
        logger.exception("预生成旁白音频失败 resource_id=%s", resource_id)


async def _search_external_videos_early(task_id: str, topic: str, user_id: int, chat_group_id: int = 0):
    """在资源生成任务启动时并行搜索外部教学视频（B站），通过 SSE 实时推送给前端。

    本函数与主 graph 并发执行，搜索结果会先于自生成资源到达前端。
    """
    try:
        from backend.src.service.video_service import ExternalVideoService, _format_duration, _format_view_count
        videos = await ExternalVideoService.search(topic, max_results=2)
        if not videos:
            logger.info("[外部视频] 未搜索到「%s」的相关视频", topic)
            return

        logger.info("[外部视频] 搜索到 %d 个「%s」的相关视频", len(videos), topic)
        saved = []
        for v in videos:
            record = await GeneratedResource.create(
                topic=topic,
                resource_type="external_video",
                content=json.dumps(v, ensure_ascii=False),
                file_url=v.get("page_url", v.get("embed_url", "")),
                cover_url=v.get("cover_url"),
                review_passed=True,
                retry_count=0,
                user_id=user_id,
            )
            saved.append({
                "resource_id": record.id,
                "topic": record.topic,
                "resource_type": "external_video",
                "file_type": "external_video",
                "filename": f"推荐视频: {(v.get('title') or '')[:40]}",
                "file_url": record.file_url,
                "cover_url": v.get("cover_url", ""),
                "embed_url": v.get("embed_url", ""),
                "title": v.get("title", ""),
                "author": v.get("author", ""),
                "duration": v.get("duration"),
                "duration_text": _format_duration(v.get("duration")) if v.get("duration") else "",
                "view_count": v.get("view_count", 0),
                "view_count_text": _format_view_count(v.get("view_count")),
                "description": v.get("description", ""),
                "source": v.get("source_label", ""),
                "source_label": v.get("source_label", ""),
                "preview_url": v.get("embed_url", ""),
            })

        # 写入聊天历史（刷新页面后仍可见）
        if not chat_group_id or chat_group_id <= 0:
            from backend.src.utils.chat_utils import allocate_chat_group_id
            chat_group_id = await allocate_chat_group_id(user_id)
        await _save_generation_to_history(user_id, chat_group_id, topic, saved)

        await _notify_task_sse(task_id, {
            "type": "external_videos",
            "external_videos": saved,
            "progress_msg": f"已找到相关教学视频",
        })
        logger.info("[外部视频] 已推送 %d 个视频到 task_id=%s", len(saved), task_id)

    except ImportError:
        logger.debug("[外部视频] video_service 未就绪，跳过")
    except Exception:
        logger.info("[外部视频] 搜索失败（非关键错误，继续主流程）", exc_info=True)
