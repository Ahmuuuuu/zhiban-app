"""
记忆向量封装 — 复用 knowledge_base 的 BGE 本地模型 + Redis 缓存。

只做一件事：把文本编码成归一化向量。写入（情景摘要、原文索引）和
读取（语义检索）共用同一入口，避免记忆模块自己再维护一套 embedding。
"""

from __future__ import annotations


async def encode(text: str):
    """编码文本为归一化向量（BGE + Redis 缓存 + 线程池）。"""
    from backend.src.utils.knowledge_base import _encode_async

    if not text or not text.strip():
        raise ValueError("encode() 需要非空文本")
    return await _encode_async(text)
