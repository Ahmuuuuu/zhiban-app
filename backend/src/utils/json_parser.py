"""统一的 LLM JSON 响应解析，自动去除 markdown 代码块包裹"""

import json
import logging

logger = logging.getLogger(__name__)


def parse_llm_json(text: str) -> dict | list:
    """从 LLM 响应中提取 JSON，去除 markdown 代码块包裹"""
    content = text.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:])
        if content.endswith("```"):
            content = content[:-3]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("LLM JSON 解析失败，原始响应前200字符: %s", text[:200])
        raise
