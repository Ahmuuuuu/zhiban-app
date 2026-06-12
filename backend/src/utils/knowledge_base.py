"""
知识库 — 向量数据存储于 MySQL，支持用户隔离和公开/私有权限
BGE 模型仍从本地加载（开源模型，不包含用户数据）
"""
import os
import json
import hashlib
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
if HF_ENDPOINT:
    os.environ.setdefault("HF_ENDPOINT", HF_ENDPOINT)

from tortoise.expressions import Q

from sentence_transformers import SentenceTransformer

from backend.src.models.knowledgemodel import KnowledgeVector

MODEL_DIR = str(Path(__file__).parent.parent / "ai_core" / "knowledge_base" / "bge_model")
_embed_model = None


async def init_embed_model():
    """服务启动时预加载 BGE 模型（通过线程池，不阻塞事件循环）"""
    global _embed_model
    local_path = Path(MODEL_DIR)
    if local_path.exists() and any(local_path.iterdir()):
        _embed_model = await asyncio.to_thread(SentenceTransformer, str(local_path))
    else:
        _embed_model = await asyncio.to_thread(SentenceTransformer, "BAAI/bge-small-zh-v1.5")
        await asyncio.to_thread(_embed_model.save, str(local_path))


async def _encode_async(text: str):
    return await asyncio.to_thread(_embed_model.encode, text, normalize_embeddings=True)


async def search(query: str, top_k: int = 5, user_id: int = None, category: str = None) -> str:
    """
    从知识库检索资料。
    - user_id 为空：只查公开资料
    - user_id 不为空：查公开资料 + 该用户自己的私有资料
    - category: 限定分类，如 "exercise" / "textbook"
    """
    try:
        import numpy as np
        query_vec = await _encode_async(query)

        if user_id:
            qs = KnowledgeVector.filter(Q(visibility="public") | Q(user_id=user_id))
        else:
            qs = KnowledgeVector.filter(visibility="public")

        if category:
            qs = qs.filter(category=category)

        records = await qs.values("title", "content", "category", "embedding")

        if not records:
            return "知识库中暂无相关内容"

        scored = []
        for r in records:
            vec = np.array(json.loads(r["embedding"]), dtype=np.float32)
            sim = float(np.dot(query_vec, vec))
            scored.append((sim, r["title"], r["content"], r.get("category", "")))

        scored.sort(key=lambda x: x[0], reverse=True)

        items = [
            f"【资料{i+1}】来源：{title}（{cat}）\n{content}\n"
            for i, (_, title, content, cat) in enumerate(scored[:top_k])
        ]
        return "\n".join(items)

    except Exception as e:
        return f"知识库检索失败：{e}"


async def ingest(
    title: str,
    content: str,
    user_id: int = None,
    visibility: str = "private",
    category: str = "knowledge_point",
    cover_url: str | None = None,
) -> str:
    """
    向知识库添加一条资料。
    - user_id=None: 系统上传（需管理员权限）
    - visibility='public': 全员可见; 'private': 仅上传者可见
    - category: 见 KB_CATEGORIES
    - cover_url: 可选封面图 URL，不传则按 category 使用默认封面
    """
    try:
        if len(content.strip()) < 50:
            return "内容过短（<50字），未入库"

        doc_id = hashlib.sha256((title + content[:100]).encode()).hexdigest()[:16]
        vector = await _encode_async(content)

        existing = await KnowledgeVector.filter(doc_id=doc_id).first()
        if existing:
            updated = False
            if existing.visibility == "private" and visibility == "public":
                existing.visibility = "public"
                updated = True
            if existing.user_id is None and user_id is not None:
                existing.user_id = user_id
                updated = True
            if category != existing.category:
                existing.category = category
                updated = True
            if updated:
                await existing.save()
                return f"「{title}」已存在，已更新权限"
            return f"「{title}」已存在，跳过"

        if not cover_url:
            category_cover_map = {
                "knowledge_point": "document",
                "exercise": "exercise",
                "textbook": "document",
                "note": "document",
                "case_study": "document",
                "reference": "document",
            }
            cover_url = f"/static/covers/default_{category_cover_map.get(category, '')}.svg"

        await KnowledgeVector.create(
            doc_id=doc_id,
            title=title,
            content=content,
            embedding=json.dumps(vector.tolist()),
            user_id=user_id,
            visibility=visibility,
            category=category,
            cover_url=cover_url,
        )
        label = "公开" if visibility == "public" else "私有"
        return f"「{title}」已入库（{len(content)}字，{label}，{category}）"

    except Exception as e:
        return f"入库失败：{e}"


async def list_all(user_id: int = None, visibility: str = None) -> list[dict]:
    """
    列出知识库条目（原始切片）。
    - user_id: 过滤上传者（可选）
    - visibility: 过滤可见性（可选）
    """
    qs = KnowledgeVector.all()
    if user_id:
        qs = qs.filter(Q(visibility="public") | Q(user_id=user_id))
    if visibility:
        qs = qs.filter(visibility=visibility)

    records = await qs.order_by("-created_at").values(
        "doc_id", "title", "content", "category", "user_id", "visibility", "cover_url", "created_at"
    )
    return list(records)


async def list_grouped(user_id: int = None, visibility: str = None) -> list[dict]:
    """
    按原始文档分组展示，合并 BGE 切片避免前端展示混乱。
    切片标题格式: "文档名 (第N部分)" → 按 "文档名" 合并
    """
    import re

    qs = KnowledgeVector.all()
    if user_id:
        qs = qs.filter(Q(visibility="public") | Q(user_id=user_id))
    if visibility:
        qs = qs.filter(visibility=visibility)

    records = await qs.order_by("-created_at").values(
        "doc_id", "title", "content", "category", "user_id", "visibility", "cover_url", "created_at"
    )

    groups: dict[str, dict] = {}
    for r in records:
        title = r["title"]
        base = re.sub(r"\s*（第\d+部分）\s*", "", title)
        base = re.sub(r"\s*\(第\d+部分\)\s*", "", base)

        if base not in groups:
            groups[base] = {
                "title": base,
                "category": r.get("category", "knowledge_point"),
                "chunks": 0,
                "total_chars": 0,
                "preview": r["content"][:200],
                "visibility": r["visibility"],
                "uploader_id": r["user_id"],
                "cover_url": r.get("cover_url"),
                "created_at": str(r["created_at"]),
            }
        groups[base]["chunks"] += 1
        groups[base]["total_chars"] += len(r["content"])
        if str(r["created_at"]) < groups[base]["created_at"]:
            groups[base]["created_at"] = str(r["created_at"])

    return sorted(groups.values(), key=lambda x: x["created_at"], reverse=True)


async def get_by_id(doc_id: str) -> dict | None:
    """根据 doc_id 获取单条知识库记录"""
    record = await KnowledgeVector.filter(doc_id=doc_id).values(
        "doc_id", "title", "content", "category", "user_id", "visibility", "cover_url", "created_at"
    ).first()
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
            new_doc_id = hashlib.sha256((title or record.title + content[:100]).encode()).hexdigest()[:16]
            vector = await _encode_async(content)
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
