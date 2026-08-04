"""聊天历史记录工具 — 按聊天组隔离，返回紧凑预览（配合多级记忆系统）"""

from backend.src.utils.database import init_db
from langchain_core.tools import tool


@tool
async def get_used_history(user_id: str, chat_group_id: int = 0):
    """获取当前聊天组的历史记录（最近若干轮紧凑摘要），参数user_id为用户数字ID。
    当用户提到"之前说过""上次聊过"时调用；需要跨对话组回忆时用 search_memory。"""
    try:
        await init_db()
        uid = int(user_id.strip())
        gid = chat_group_id or 0
        from backend.src.service.memory.service import build_history_preview
        return await build_history_preview(uid, gid)
    except Exception as e:
        return f"获取历史记录失败：{e}"
