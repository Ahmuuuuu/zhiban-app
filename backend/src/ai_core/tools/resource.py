"""学习资源生成工具 — 返回结构化 graph 状态供 Brain 感知"""

import json

from langchain_core.tools import tool
from backend.src.service.resource_service import ResourceService

_TYPE_LABELS = {
    "document": "文档", "ppt": "PPT", "exercise": "习题",
    "mindmap": "思维导图", "image": "图片", "case": "案例分析",
    "reading": "阅读材料",
}


@tool
async def generate_learning_resource(topic: str, user_id: str, resource_types: str = "document", chat_group_id: str = "0"):
    """生成学习资源。当用户说"帮我生成学习资料""做个PPT""出几道练习题""帮我整理成文档"时调用此工具。
    参数：topic学习主题，user_id用户数字ID，resource_types资源类型(逗号分隔，可选: document/ppt/mindmap/exercise/case/reading，默认document)，chat_group_id聊天组ID"""
    uid = int(user_id.strip())
    gid = int(chat_group_id) if str(chat_group_id).isdigit() else 0
    types = [t.strip() for t in resource_types.split(",") if t.strip()]
    if not types:
        types = ["document"]
    results = await ResourceService.generate_and_save(topic, uid, types, chat_group_id=gid)
    if not results:
        return "[资源生成] 生成失败，请稍后重试。"

    parts = [f"[资源生成] 已为「{topic}」生成 {len(results)} 份资源："]
    for r in results:
        rt = r.get("resource_type", "unknown")
        rid = r.get("resource_id", "?")
        content_len = len(r.get("content", ""))
        retry = r.get("retry_count", 0)
        passed = r.get("review_passed", True)

        label = _TYPE_LABELS.get(rt, rt)

        status_parts = []
        if passed:
            if retry > 0:
                status_parts.append(f"审核通过(重试{retry}次)")
        else:
            status_parts.append(f"审核未通过(已重试{retry}次)")

        detail = ""
        if rt == "exercise":
            try:
                questions = json.loads(r.get("content", "[]"))
                if isinstance(questions, list):
                    detail = f"，{len(questions)}题"
            except Exception:
                pass
        elif rt == "image":
            if r.get("file_url"):
                detail = "，图片已生成"
            else:
                detail = "，图片生成失败"

        status = f"，{'，'.join(status_parts)}" if status_parts else ""
        parts.append(f"  [{rid}] {label}：{content_len}字{detail}{status}")

    parts.append("你可以：查看某份资源(id) / 修改某份资源 / 重新生成 / 下载 PPT / 基于资源出题")
    return "\n".join(parts)
