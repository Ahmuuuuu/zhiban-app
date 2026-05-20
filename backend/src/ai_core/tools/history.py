"""聊天历史记录工具"""

from backend.src.utils.database import init_db
from backend.src.models.usermodel import User
from langchain_core.tools import tool


@tool
async def get_used_history(user_id: str):
    """获取全部聊天记录，参数user_id为用户数字ID"""
    try:
        await init_db()
        user = await User.filter(id=int(user_id.strip())).first()
        if not user:
            return "未查找到该用户"
        history = await user.chat_history.all().order_by("created_at")
        if not history:
            return "该用户暂无聊天记录"
        chat_content = "【历史聊天记录】：\n"
        for message in history:
            chat_content += f"时间：{message.created_at} | 用户提问：{message.req} | AI回答：{message.res}\n"
        return chat_content
    except Exception as e:
        return f"获取历史记录失败：{e}"
