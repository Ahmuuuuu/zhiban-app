"""Unified helpers for parsing JSON returned by LLMs."""

import json
import logging

logger = logging.getLogger(__name__)


def _strip_code_fence(content: str) -> str:
    content = str(content or "").strip().lstrip("\ufeff")
    if not content.startswith("```"):
        return content

    lines = content.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_candidate(content: str) -> str:
    starts = [idx for idx in (content.find("["), content.find("{")) if idx >= 0]
    if not starts:
        return content

    start = min(starts)
    opener = content[start]
    closer = "]" if opener == "[" else "}"
    end = content.rfind(closer)
    if end > start:
        return content[start:end + 1].strip()
    return content[start:].strip()


def _loads_lenient(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError as strict_error:
        try:
            return json.loads(content, strict=False)
        except json.JSONDecodeError:
            raise strict_error


def parse_llm_json(text: str) -> dict | list:
    """Parse JSON from an LLM response.

    The parser accepts fenced markdown JSON, responses with short prose around
    the JSON payload, and raw control characters inside strings. The last case
    commonly appears in generated exercises when an explanation contains an
    unescaped newline.
    """
    content = _strip_code_fence(text)
    candidates = [content]
    extracted = _extract_json_candidate(content)
    if extracted and extracted != content:
        candidates.append(extracted)

    last_error = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return _loads_lenient(candidate)
        except json.JSONDecodeError as error:
            last_error = error

    logger.warning("LLM JSON 解析失败，原始响应前200字符: %s", str(text or "")[:200])
    if last_error:
        raise last_error
    raise json.JSONDecodeError("Empty JSON content", content, 0)
