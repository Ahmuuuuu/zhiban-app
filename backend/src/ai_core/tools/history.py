"""聊天历史记录工具 — 按聊天组隔离"""

from backend.src.utils.database import init_db
from backend.src.models.usermodel import User
from langchain_core.tools import tool


@tool
async def get_used_history(user_id: str, chat_group_id: int = 0):
    """获取当前聊天组的历史记录，参数user_id为用户数字ID"""
    try:
        await init_db()
        user = await User.filter(id=int(user_id.strip())).first()
        if not user:
            return "未查找到该用户"
        qs = user.chat_history
        if chat_group_id:
            qs = qs.filter(chat_group_id=chat_group_id)
        history = await qs.order_by("created_at")
        if not history:
            return "当前聊天组暂无历史记录"
        chat_content = "【当前聊天组的历史记录】：\n"
        for message in history:
            chat_content += f"用户提问：{message.req} | AI回答：{message.res}\n"
        return chat_content
    except Exception as e:
        return f"获取历史记录失败：{e}"
