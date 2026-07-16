import asyncio
import json
import logging

logger = logging.getLogger(__name__)

from backend.src.ai_core.resource_graph import resource_graph
from backend.src.service.resource.task_runtime import (
    cache_task_state as _runtime_cache_task_state,
    notify_task_sse as _runtime_notify_task_sse,
    replay_sse,
    subscribe_task_sse as _runtime_subscribe_task_sse,
    unsubscribe_task_sse as _runtime_unsubscribe_task_sse,
)
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.usermodel import User
from backend.src.models.notification_model import Notification

from backend.src.utils.json_parser import parse_llm_json
from backend.src.utils.mindmap import parse_mindmap_text
from backend.src.service.resource.metadata import (
    FILE_EXT_MAP as _FILE_EXT_MAP,
    apply_ppt_theme_to_content as _apply_ppt_theme_to_content,
    build_cover_url,
    extract_ppt_theme_id as _extract_ppt_theme_id,
    format_mindmap_content as _format_mindmap_content,
    normalize_ppt_theme_id as _normalize_ppt_theme_id,
)
from backend.src.service.resource.generation_context import (
    ensure_chat_group_id as _ensure_chat_group_id,
    ensure_generation_chat_group_id as _ensure_generation_chat_group_id,
    make_generation_state as _make_state,
)
from backend.src.service.resource.history import save_generation_to_history as _save_generation_to_history
from backend.src.service.resource.library import ResourceLibraryService
from backend.src.service.resource.persistence import (
    clean_generation_topic as _clean_generation_topic,
    save_resources as _save_resources,
)
from backend.src.service.resource.tasks import ResourceTaskService


async def _generate_resource_title(topic: str, type_names: list[str]) -> str:
    """为生成的学习资源起一个标题"""
    types_str = "、".join(type_names)
    return f"「{topic}」{types_str}"


async def _save_single_generated_resource(
    topic: str,
    user: User | None,
    resource_type: str,
    content: str,
    *,
    file_url: str | None = None,
    review_passed: bool = False,
    retry_count: int = 0,
    ppt_theme_id: str | None = None,
) -> dict | None:
    if not user or not resource_type or content is None:
        return None
    topic = _clean_generation_topic(topic)

    item_content = (
        _apply_ppt_theme_to_content(content, ppt_theme_id)
        if resource_type == "ppt"
        else content
    )
    record = await GeneratedResource.create(
        topic=topic,
        resource_type=resource_type,
        content=item_content,
        review_passed=review_passed,
        retry_count=retry_count,
        file_url=file_url,
        user=user,
    )
    cover_url = build_cover_url(resource_type, file_url, record.id)
    if cover_url:
        await GeneratedResource.filter(id=record.id).update(cover_url=cover_url)

    saved = {
        "resource_id": record.id,
        "topic": record.topic,
        "resource_type": record.resource_type,
        "content": record.content,
        "review_passed": record.review_passed,
        "retry_count": record.retry_count,
        "file_url": record.file_url,
        "cover_url": cover_url,
        "visibility": record.visibility or "private",
    }
    if resource_type == "ppt":
        saved["ppt_theme_id"] = _extract_ppt_theme_id(record.content)
    logger.info("[Resource] 提前入库 %s id=%s topic=%s", resource_type, record.id, topic)
    return saved


# ─── 任务 SSE 通知队列（基于 Redis Pub/Sub + Stream，兼容多进程）───
# 使用 redis_client 的统一 SSE 机制：本地进程走内存队列，跨进程走 Redis


def _resource_preview_content(resource_type: str, content):
    if resource_type != "mindmap" or content in (None, ""):
        return content
    try:
        return parse_mindmap_text(content)
    except Exception:
        logger.exception("SSE mindmap preview content parse failed")
        return content


def _subscribe_task_sse(task_id: str):
    """为生成任务 SSE 客户端创建消息队列"""
    return _runtime_subscribe_task_sse(task_id)


def _unsubscribe_task_sse(task_id: str, q: list):
    """取消 SSE 订阅"""
    _runtime_unsubscribe_task_sse(task_id, q)


async def _notify_task_sse(task_id: str, data: dict):
    """通知所有 SSE 客户端（本地内存 + Redis Pub/Sub + Stream）"""
    await _runtime_notify_task_sse(task_id, data)


