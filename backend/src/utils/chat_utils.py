"""聊天组 ID 分配工具 (全局锁 + 占位记录防竞态)"""

import asyncio
import logging
from backend.src.models.chat_history_model import ChatHistory

_logger = logging.getLogger("chat_utils")
_allocate_lock = asyncio.Lock()


async def allocate_chat_group_id(user_id: int) -> int:
    """为指定用户分配新的 chat_group_id。
    全局锁内「读 max + 写占位记录」，保证跨请求的并发安全。
    占位记录的 req/res 均为空串，读取历史时需过滤。
    """
    async with _allocate_lock:
        latest = await ChatHistory.filter(user_id=user_id).order_by("-chat_group_id").first()
        new_id = 1 if not latest or not latest.chat_group_id else latest.chat_group_id + 1
        _logger.info("分配 chat_group_id=%d user_id=%d (当前max=%s)",
                      new_id, user_id, latest.chat_group_id if latest else None)
        await ChatHistory.create(
            user_id=user_id,
            chat_group_id=new_id,
            req="",
            res="",
        )
        _logger.info("占位记录已写入 chat_group_id=%d user_id=%d", new_id, user_id)
        return new_id
