import json

from backend.src.ai_core.agent import UnifiedChat
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User

chat_instances: dict[str, UnifiedChat] = {}


async def get_max_chat_group(user_id: int):
    max_chat_group = await ChatHistory.filter(user_id=user_id).order_by("-chat_group_id").first()
    if not max_chat_group:
        return 1
    return max_chat_group.chat_group_id + 1


class ChatService:

    @staticmethod
    async def create_new_history(user_id: int, user_req: str):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "未查找到用户"
        chat_group_id = await get_max_chat_group(user_id)
        instance_key = f"unified_{user_id}_{chat_group_id}"
        if instance_key not in chat_instances:
            chat_instances[instance_key] = UnifiedChat(user_id=user_id)
        bot = chat_instances[instance_key]
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
        if instance_key not in chat_instances:
            chat_instances[instance_key] = UnifiedChat(user_id=user_id)
        bot = chat_instances[instance_key]
        res = await bot.chat(user_req)
        message = await ChatHistory.create(
            user_id=user_id, chat_group_id=chat_group_id, req=user_req, res=res,
        )
        return message, "问答保存成功"

    # ── 流式 ──

    @staticmethod
    async def _stream_chat(user_id: int, chat_group_id: int, user_req: str):
        """流式对话核心逻辑"""
        instance_key = f"unified_{user_id}_{chat_group_id}"
        if instance_key not in chat_instances:
            chat_instances[instance_key] = UnifiedChat(user_id=user_id)

        bot = chat_instances[instance_key]
        full_response = ""
        async for chunk in bot.stream(user_req):
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
        group_history = {}
        for record in records:
            gid = record.chat_group_id
            if gid not in group_history:
                group_history[gid] = []
            group_history[gid].append({
                "user_id": record.user_id,
                "chat_group_id": record.chat_group_id,
                "req": record.req,
                "res": record.res,
                "created_time": str(record.created_at) if record.created_at else None,
            })
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
        await ChatHistory.filter(user__id=user_id, chat_group_id=chat_group_id).delete()
        return user_id, chat_group_id, "删除成功"
