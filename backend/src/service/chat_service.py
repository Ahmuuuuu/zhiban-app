import json
import logging
from collections import OrderedDict

from backend.src.ai_core.brain import Brain
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User

logger = logging.getLogger(__name__)

_MAX_CHAT_INSTANCES = 100

_chat_instances: OrderedDict[str, Brain] = OrderedDict()


async def _build_path_context(user_id: int) -> str:
    """构建当前学习路径的上下文文本，注入聊天 prompt"""
    try:
        from backend.src.service.path_service import PathService
        current = await PathService.get_current_path(user_id)
        if not current:
            return ""
        nodes = current.get("nodes", [])
        completed = [n["title"] for n in nodes if n.get("status") == "completed"]
        current_node = next((n for n in nodes if n.get("status") in ("unlocked", "in_progress")), None)
        lines = [
            f"用户正在学习路径「{current['goal']}」，进度 {current['progress']}%。",
        ]
        if current_node:
            lines.append(f"当前节点：「{current_node['title']}」，类型：{current_node.get('type', 'read')}。")
        if completed:
            lines.append(f"已完成节点：{' → '.join(completed)}。")
        weak_points = current.get("diagnosis", {}).get("weak_points", [])
        if weak_points:
            lines.append(f"薄弱知识点：{', '.join(w['tag'] if isinstance(w, dict) else str(w) for w in weak_points)}。")
        return "\n".join(lines)
    except Exception:
        logger.exception("构建路径上下文失败 user_id=%s", user_id)
        return ""


import time as _time
_portrait_cache: dict[int, tuple[float, str]] = {}

async def _build_portrait_context(user_id: int) -> str:
    """构建用户画像 + 知识点掌握度 + 六维雷达的上下文文本（30s 缓存）"""
    now = _time.time()
    if user_id in _portrait_cache:
        ts, ctx = _portrait_cache[user_id]
        if now - ts < 30:
            return ctx
    try:
        from backend.src.service.portrait_service import PortraitChatHistory_Service, PortraitRadarService

        user = await User.filter(id=user_id).first()
        portrait, _ = await PortraitChatHistory_Service.read_portrait(user_id)
        traits = portrait.get("traits", {}) if portrait else {}
        lines = []

        # 用户基本信息 + 专业课程体系
        if user:
            info_parts = []
            if user.major:
                info_parts.append(f"专业：{user.major}")
            if user.grade:
                info_parts.append(f"年级：{user.grade}")
            if user.university:
                info_parts.append(f"学校：{user.university}")
            if info_parts:
                lines.append("【用户背景】")
                lines.append("、".join(info_parts))
            # 专业课程（从画像 traits 中读取，由 curriculum_service 同步）
            curriculum = traits.get("curriculum_courses") if traits else None
            if curriculum and isinstance(curriculum, list) and len(curriculum) > 0:
                lines.append(f"【专业课程】{'、'.join(curriculum)}（以上为该专业当前阶段核心课程，请结合课程内容辅助学习）")

        if traits:
            if lines:
                lines.append("")
            for key, label in [
                ("strengths", "强项"), ("weaknesses", "弱项"), ("interest", "兴趣"),
                ("knowbase", "知识基础"), ("learning_pace", "学习节奏"), ("commonmis", "常见误区"),
            ]:
                val = traits.get(key)
                if val and isinstance(val, dict) and val.get("value"):
                    lines.append(f"- {label}：{val['value']}")
            mastery = traits.get("knowledge_mastery")
            if mastery and isinstance(mastery, list):
                tags = [f"{m.get('tag', '')}({m.get('level', '')})" for m in mastery[:8] if m.get("tag")]
                if tags:
                    lines.append(f"- 知识点掌握度：{'、'.join(tags)}")
            # 六维雷达
            try:
                radar = await PortraitRadarService.get(user_id)
                if radar and radar.get("dimensions"):
                    lines.append(PortraitRadarService.format_for_prompt(radar))
            except Exception:
                pass
            # 学习指导
            try:
                from backend.src.service.portrait_service import build_learning_guidance
                guidance = await build_learning_guidance(user_id)
                if guidance:
                    lines.append(guidance)
            except Exception:
                pass

        if not lines:
            ctx = ""
        else:
            ctx = "用户画像：\n" + "\n".join(lines)
        _portrait_cache[user_id] = (_time.time(), ctx)
        return ctx
    except Exception:
        logger.exception("构建画像上下文失败 user_id=%s", user_id)
        return ""


def invalidate_portrait_cache(user_id: int):
    """用户信息变更后清除画像缓存，确保下次对话使用最新数据"""
    _portrait_cache.pop(user_id, None)


def _get_or_create_chat(user_id: int, chat_group_id: int) -> Brain:
    instance_key = f"brain_{user_id}_{chat_group_id}"
    if instance_key not in _chat_instances:
        if len(_chat_instances) >= _MAX_CHAT_INSTANCES:
            _chat_instances.popitem(last=False)
        _chat_instances[instance_key] = Brain(user_id=user_id, chat_group_id=chat_group_id)
    else:
        _chat_instances.move_to_end(instance_key)
    return _chat_instances[instance_key]