# ─── Task 状态 Redis 缓存 ───
# key: task:{task_id}:state → JSON, TTL: 30s（生成中）/ 300s（已完成）


async def _cache_task_state(task_id: str, state: dict):
    await _runtime_cache_task_state(task_id, state)


class ResourceService:

    @staticmethod
    async def generate_and_save(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "", exam_count: int = 5, exam_difficulty: str = "medium", user_notes: str = "", ppt_prompt_key: str = "ppt", llm_priority: str = "high", skip_review: bool = False, bind_chat_history: bool = False, ppt_theme_id: str | None = None, include_request_in_history: bool = True, save_to_chat_history: bool = True) -> list[dict]:
        import time as _time
        _t_total = _time.perf_counter()
        chat_group_id = await _ensure_generation_chat_group_id(user_id, chat_group_id, bind_chat_history)

        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, exam_question_types, exam_count, exam_difficulty, user_notes=user_notes, ppt_prompt_key=ppt_prompt_key, llm_priority=llm_priority, skip_review=skip_review, ppt_theme_id=ppt_theme_id)
        topic = initial_state["topic"]

        result = await resource_graph.ainvoke(initial_state)
        generated = result.get("generated_resources", {})
        saved = await _save_resources(
            topic, user_id,
            generated,
            result.get("review_passed", False),
            result.get("retry_count", 0),
            file_urls=result.get("file_urls"),
            ppt_theme_id=ppt_theme_id,
        )
        if save_to_chat_history and chat_group_id > 0:
            await _save_generation_to_history(user_id, chat_group_id, topic, saved, include_request=include_request_in_history)

        # exercise 类型：解析 graph 输出的 JSON 题目 → 按 reviewer 逐题审核过滤 → 存 ExamQuestion 表
        reviewer_questions = result.get("reviewer_questions", [])
        question_quality = {q.get("index"): q.get("passed", True) for q in reviewer_questions} if reviewer_questions else {}

        for i, item in enumerate(saved):
            if item["resource_type"] == "exercise":
                try:
                    from backend.src.service.exam.service import ExamService  # deferred: circular exam<->resource

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
        logger.info("[Resource] generate_and_save 完成 topic=%s types=%s 全程耗时=%.1fs",
                    topic, resource_types, _time.perf_counter() - _t_total)
        return saved

    @staticmethod
    async def generate_stream(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, exam_question_types: str = "single_choice, multi_choice, true_false", exam_count: int = 5, exam_difficulty: str = "medium", skip_review: bool = False, user_notes: str = "", ppt_prompt_key: str = "ppt", llm_priority: str = "high", bind_chat_history: bool = False, answers: dict | None = None, ppt_theme_id: str | None = None, include_request_in_history: bool = True, save_to_chat_history: bool = True):
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
            payload = {'type': 'file', 'file_type': rt, 'filename': filename, 'content': event_content, 'resource_id': resource_id, 'download_url': download_url}
            if rt == "ppt":
                payload["ppt_theme_id"] = _extract_ppt_theme_id(content) or _normalize_ppt_theme_id(ppt_theme_id)
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        user = await User.filter(id=user_id).first()

        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, exam_question_types, exam_count, exam_difficulty, answers=answers, skip_review=skip_review, user_notes=user_notes, ppt_prompt_key=ppt_prompt_key, llm_priority=llm_priority, ppt_theme_id=ppt_theme_id)
        topic = initial_state["topic"]

        final_passed = False
        final_retry = 0
        yielded_types: set[str] = set()
        saved_types: set[str] = set()
        saved_resources: list[dict] = []

        async for mode, chunk in resource_graph.astream(initial_state, stream_mode=["values", "custom"]):
            if mode == "custom":
                if chunk.get("type") == "resource_complete":
                    rt = str(chunk.get("resource_type") or chunk.get("file_type") or "").strip()
                    content = chunk.get("content")
                    if rt and rt not in saved_types and user and content is not None:
                        item_content = _apply_ppt_theme_to_content(content, ppt_theme_id) if rt == "ppt" else content
                        saved = await _save_single_generated_resource(
                            topic,
                            user,
                            rt,
                            item_content,
                            file_url=chunk.get("file_url") or None,
                            review_passed=False,
                            retry_count=0,
                            ppt_theme_id=ppt_theme_id,
                        )
                        if saved:
                            saved_resources.append(saved)
                            saved_types.add(rt)
                            yielded_types.add(rt)
                            yield _make_file_event(topic, rt, item_content, resource_id=saved["resource_id"], download_url=f"/resource/{saved['resource_id']}/download")
                    continue
                # PPT 逐页流式事件（stream_start / stream_slide），直接转发
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            elif mode == "values":
                resources = chunk.get("generated_resources", {})
                if resources:
                    for rt, content in resources.items():
                        if rt not in saved_types and rt not in yielded_types and user:
                            item_content = _apply_ppt_theme_to_content(content, ppt_theme_id) if rt == "ppt" else content
                            record = await GeneratedResource.create(
                                topic=topic, resource_type=rt, content=item_content,
                                review_passed=False, retry_count=0,
                                file_url=chunk.get("file_urls", {}).get(rt),
                                user=user,
                            )
                            cover_url = build_cover_url(rt, record.file_url, record.id)
                            if cover_url:
                                await GeneratedResource.filter(id=record.id).update(cover_url=cover_url)
                            saved_resources.append({
                                "resource_id": record.id, "topic": topic,
                                "resource_type": rt, "content": item_content,
                                "review_passed": False, "retry_count": 0,
                                "visibility": record.visibility or "private",
                            })
                            if rt == "ppt":
                                saved_resources[-1]["ppt_theme_id"] = _extract_ppt_theme_id(item_content)
                            logger.info("[SSE] 即时存库 %s id=%s topic=%s", rt, record.id, topic)
                            saved_types.add(rt)
                            yielded_types.add(rt)
                            yield _make_file_event(topic, rt, item_content, resource_id=record.id, download_url=f"/resource/{record.id}/download")
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
        if save_to_chat_history and chat_group_id > 0:
            await _save_generation_to_history(user_id, chat_group_id, topic, saved_resources, include_request=include_request_in_history)

        # 后台预生成旁白（播放时秒开）
        done_data = {
            "done": True,
            "chat_group_id": chat_group_id,
            "resources": [
                {
                    "resource_id": r["resource_id"],
                    "file_type": r["resource_type"],
                    "topic": r["topic"],
                    "content": r.get("content", ""),
                    "download_url": f"/resource/{r['resource_id']}/download",
                    **({"ppt_theme_id": r.get("ppt_theme_id")} if r["resource_type"] == "ppt" else {}),
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
        return await ResourceLibraryService.toggle_like(resource_id, user_id)

    @staticmethod
    async def toggle_favorite(resource_id: int, user_id: int) -> dict:
        return await ResourceLibraryService.toggle_favorite(resource_id, user_id)

    @staticmethod
    async def get_resource(resource_id: int, user_id: int) -> dict | None:
        return await ResourceLibraryService.get_resource(resource_id, user_id)

    @staticmethod
    async def list_resources(user_id: int, visibility: str | None = None) -> list[dict]:
        return await ResourceLibraryService.list_resources(user_id, visibility)

    @staticmethod
    async def admin_list_resources(visibility: str | None = None, include_content: bool = False) -> list[dict]:
        return await ResourceLibraryService.admin_list_resources(visibility, include_content)

    @staticmethod
    async def admin_update_resource(resource_id: int, data: dict) -> dict | None:
        return await ResourceLibraryService.admin_update_resource(resource_id, data)

    @staticmethod
    async def admin_delete_resource(resource_id: int) -> bool:
        return await ResourceLibraryService.admin_delete_resource(resource_id)

    @staticmethod
    async def admin_approve_resource(resource_id: int) -> dict | None:
        return await ResourceLibraryService.admin_approve_resource(resource_id)

    @staticmethod
    async def admin_reject_resource(resource_id: int) -> dict | None:
        return await ResourceLibraryService.admin_reject_resource(resource_id)

    @staticmethod
    async def admin_import_base_resource(admin_id: int, data: dict) -> dict | None:
        return await ResourceLibraryService.admin_import_base_resource(admin_id, data)

    @staticmethod
    async def publish_resource(resource_id: int, user_id: int, visibility: str = "public") -> dict | None:
        return await ResourceLibraryService.publish_resource(resource_id, user_id, visibility)

    @staticmethod
    async def download_resource(resource_id: int, user_id: int) -> tuple[bytes, str, str] | None:
        return await ResourceLibraryService.download_resource(resource_id, user_id)

    @staticmethod
    async def delete_resource(resource_id: int, user_id: int) -> bool:
        return await ResourceLibraryService.delete_resource(resource_id, user_id)

    # Task management
    @staticmethod
    async def create_task(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0, answers: dict | None = None, bind_chat_history: bool = False, skip_review: bool = False, ppt_theme_id: str | None = None, save_to_chat_history: bool = True) -> dict:
        return await ResourceTaskService.create_task(
            topic,
            user_id,
            resource_types,
            chat_group_id,
            answers,
            bind_chat_history,
            skip_review,
            ppt_theme_id,
            save_to_chat_history,
            ensure_chat_group_id=_ensure_generation_chat_group_id,
            run_task=_run_generation_task,
        )

    @staticmethod
    async def get_task(task_id: str, user_id: int) -> dict | None:
        return await ResourceTaskService.get_task(task_id, user_id)

    @staticmethod
    async def list_tasks(user_id: int) -> list[dict]:
        return await ResourceTaskService.list_tasks(user_id)

    @staticmethod
    async def init_tasks():
        await ResourceTaskService.init_tasks()


# ═══════════════════════════════════════════════
#  后台任务执行
# ═══════════════════════════════════════════════

async def _run_generation_task(db_id: int, task_id: str, answers: dict | None = None, skip_review: bool = False, ppt_theme_id: str | None = None, save_to_chat_history: bool = True):
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
        if save_to_chat_history and topic and len(topic) > 1 and "video" in resource_types:
            asyncio.ensure_future(_search_external_videos_early(
                task_id, topic, user_id, chat_group_id,
            ))

        # 构建 graph 初始状态
        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id, answers=answers, ppt_prompt_key="ppt", skip_review=skip_review, ppt_theme_id=ppt_theme_id)
        topic = initial_state["topic"]

        # 更新 topic（可能从聊天记录提取）
        if topic != task.topic:
            task.topic = topic
            await task.save()

        user = await User.filter(id=user_id).first()
        final_resources: dict = {}
        final_passed = False
        final_retry = 0
        final_file_urls: dict = {}
        yielded_types: set[str] = set()
        saved_types: set[str] = set()
        saved_resources: list[dict] = []
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
                if chunk.get("type") == "resource_complete":
                    rt = str(chunk.get("resource_type") or chunk.get("file_type") or "").strip()
                    content = chunk.get("content")
                    if rt and rt not in saved_types and user and content is not None:
                        saved = await _save_single_generated_resource(
                            topic,
                            user,
                            rt,
                            content,
                            file_url=chunk.get("file_url") or None,
                            review_passed=False,
                            retry_count=0,
                            ppt_theme_id=ppt_theme_id,
                        )
                        if saved:
                            saved_resources.append(saved)
                            saved_types.add(rt)
                            yielded_types.add(rt)
                            ext = _FILE_EXT_MAP.get(rt, "md")
                            done = len(yielded_types)
                            pct = 20 + int((done / max(total_types, 1)) * 40)
                            rt_elapsed = int((_time.perf_counter() - _t_stream_start) * 1000)
                            task.progress = min(pct, 85)
                            task.progress_msg = f"「{rt}」已生成并保存，耗时 {rt_elapsed / 1000:.1f}s"
                            await task.save()
                            await _notify_task_sse(task_id, {
                                "type": "file",
                                "file_type": rt,
                                "resource_type": rt,
                                "filename": f"{topic}_{rt}.{ext}",
                                "resource_id": saved["resource_id"],
                                "download_url": f"/resource/{saved['resource_id']}/download",
                                "topic": topic,
                                "content": _resource_preview_content(rt, saved.get("content")),
                                **({"ppt_theme_id": saved.get("ppt_theme_id")} if rt == "ppt" else {}),
                            })
                            await _notify_task_sse(task_id, {
                                "type": "progress",
                                "resource_type": rt,
                                "progress": task.progress,
                                "progress_msg": task.progress_msg,
                                "elapsed_ms": rt_elapsed,
                            })
                            asyncio.ensure_future(_cache_task_state(task_id, {
                                "task_id": task_id,
                                "status": "running",
                                "progress": task.progress,
                                "progress_msg": task.progress_msg,
                                "user_id": user_id,
                            }))
                    continue
                if _custom_count <= 3 or chunk.get("type") in ("stream_slide", "stream_section_replace", "stream_start"):
                    logger.info("[TaskStream] custom event #%d mode=%s type=%s keys=%s",
                                _custom_count, mode, chunk.get("type", "?"), list(chunk.keys())[:5])
                await _notify_task_sse(task_id, chunk)
                continue

            resources = chunk.get("generated_resources", {})
            if resources:
                final_resources = resources
                for rt in resources.keys():
                    if rt not in saved_types and rt not in yielded_types:
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
        await _notify_task_sse(task_id, {
            "type": "agent_event",
            "agent_id": "saver",
            "agent_name": "ResourceService",
            "phase": "saver",
            "status": "saving",
            "message": "正在保存生成资源",
        })
        await _notify_task_sse(task_id, {"type": "status", "progress": 85, "progress_msg": "正在保存…"})
        asyncio.ensure_future(_cache_task_state(task_id, {"task_id": task_id, "status": "running", "progress": 85, "progress_msg": "正在保存…", "user_id": user_id}))

        remaining_resources = {
            rt: content
            for rt, content in final_resources.items()
            if rt not in saved_types
        }
        saved = list(saved_resources)
        if remaining_resources:
            saved.extend(await _save_resources(
                topic,
                user_id,
                remaining_resources,
                final_passed,
                final_retry,
                file_urls=final_file_urls,
                ppt_theme_id=ppt_theme_id,
            ))

        for item in saved:
            await GeneratedResource.filter(id=item["resource_id"]).update(
                review_passed=final_passed,
                retry_count=final_retry,
            )
            item["review_passed"] = final_passed
            item["retry_count"] = final_retry

        # 后台预生成旁白音频（PPT/文档等文字类资源），播放时秒开
        # 保存到聊天历史
        if save_to_chat_history and chat_group_id > 0:
            await _save_generation_to_history(user_id, chat_group_id, topic, saved)

        # 记录结果
        result_data = [
            {
                "resource_id": r["resource_id"],
                "file_type": r["resource_type"],
                "topic": r["topic"],
                "download_url": f"/resource/{r['resource_id']}/download",
                **({"content": _resource_preview_content(r["resource_type"], r.get("content"))} if r["resource_type"] == "mindmap" else {}),
                **({"ppt_theme_id": r.get("ppt_theme_id")} if r["resource_type"] == "ppt" else {}),
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
        await _notify_task_sse(task_id, {
            "type": "agent_event",
            "agent_id": "saver",
            "agent_name": "ResourceService",
            "phase": "saver",
            "status": "done",
            "message": f"已保存 {len(saved)} 个资源",
            "total": len(saved),
        })

        # 生成标题
        type_labels = {"document": "文献", "exercise": "习题", "mindmap": "思维导图", "ppt": "PPT", "image": "图片"}
        type_names = [type_labels.get(r["resource_type"], r["resource_type"]) for r in saved]
        gen_title = await _generate_resource_title(task.topic, type_names)

        total_ms = int((_time.perf_counter() - _t_total) * 1000)
        await _notify_task_sse(task_id, {
            "type": "agent_event",
            "agent_id": "complete",
            "agent_name": "完成",
            "phase": "complete",
            "status": "done",
            "message": f"全部生成完毕，总耗时 {total_ms / 1000:.1f}s",
            "elapsed_ms": total_ms,
        })
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
                    "type": "agent_event",
                    "agent_id": "complete",
                    "agent_name": "生成失败",
                    "phase": "complete",
                    "status": "failed",
                    "message": str(e)[:160],
                })
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
    return
    """后台预生成旁白音频，后续视频构建时可复用缓存"""
    try:
        from backend.src.service.narration.service import narrate_resource
        await narrate_resource(resource_id, voice)
    except Exception:
        logger.exception("预生成旁白音频失败 resource_id=%s", resource_id)


async def _search_external_videos_early(task_id: str, topic: str, user_id: int, chat_group_id: int = 0):
    """在资源生成任务启动时并行搜索外部教学视频（B站），通过 SSE 实时推送给前端。

    本函数与主 graph 并发执行，搜索结果会先于自生成资源到达前端。
    """
    try:
        from backend.src.service.video.service import ExternalVideoService, _format_duration, _format_view_count
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
