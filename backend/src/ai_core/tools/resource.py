"""学习资源生成工具 — 返回结构化 graph 状态供 Brain 感知"""

import json
import re
import logging

from langchain_core.tools import tool
from backend.src.service.resource.service import ResourceService

logger = logging.getLogger(__name__)

_TYPE_LABELS = {
    "document": "文档", "ppt": "PPT", "exercise": "习题",
    "mindmap": "思维导图", "image": "图片", "case": "案例分析",
    "reading": "阅读材料",
    "external_video": "视频推荐",
}

# 明确的资源生成意图模式 — 只有匹配这些才允许执行
_EXPLICIT_GENERATION_PATTERNS = [
    r"(?:帮我|给我|请)(?:生成|制作|做|写|整理|弄|搞)(?:一个|一份|一些|几个|点)?(?:学习)?(?:资料|文档|PPT|课件|思维导图|脑图|习题|练习|案例|阅读)",
    r"(?:生成|制作|做|写|整理)(?:一个|一份|一下)?(?:学习)?(?:资料|文档|PPT|课件|思维导图|脑图|习题|练习|案例|阅读)",
    r"(?:要|想要|需要)(?:一个|一份)?(?:学习)?(?:资料|文档|PPT|课件|思维导图|脑图|习题|练习)",
    r"(?:出几?道|来几?道|弄几?道)(?:题|练习|习题)",
    r"帮我(?:复习|巩固|学习|备考|准备).{0,10}(?:资料|文档|PPT|课件)",
]


def _has_explicit_generation_intent(message: str) -> bool:
    """检查用户消息是否明确要求生成资源"""
    for pattern in _EXPLICIT_GENERATION_PATTERNS:
        if re.search(pattern, message):
            return True
    return False


@tool
async def generate_learning_resource(topic: str, user_id: str, resource_types: str = "document", chat_group_id: str = "0"):
    """生成学习资源。当用户说"帮我生成学习资料""做个PPT""出几道练习题""帮我整理成文档"时调用此工具。
    参数：topic学习主题，user_id用户数字ID，resource_types资源类型(逗号分隔，可选: document/ppt/mindmap/exercise/case/reading，默认document)，chat_group_id聊天组ID"""
    uid = int(user_id.strip())
    gid = int(chat_group_id) if str(chat_group_id).isdigit() else 0

    # 校验用户最后一条消息是否真的有生成意图，防止 LLM 误触发
    try:
        from backend.src.models.chat_history_model import ChatHistory
        last_msg = None
        if gid > 0:
            recent = await ChatHistory.filter(
                user_id=uid,
                chat_group_id=gid,
            ).order_by("-created_at").limit(5)
            last_msg = next((record for record in recent if record.req), None)
        last_text = (last_msg.req or "") if last_msg else ""
        if last_text:
            if not _has_explicit_generation_intent(last_text):
                logger.info("generate_learning_resource 被调用但用户消息无明确生成意图，已拦截。topic=%s msg=%s", topic, last_text[:80])
                return "[资源生成] 未检测到明确的资源生成请求。如果你确实需要生成学习资料，请直接告诉我：'帮我生成XX的文档/PPT/思维导图'。"
    except Exception:
        logger.exception("generate_learning_resource 意图校验失败 topic=%s gid=%s", topic, gid)

    types = [t.strip() for t in resource_types.split(",") if t.strip()]
    if not types:
        types = ["document"]
    results = await ResourceService.generate_and_save(
        topic,
        uid,
        types,
        chat_group_id=gid,
        include_request_in_history=False,
    )
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
                logger.debug("解析习题数量失败 rid=%s", rid)
        elif rt == "image":
            if r.get("file_url"):
                detail = "，图片已生成"
            else:
                detail = "，图片生成失败"

        status = f"，{'，'.join(status_parts)}" if status_parts else ""
        parts.append(f"  [{rid}] {label}：{content_len}字{detail}{status}")

    parts.append("你可以：查看某份资源(id) / 修改某份资源 / 重新生成 / 下载 PPT / 基于资源出题")
    return "\n".join(parts)
