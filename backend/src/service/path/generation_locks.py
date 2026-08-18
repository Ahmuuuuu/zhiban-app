import asyncio
from collections import OrderedDict

NodeGenerationKey = tuple[int, int, int, str]

# 上限：防止长期运行后锁字典无限增长（每个 (user, path, node, kind) 都会留下一个锁）
_MAX_LOCKS = 512
_NODE_GENERATION_LOCKS: "OrderedDict[NodeGenerationKey, asyncio.Lock]" = OrderedDict()
_NODE_GENERATION_LOCKS_GUARD = asyncio.Lock()


async def get_node_generation_lock(
    user_id: int,
    path_id: int,
    node_id: int,
    kind: str,
) -> asyncio.Lock:
    key = (int(user_id), int(path_id), int(node_id), kind)
    async with _NODE_GENERATION_LOCKS_GUARD:
        lock = _NODE_GENERATION_LOCKS.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _NODE_GENERATION_LOCKS[key] = lock
        else:
            # LRU 命中：刷新活跃度
            _NODE_GENERATION_LOCKS.move_to_end(key)
        if len(_NODE_GENERATION_LOCKS) > _MAX_LOCKS:
            # 只清理"未被持有且无等待者"的锁。
            # asyncio.Lock.locked() 在有等待者时为 True，因此不会删掉正在排队的关键锁，
            # 避免删除后并发请求拿到不同锁对象而破坏互斥。
            for stale_key, stale_lock in list(_NODE_GENERATION_LOCKS.items()):
                if stale_key == key:
                    continue
                if not stale_lock.locked():
                    del _NODE_GENERATION_LOCKS[stale_key]
                if len(_NODE_GENERATION_LOCKS) <= _MAX_LOCKS:
                    break
        return lock
