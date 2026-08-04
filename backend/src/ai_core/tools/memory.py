"""记忆检索工具 — 让 agent 主动跨组查询用户的长期记忆"""

from backend.src.utils.database import init_db
from langchain_core.tools import tool

from backend.src.service.memory.retrieval import retrieve_episodes, retrieve_messages, retrieve_kvs


@tool
async def search_memory(user_id: str, query: str, chat_group_id: int = 0, top_k: int = 5):
    """检索该用户的长期记忆（跨对话组），包括历史对话摘要、用户原话、长期事实。
    参数 user_id 为用户数字ID；query 为要检索的内容描述；chat_group_id 为当前会话组ID。
    当用户问"之前说过/上次聊过/我记得你讲过"之类，或需要结合历史信息时调用。"""
    try:
        await init_db()
        uid = int(user_id.strip())
        gid = chat_group_id or 0

        parts = []
        episodes = await retrieve_episodes(uid, gid, query, top_k=max(1, min(3, top_k)))
        for ep in episodes:
            tag = f"会话{ep['chat_group_id']}" if ep["chat_group_id"] != gid else "当前会话"
            parts.append(f"[历史对话·{tag}] {ep['summary'][:200]}")

        msgs = await retrieve_messages(uid, gid, query, top_k=max(1, min(3, top_k)))
        for m in msgs:
            parts.append(f"[用户原话] {m['content'][:150]}")

        kvs = await retrieve_kvs(uid, gid, query, top_k=max(1, min(5, top_k)))
        for v in kvs:
            parts.append(f"[长期事实] {v[:150]}")

        if not parts:
            return "没有检索到相关的长期记忆。"
        return "检索到的长期记忆：\n" + "\n".join(parts)
    except Exception as e:
        return f"记忆检索失败：{e}"
