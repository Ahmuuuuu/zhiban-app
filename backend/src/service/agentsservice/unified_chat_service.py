import json
from backend.src.ai_core.agents.unified_chat import UnifiedChat
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User

# 防止记忆冲突
unified_chat_instances: dict[str, UnifiedChat] = {}


async def get_max_chat_group(user_id: int):
    max_chat_group = await ChatHistory.filter(user_id=user_id).order_by("-chat_group_id").first()
    if not max_chat_group:
        return 1
    return max_chat_group.chat_group_id + 1


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
            user_id=user_id,
            chat_group_id=chat_group_id,
            req=user_req,
            res=res,
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
            user_id=user_id,
            chat_group_id=chat_group_id,
            req=user_req,
            res=res,
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

        bot = unified_chat_instances[instance_key]
        full_response = ""
        async for chunk in bot.stream(user_req):
            full_response += chunk
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

        message = await ChatHistory.create(
            user_id=user_id,
            chat_group_id=chat_group_id,
            req=user_req,
            res=full_response,
        )
        yield f"data: {json.dumps({'done': True, 'chat_group_id': message.chat_group_id}, ensure_ascii=False)}\n\n"
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

        bot = unified_chat_instances[instance_key]
        full_response = ""
        async for chunk in bot.stream(user_req):
            full_response += chunk
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

        await ChatHistory.create(
            user_id=user_id,
            chat_group_id=chat_group_id,
            req=user_req,
            res=full_response,
        )
        yield f"data: {json.dumps({'done': True, 'chat_group_id': chat_group_id}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    # ── 读取 ──

    @staticmethod
    async def read_history(user_id: int):
        records = await ChatHistory.filter(
            user__id=user_id,
        ).order_by("created_at").all()
        group_history = {}
        for record in records:
            gid = record.chat_group_id
            if gid not in group_history:
                group_history[gid] = []
            group_history[gid].append(record)
        return group_history, "返回群组字典成功"

    @staticmethod
    async def read_message(user_id: int, chat_group_id: int):
        records = await ChatHistory.filter(
            user__id=user_id,
            chat_group_id=chat_group_id,
        ).order_by("created_at").all()
        req_and_res = []
        for record in records:
            req_and_res.append({
                "user_id": user_id,
                "chat_group_id": chat_group_id,
                "req": record.req,
                "res": record.res,
                "created_time": record.created_at,
            })
        return req_and_res, "返回对话列表成功"

    # ── 删除 ──

    @staticmethod
    async def delete_history(user_id: int, chat_group_id: int):
        user = await User.filter(id=user_id).first()
        if not user:
            return None, None, "未查找到该用户"
        records = await ChatHistory.filter(
            user__id=user_id,
            chat_group_id=chat_group_id,
        ).all()
        if not records:
            return None, None, "未查找到该聊天组"
        await ChatHistory.delete(records)
        return user_id, chat_group_id, "删除成功"
