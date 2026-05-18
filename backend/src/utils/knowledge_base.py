"""
知识库 — 向量数据存储于 MySQL，支持用户隔离和公开/私有权限
BGE 模型仍从本地加载（开源模型，不包含用户数据）
"""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from tortoise.expressions import Q

from backend.src.models.knowledgemodel import KnowledgeVector

# BGE 模型本地缓存路径 — 第一次会自动下载到这里，后续离线加载
MODEL_DIR = str(Path(__file__).parent.parent / "ai_core" / "knowledge_base" / "bge_model")
_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is not None:
        return _embed_model

    local_path = Path(MODEL_DIR)
    if local_path.exists() and any(local_path.iterdir()):
        _embed_model = SentenceTransformer(str(local_path))
    else:
        _embed_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        _embed_model.save(str(local_path))
    return _embed_model


async def search(query: str, top_k: int = 5, user_id: int = None) -> str:
    """
    从知识库检索资料。
    - user_id 为空：只查公开资料
    - user_id 不为空：查公开资料 + 该用户自己的私有资料
    """
    try:
        model = _get_embed_model()
        query_vec = model.encode(query, normalize_embeddings=True)

        if user_id:
            records = await KnowledgeVector.filter(
                Q(visibility="public") | Q(user_id=user_id)
            ).values("title", "content", "embedding")
        else:
            records = await KnowledgeVector.filter(
                visibility="public"
            ).values("title", "content", "embedding")

        if not records:
            return "知识库中暂无相关内容"

        scored = []
        for r in records:
            vec = np.array(json.loads(r["embedding"]), dtype=np.float32)
            sim = float(np.dot(query_vec, vec))
            scored.append((sim, r["title"], r["content"]))

        scored.sort(key=lambda x: x[0], reverse=True)

        items = [
            f"【资料{i+1}】来源：{title}\n{content}\n"
            for i, (_, title, content) in enumerate(scored[:top_k])
        ]
        return "\n".join(items)

    except Exception as e:
        return f"知识库检索失败：{e}"


async def ingest(
    title: str,
    content: str,
    user_id: int = None,
    visibility: str = "private",
) -> str:
    """
    向知识库添加一条资料。
    - user_id=None: 系统上传（需管理员权限）
    - visibility='public': 全员可见; 'private': 仅上传者可见
    """
    try:
        if len(content.strip()) < 50:
            return "内容过短（<50字），未入库"

        model = _get_embed_model()
        doc_id = str(hash(title + content[:100]))
        vector = model.encode(content, normalize_embeddings=True)

        existing = await KnowledgeVector.filter(doc_id=doc_id).first()
        if existing:
            updated = False
            if existing.visibility == "private" and visibility == "public":
                existing.visibility = "public"
                updated = True
            if existing.user_id is None and user_id is not None:
                existing.user_id = user_id
                updated = True
            if updated:
                await existing.save()
                return f"「{title}」已存在，已更新权限"
            return f"「{title}」已存在，跳过"

        await KnowledgeVector.create(
            doc_id=doc_id,
            title=title,
            content=content,
            embedding=json.dumps(vector.tolist()),
            user_id=user_id,
            visibility=visibility,
        )
        label = "公开" if visibility == "public" else "私有"
        return f"「{title}」已入库（{len(content)}字，{label}）"

    except Exception as e:
        return f"入库失败：{e}"


async def list_all(user_id: int = None, visibility: str = None) -> list[dict]:
    """
    列出知识库条目。
    - user_id: 过滤上传者（可选）
    - visibility: 过滤可见性（可选）
    """
    qs = KnowledgeVector.all()
    if user_id:
        qs = qs.filter(Q(visibility="public") | Q(user_id=user_id))
    if visibility:
        qs = qs.filter(visibility=visibility)

    records = await qs.order_by("-created_at").values(
        "doc_id", "title", "content", "user_id", "visibility", "created_at"
    )
    return list(records)


async def get_by_id(doc_id: str) -> dict | None:
    """根据 doc_id 获取单条知识库记录"""
    record = await KnowledgeVector.filter(doc_id=doc_id).first().values(
        "doc_id", "title", "content", "user_id", "visibility", "created_at"
    )
    return record


async def update(
    doc_id: str,
    title: str = None,
    content: str = None,
    visibility: str = None,
    user_id: int = None,
    is_admin: bool = False,
) -> str:
    """
    更新知识库条目。
    - 仅 owner 或 admin 可操作
    - content 变更会自动重新嵌入向量
    """
    try:
        record = await KnowledgeVector.filter(doc_id=doc_id).first()
        if not record:
            return "记录不存在"

        # ── 权限：仅 owner 或 admin ──
        if record.user_id is not None and record.user_id != user_id and not is_admin:
            return "无权修改他人私有资料"

        # ── 系统资料仅 admin ──
        if record.user_id is None and not is_admin:
            return "无权修改系统公开资料"

        if title is not None:
            record.title = title
        if visibility is not None:
            record.visibility = visibility

        # 内容变更 → 重新嵌入
        if content is not None:
            if len(content.strip()) < 50:
                return "内容过短（<50字），更新失败"
            model = _get_embed_model()
            new_doc_id = str(hash(title or record.title + content[:100]))
            vector = model.encode(content, normalize_embeddings=True)
            record.doc_id = new_doc_id
            record.content = content
            record.embedding = json.dumps(vector.tolist())

        await record.save()
        return f"「{record.title}」已更新"
    except Exception as e:
        return f"更新失败：{e}"


async def delete(doc_id: str, user_id: int = None, is_admin: bool = False) -> str:
    """
    删除知识库条目。
    - 仅 owner 或 admin 可操作
    """
    try:
        record = await KnowledgeVector.filter(doc_id=doc_id).first()
        if not record:
            return "记录不存在"

        if record.user_id is not None and record.user_id != user_id and not is_admin:
            return "无权删除他人私有资料"
        if record.user_id is None and not is_admin:
            return "无权删除系统公开资料"

        title = record.title
        await record.delete()
        return f"「{title}」已删除"
    except Exception as e:
        return f"删除失败：{e}"
