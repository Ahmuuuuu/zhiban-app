import asyncio

NodeGenerationKey = tuple[int, int, int, str]

_NODE_GENERATION_LOCKS: dict[NodeGenerationKey, asyncio.Lock] = {}
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
        return lock
