"""知识库工具：检索、入库、列出、更新、删除"""

from backend.src.utils.knowledge_base import (
    search as kb_search,
    ingest as kb_ingest,
    list_all as kb_list,
    update as kb_update,
    delete as kb_delete,
)
from langchain_core.tools import tool


@tool
async def search_knowledge_base(query: str, user_id: str, top_k: int = 5):
    """从知识库中检索相关资料。参数：query用户问题关键词，user_id用户数字ID，top_k返回条数默认5"""
    return await kb_search(query, top_k, user_id=int(user_id))


@tool
async def ingest_document(title: str, content: str, user_id: str):
    """向知识库添加一篇新资料。参数：title资料标题，content资料正文，user_id用户数字ID"""
    return await kb_ingest(title, content, user_id=int(user_id))


@tool
async def list_knowledge(user_id: str):
    """列出知识库中该用户可见的全部资料（公开+自己的私有）。参数：user_id用户数字ID"""
    records = await kb_list(user_id=int(user_id))
    if not records:
        return "知识库中暂无资料"
    lines = ["知识库资料列表："]
    for i, r in enumerate(records, 1):
        label = "公开" if r["visibility"] == "public" else "私有"
        lines.append(f"{i}. [{label}] {r['title']} (id: {r['doc_id']})")
        lines.append(f"   内容摘要：{r['content'][:120]}...")
    return "\n".join(lines)


@tool
async def update_knowledge(doc_id: str, user_id: str, title: str = None, content: str = None):
    """更新知识库中的一条资料。参数：doc_id资料ID，user_id用户数字ID，title新标题(可选)，content新内容(可选)"""
    return await kb_update(doc_id=doc_id, title=title, content=content, user_id=int(user_id), is_admin=False)


@tool
async def delete_knowledge(doc_id: str, user_id: str):
    """删除知识库中的一条资料（仅限自己上传的私有资料）。参数：doc_id资料ID，user_id用户数字ID"""
    return await kb_delete(doc_id=doc_id, user_id=int(user_id), is_admin=False)
