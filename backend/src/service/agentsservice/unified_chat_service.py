import json
import re

from backend.src.ai_core.agents.unified_chat import UnifiedChat
from backend.src.ai_core.graph import resource_graph
from backend.src.service.agentsservice.resource_service import _make_state, _save_resources
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User

_FILE_EXT_MAP = {
    "document": "md", "ppt": "pptx", "mindmap": "md",
    "exercise": "md", "case": "md", "reading": "md",
}

_RESOURCE_TRIGGERS = [
    "生成", "制作", "出题", "总结成", "做成",
    "学习资料", "练习题", "PPT", "课件", "思维导图",
]

unified_chat_instances: dict[str, UnifiedChat] = {}


def _detect_resource_request(text: str) -> dict | None:
    """检测用户是否要生成学习资源，返回 {topic, resource_types} 或 None"""
    if not any(t in text for t in _RESOURCE_TRIGGERS):
        return None

    types = {"document"}
    if any(t in text for t in ["PPT", "ppt", "课件", "幻灯片"]):
        types.add("ppt")
    if any(t in text for t in ["习题", "题目", "练习题", "试题"]):
        types.add("exercise")
    if any(t in text for t in ["思维导图", "脑图"]):
        types.add("mindmap")
    if any(t in text for t in ["案例", "实例"]):
        types.add("case")

    cleaned = text
    for prefix in ["帮我", "请帮我", "给我", "请给我", "我想", "我要", "可以帮我"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    if cleaned.startswith("帮"):
        cleaned = cleaned[1:]

    m = re.search(r'(.+?)的(?:学习资料|PPT|课件|习题|练习题|思维导图)', cleaned)
    if m:
        topic = m.group(1).strip()
    else:
        for verb in ["生成", "制作", "出", "总结", "做"]:
            if cleaned.startswith(verb):
                cleaned = cleaned[len(verb):]
                break
        for suffix in ["学习资料", "PPT", "课件", "练习题", "习题", "思维导图", "资料"]:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)]
                break
        topic = cleaned.strip()

    if not topic or len(topic) > 30:
        topic = cleaned[:30] or "通用学习"

    return {"topic": topic, "resource_types": sorted(types)}


async def get_max_chat_group(user_id: int):
    max_chat_group = await ChatHistory.filter(user_id=user_id).order_by("-chat_group_id").first()
    if not max_chat_group:
        return 1
    return max_chat_group.chat_group_id + 1


async def _resource_stream(user_id: int, topic: str, resource_types: list[str]):
    """运行资源图，yield progress + file 事件"""
    initial_state = await _make_state(topic, user_id, resource_types)
    final_resources = {}
    final_passed = False
    final_retry = 0
    seen_executor = False
    seen_review = False

    async for full_state in resource_graph.astream(initial_state, stream_mode="values"):
        resources = full_state.get("generated_resources", {})
        passed = full_state.get("review_passed", False)
        retry = full_state.get("retry_count", 0)

        if resources and not seen_executor:
            seen_executor = True
            yield {"type": "content", "content": "正在生成学习内容..."}

        if passed and not seen_review:
            seen_review = True
            yield {"type": "content", "content": "正在审核生成结果..."}

        if resources:
            final_resources = resources
        if passed:
            final_passed = passed
        if retry > final_retry:
            final_retry = retry

    saved = await _save_resources(topic, user_id, final_resources, final_passed, final_retry)
    if not saved:
        yield {"type": "content", "content": "生成失败，请稍后重试。"}
        return

    for r in saved:
        ext = _FILE_EXT_MAP.get(r["resource_type"], "md")
        yield {
            "type": "file",
            "file_type": r["resource_type"],
            "filename": f"{r['topic']}_{r['resource_type']}.{ext}",
            "content": r["content"],
            "download_url": f"/resource/{r['resource_id']}/download",
        }

    lines = [f"- {r['resource_type']}: {len(r['content'])}字" for r in saved]
    context = f"已为用户生成了以下学习资料：\n" + "\n".join(lines)
    yield {"type": "resource_context", "content": context}