async def get_max_chat_group(user_id: int):
    max_chat_group = await ChatHistory.filter(user_id=user_id).order_by("-chat_group_id").first()
    if not max_chat_group or not max_chat_group.chat_group_id:
        logger.info("文本对话分配首个聊天组 user_id=%s chat_group_id=1", user_id)
        return 1
    new_id = max_chat_group.chat_group_id + 1
    logger.info("文本对话分配新聊天组 user_id=%s chat_group_id=%d", user_id, new_id)
    return new_id


class ChatService:

    @staticmethod
    async def create_new_history(user_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "未查找到用户"
        chat_group_id = await get_max_chat_group(user_id)
        bot = _get_or_create_chat(user_id, chat_group_id)
        path_context = await _build_path_context(user_id)
        portrait_context = await _build_portrait_context(user_id)
        res = await bot.chat(user_req, path_context=path_context, portrait_context=portrait_context)
        message = await ChatHistory.create(
            user_id=user_id, chat_group_id=chat_group_id, req=user_req, res=res,
        )
        return message, "新对话保存成功"

    @staticmethod
    async def create_message_into_history(user_id: int, chat_group_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "未查找到用户"
        bot = _get_or_create_chat(user_id, chat_group_id)
        path_context = await _build_path_context(user_id)
        portrait_context = await _build_portrait_context(user_id)
        res = await bot.chat(user_req, path_context=path_context, portrait_context=portrait_context)
        message = await ChatHistory.create(
            user_id=user_id, chat_group_id=chat_group_id, req=user_req, res=res,
        )
        return message, "问答保存成功"

    # ── 流式 ──

    @staticmethod
    async def _stream_chat(user_id: int, chat_group_id: int, user_req: str):
        """流式对话核心逻辑"""
        bot = _get_or_create_chat(user_id, chat_group_id)
        path_context = await _build_path_context(user_id)
        portrait_context = await _build_portrait_context(user_id)
        full_response = ""
        async for chunk in bot.stream(user_req, path_context=path_context, portrait_context=portrait_context):
            if isinstance(chunk, dict):
                if chunk.get("type") in ("chunk", "content"):
                    full_response += chunk.get("content", "")
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            else:
                full_response += chunk
                yield f"data: {json.dumps({'role': 'assistant', 'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

        await ChatHistory.create(
            user_id=user_id, chat_group_id=chat_group_id, req=user_req, res=full_response,
        )
        yield f"data: {json.dumps({'role': 'system', 'type': 'done', 'chat_group_id': chat_group_id}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    @staticmethod
    async def stream_create_new_history(user_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            yield f"data: {json.dumps({'error': '未查找到用户'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        chat_group_id = await get_max_chat_group(user_id)
        async for event in ChatService._stream_chat(user_id, chat_group_id, user_req):
            yield event

    @staticmethod
    async def stream_create_message_into_history(user_id: int, chat_group_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            yield f"data: {json.dumps({'error': '未查找到用户'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        async for event in ChatService._stream_chat(user_id, chat_group_id, user_req):
            yield event

    # ── 读取、删除 ──

    @staticmethod
    async def read_history(user_id: int):
        records = await ChatHistory.filter(user__id=user_id).order_by("created_at").all()
        group_history: dict[int, list[dict]] = {}
        for record in records:
            gid = record.chat_group_id
            if gid is None:
                continue  # 跳过 chat_group_id 为 NULL 的旧记录
            if gid not in group_history:
                group_history[gid] = []
            group_history[gid].append({
                "role": "user",
                "type": "text",
                "content": record.req,
                "created_time": str(record.created_at) if record.created_at else None,
            })
            group_history[gid].append({
                "role": "assistant",
                "type": "text",
                "content": record.res,
                "created_time": str(record.created_at) if record.created_at else None,
            })

        result = []
        for gid, messages in group_history.items():
            first_user = next((m for m in messages if m["role"] == "user"), None)
            last_msg = messages[-1] if messages else None
            result.append({
                "id": gid,
                "title": first_user["content"] if first_user else f"对话 {gid}",
                "last_message": last_msg["content"] if last_msg else "",
                "message_count": len(messages),
                "created_time": last_msg["created_time"] if last_msg else None,
            })
        return sorted(result, key=lambda x: x["created_time"] or ""), "返回群组列表成功"

    @staticmethod
    async def read_message(user_id: int, chat_group_id: int):
        records = await ChatHistory.filter(user__id=user_id, chat_group_id=chat_group_id).order_by("created_at").all()
        messages = []
        for r in records:
            created_time = str(r.created_at) if r.created_at else None
            messages.append({"role": "user", "type": "text", "content": r.req, "created_time": created_time})
            messages.append({"role": "assistant", "type": "text", "content": r.res, "created_time": created_time})
        return messages, "返回消息列表成功"

    @staticmethod
    async def delete_history(user_id: int, chat_group_id: int):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, None, "未查找到该用户"
        records = await ChatHistory.filter(user__id=user_id, chat_group_id=chat_group_id).all()
        if not records:
            return None, None, "未查找到该聊天组"
        await ChatHistory.filter(user__id=user_id, chat_group_id=chat_group_id).delete()
        return user_id, chat_group_id, "删除成功"
