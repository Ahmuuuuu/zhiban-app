import json

from backend.src.ai_core.graph import resource_graph, _fill
from backend.src.ai_core.llm_config import llm
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.agent_skill_model import AgentSkill
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User
from backend.src.utils.database import init_db

# 资源类型 → 文件扩展名映射
_FILE_EXT_MAP = {
    "document": "md",
    "ppt": "pptx",
    "mindmap": "md",
    "exercise": "md",
    "case": "md",
    "reading": "md",
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
    prompt = _fill(load_prompt("resource/topic_extract"), conversation=conversation)
    response = await llm.ainvoke(prompt)
    return response.content.strip()


async def _make_state(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0) -> dict:
    await init_db()

    # 没传 topic 但有 chat_group_id → 从聊天记录自动提取
    if not topic and chat_group_id > 0:
        topic = await _extract_topic_from_chat(user_id, chat_group_id)

    portrait_context = "暂无画像数据"
    user = await User.filter(id=user_id).first()
    if user:
        picture = await user.picture
        if picture:
            portrait_context = "\n".join(format_portrait(picture, show_missing=False))

    kb_context = "暂无相关知识库资料"
    try:
        kb_result = await kb_search(topic, top_k=5, user_id=user_id)
        if kb_result and "暂无" not in kb_result:
            kb_context = kb_result
    except Exception:
        pass

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
    async def generate_and_save(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0) -> list[dict]:
        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id)
        topic = initial_state["topic"]
        result = await resource_graph.ainvoke(initial_state)
        return await _save_resources(
            topic, user_id,
            result.get("generated_resources", {}),
            result.get("review_passed", False),
            result.get("retry_count", 0),
        )

    @staticmethod
    async def generate_stream(topic: str, user_id: int, resource_types: list[str], chat_group_id: int = 0):
        """节点级流式 — astream 逐节点产出状态，只跑一次 graph，同时推送文件事件"""
        initial_state = await _make_state(topic, user_id, resource_types, chat_group_id)
        topic = initial_state["topic"]
        final_resources = {}
        final_passed = False
        final_retry = 0
        yielded_types: set[str] = set()

        def _file_event(rt: str, content: str) -> str:
            ext = _FILE_EXT_MAP.get(rt, "md")
            filename = f"{topic}_{rt}.{ext}"
            return f"data: {json.dumps({'type': 'file', 'file_type': rt, 'filename': filename, 'content': content}, ensure_ascii=False)}\n\n"

        async for chunk in resource_graph.astream(initial_state, stream_mode="values"):
            resources = chunk.get("generated_resources", {})
            if resources:
                final_resources = resources
                # 有新产出的资源类型 → 推送文件事件
                for rt, content in resources.items():
                    if rt not in yielded_types:
                        yielded_types.add(rt)
                        yield _file_event(rt, content)
            final_passed = chunk.get("review_passed", False)
            final_retry = chunk.get("retry_count", 0)

            yield f"data: {json.dumps({'resources': list(resources.keys()), 'review_passed': final_passed}, ensure_ascii=False)}\n\n"

        # 流式结束后存库
        saved = await _save_resources(topic, user_id, final_resources, final_passed, final_retry)
        # 在 done 事件中附带 download_url
        done_data = {
            "done": True,
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
        return {
            "resource_id": record.id,
            "topic": record.topic,
            "resource_type": record.resource_type,
            "content": record.content,
            "review_passed": record.review_passed,
            "retry_count": record.retry_count,
            "created_at": str(record.created_at),
        }

    @staticmethod
    async def list_resources(user_id: int) -> list[dict]:
        records = await GeneratedResource.filter(user_id=user_id).order_by("-created_at").all()
        return [
            {
                "resource_id": r.id,
                "topic": r.topic,
                "resource_type": r.resource_type,
                "review_passed": r.review_passed,
                "created_at": str(r.created_at),
            }
            for r in records
        ]

    @staticmethod
    async def download_resource(resource_id: int, user_id: int) -> tuple[bytes, str, str] | None:
        record = await GeneratedResource.filter(id=resource_id, user_id=user_id).first()
        if not record:
            return None
        ext = _FILE_EXT_MAP.get(record.resource_type, "md")
        filename = f"{record.topic}_{record.resource_type}.{ext}"
        if record.resource_type == "ppt":
            from backend.src.utils.pptx_generator import markdown_to_pptx
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