class UnifiedChatHistory_Service:

    @staticmethod
    async def create_new_history(user_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "未查找到用户"
        chat_group_id = await get_max_chat_group(user_id)
        instance_key = f"unified_{user_id}_{chat_group_id}"
        if instance_key not in unified_chat_instances:
            unified_chat_instances[instance_key] = UnifiedChat(user_id=user_id)
        bot = unified_chat_instances[instance_key]
        res = await bot.chat(user_req)
        message = await ChatHistory.create(
            user_id=user_id, chat_group_id=chat_group_id, req=user_req, res=res,
        )
        return message, "新对话保存成功"

    @staticmethod
    async def create_message_into_history(user_id: int, chat_group_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "未查找到用户"
        instance_key = f"unified_{user_id}_{chat_group_id}"
        if instance_key not in unified_chat_instances:
            unified_chat_instances[instance_key] = UnifiedChat(user_id=user_id)
        bot = unified_chat_instances[instance_key]
        res = await bot.chat(user_req)
        message = await ChatHistory.create(
            user_id=user_id, chat_group_id=chat_group_id, req=user_req, res=res,
        )
        return message, "问答保存成功"

    # ── 流式 ──

    @staticmethod
    async def stream_create_new_history(user_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            yield f"data: {json.dumps({'error': '未查找到用户'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        chat_group_id = await get_max_chat_group(user_id)
        instance_key = f"unified_{user_id}_{chat_group_id}"
        if instance_key not in unified_chat_instances:
            unified_chat_instances[instance_key] = UnifiedChat(user_id=user_id)

        # 预检测资源生成意图
        resource_req = _detect_resource_request(user_req)
        resource_context = ""
        if resource_req:
            async for ev in _resource_stream(user_id, resource_req["topic"], resource_req["resource_types"]):
                if ev.get("type") == "resource_context":
                    resource_context = ev["content"]
                else:
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

        bot = unified_chat_instances[instance_key]
        full_response = ""
        async for chunk in bot.stream(user_req, resource_context):
            if isinstance(chunk, dict):
                if chunk.get("type") == "content":
                    full_response += chunk["content"]
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            else:
                full_response += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"

        message = await ChatHistory.create(
            user_id=user_id, chat_group_id=chat_group_id, req=user_req, res=full_response,
        )
        yield f"data: {json.dumps({'type': 'done', 'chat_group_id': message.chat_group_id}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    @staticmethod
    async def stream_create_message_into_history(user_id: int, chat_group_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            yield f"data: {json.dumps({'error': '未查找到用户'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        instance_key = f"unified_{user_id}_{chat_group_id}"
        if instance_key not in unified_chat_instances:
            unified_chat_instances[instance_key] = UnifiedChat(user_id=user_id)

        # 预检测资源生成意图
        resource_req = _detect_resource_request(user_req)
        resource_context = ""
        if resource_req:
            async for ev in _resource_stream(user_id, resource_req["topic"], resource_req["resource_types"]):
                if ev.get("type") == "resource_context":
                    resource_context = ev["content"]
                else:
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

        bot = unified_chat_instances[instance_key]
        full_response = ""
        async for chunk in bot.stream(user_req, resource_context):
            if isinstance(chunk, dict):
                if chunk.get("type") == "content":
                    full_response += chunk["content"]
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            else:
                full_response += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"

        await ChatHistory.create(
            user_id=user_id, chat_group_id=chat_group_id, req=user_req, res=full_response,
        )
        yield f"data: {json.dumps({'type': 'done', 'chat_group_id': chat_group_id}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    # ── 读取、删除 ──

    @staticmethod
    async def read_history(user_id: int):
        records = await ChatHistory.filter(user__id=user_id).order_by("created_at").all()
        group_history = {}
        for record in records:
            gid = record.chat_group_id
            if gid not in group_history:
                group_history[gid] = []
            group_history[gid].append(record)
        return group_history, "返回群组字典成功"

    @staticmethod
    async def read_message(user_id: int, chat_group_id: int):
        records = await ChatHistory.filter(user__id=user_id, chat_group_id=chat_group_id).order_by("created_at").all()
        return [{"user_id": user_id, "chat_group_id": chat_group_id, "req": r.req, "res": r.res, "created_time": r.created_at} for r in records], "返回对话列表成功"

    @staticmethod
    async def delete_history(user_id: int, chat_group_id: int):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, None, "未查找到该用户"
        records = await ChatHistory.filter(user__id=user_id, chat_group_id=chat_group_id).all()
        if not records:
            return None, None, "未查找到该聊天组"
        await ChatHistory.delete(records)
        return user_id, chat_group_id, "删除成功"
