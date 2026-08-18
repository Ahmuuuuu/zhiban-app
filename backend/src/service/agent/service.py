# -*- coding: utf-8 -*-
"""用户自建智能体 CRUD + 记忆管理"""

import json
import logging
from datetime import datetime, timezone

from backend.src.models.user_agent_model import UserAgent

logger = logging.getLogger(__name__)

_ALLOWED_TOOLS = {
    "search_knowledge_base", "ingest_document", "search_web_and_stage_knowledge",
    "list_knowledge", "update_knowledge", "delete_knowledge",
    "read_portrait", "update_portrait", "get_used_history", "web_search",
    "read_skill", "upsert_skill", "list_skills", "delete_skill", "create_action_skill",
    "generate_learning_resource", "generate_image", "generate_exam_questions",
    "generate_slide_animation", "search_online_video",
    "list_learning_paths", "get_learning_path_detail", "enroll_learning_path",
    "regenerate_learning_path", "update_path_node", "add_path_node", "delete_path_node",
    "search_memory",
}

# 系统内置智能体的保留名称：用户不得自建同名智能体，避免身份劫持
_RESERVED_AGENT_NAMES = {"课堂小知"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(raw: str | None, default=None):
    if default is None:
        default = []
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _dump_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


_PERSONA_BLOCKLIST = [
    r"ignore\s+(all\s+)?(previous|prior|above|before)\s+(instructions?|prompts?|rules?)",
    r"(you\s+are|act\s+as)\s+(DAN|jailbreak|unfiltered|unrestricted)",
    r"(forget|disregard|override)\s+(your|all)\s+(training|guidelines?|safety)",
    r"(roleplay|role.play)\s+(as|like)\s+(girlfriend|boyfriend|lover|partner)",
    r"(pretend|imagine)\s+you\s+(are|were)\s+(not|no\s+longer)",
]

import re as _re

def _validate_persona(persona: str) -> str:
    for pattern in _PERSONA_BLOCKLIST:
        if _re.search(pattern, persona, _re.IGNORECASE):
            raise ValueError("角色设定包含不安全内容，请修改后重试")
    return persona.strip()[:2000]


def _validate_tools(tools: list) -> list:
    return [t for t in tools if t in _ALLOWED_TOOLS]


# ═══════════════════════════════════════
#  CRUD
# ═══════════════════════════════════════

async def create(user_id: int, name: str, persona: str = "",
                 tools: list | None = None, avatar: str = "",
                 schedule: dict | None = None,
                 is_system: bool = False) -> dict:
    name = name.strip()[:64]
    if not is_system and name in _RESERVED_AGENT_NAMES:
        raise ValueError("该名称已保留，无法创建同名智能体")
    agent = await UserAgent.create(
        user_id=user_id,
        name=name,
        avatar=avatar,
        persona=_validate_persona(persona),
        tools=_dump_json(_validate_tools(tools or [])),
        schedule=_dump_json(schedule) if schedule else None,
        is_system=is_system,
    )
    return _to_dict(agent)


async def update(user_id: int, agent_id: int, **kwargs) -> dict | None:
    agent = await UserAgent.filter(id=agent_id, user_id=user_id).first()
    if not agent:
        return None
    if getattr(agent, "is_system", False):
        raise ValueError("系统内置智能体不可编辑")

    behavior_changed = False
    if "name" in kwargs:
        new_name = str(kwargs["name"]).strip()[:64]
        if new_name in _RESERVED_AGENT_NAMES and new_name != agent.name:
            raise ValueError("该名称已保留，无法修改")
        agent.name = new_name
        behavior_changed = True
    if "persona" in kwargs:
        new_persona = _validate_persona(str(kwargs["persona"]))
        if new_persona != agent.persona:
            agent.persona = new_persona
            behavior_changed = True
    if "tools" in kwargs:
        new_tools = _dump_json(_validate_tools(kwargs["tools"]))
        if new_tools != agent.tools:
            agent.tools = new_tools
            behavior_changed = True
    if "avatar" in kwargs:
        new_avatar = str(kwargs["avatar"])
        if new_avatar != agent.avatar:
            agent.avatar = new_avatar
            behavior_changed = True
    if "is_public" in kwargs:
        agent.is_public = bool(kwargs["is_public"])
    if "enabled" in kwargs:
        was_enabled = agent.enabled
        agent.enabled = bool(kwargs["enabled"])
        if was_enabled and not agent.enabled:
            from backend.src.ai_core.brain import Brain
            Brain.rebuild_for_user(user_id)
    if "schedule" in kwargs:
        agent.schedule = _dump_json(kwargs["schedule"]) if kwargs["schedule"] else None

    await agent.save()
    # 人设/工具/头像变化后，旧 Brain 不会自动感知，主动踢缓存让下次重新加载
    if behavior_changed:
        from backend.src.ai_core.brain import Brain
        Brain.rebuild_for_user(user_id)
    return _to_dict(agent)


async def delete(user_id: int, agent_id: int) -> bool:
    agent = await UserAgent.filter(id=agent_id, user_id=user_id).first()
    if not agent:
        return False
    if getattr(agent, "is_system", False):
        raise ValueError("系统内置智能体不可删除")
    await agent.delete()
    return True


async def get(user_id: int, agent_id: int) -> dict | None:
    agent = await UserAgent.filter(id=agent_id, user_id=user_id, enabled=True).first()
    if not agent:
        return None
    return _to_dict(agent)


async def list_by_user(user_id: int) -> list[dict]:
    agents = await UserAgent.filter(user_id=user_id, enabled=True).order_by("-updated_at").all()
    return [_to_brief(a) for a in agents]


async def list_public(user_id: int) -> list[dict]:
    """公开市场：排除当前用户自己的"""
    agents = await UserAgent.filter(is_public=True, enabled=True).exclude(user_id=user_id).order_by("-updated_at").all()
    return [_to_brief(a) for a in agents]


async def copy(user_id: int, source_agent_id: int) -> dict | None:
    """从公开市场复制一个智能体到自己的空间"""
    source = await UserAgent.filter(id=source_agent_id, is_public=True, enabled=True).first()
    if not source:
        return None
    agent = await UserAgent.create(
        user_id=user_id,
        name=f"{source.name} (副本)",
        avatar=source.avatar,
        persona=source.persona,
        tools=source.tools,
    )
    return _to_dict(agent)


# ═══════════════════════════════════════
#  记忆管理
# ═══════════════════════════════════════

async def append_memory(user_id: int, agent_id: int, entry: str, max_entries: int = 20) -> None:
    agent = await UserAgent.filter(id=agent_id, user_id=user_id).first()
    if not agent:
        return
    memory = _load_json(agent.memory, [])
    memory.append({"content": entry, "time": _now_iso()})
    if len(memory) > max_entries:
        memory = memory[-max_entries:]
    agent.memory = _dump_json(memory)
    await agent.save()


async def get_memory_text(user_id: int, agent_id: int) -> str:
    agent = await UserAgent.filter(id=agent_id, user_id=user_id).first()
    if not agent:
        return ""
    memory = _load_json(agent.memory, [])
    if not memory:
        return ""
    lines = ["\n## 智能体记忆（历史对话摘要）"]
    for i, m in enumerate(memory, 1):
        lines.append(f"{i}. {m['content']}")
    return "\n".join(lines)


# ═══════════════════════════════════════
#  序列化
# ═══════════════════════════════════════

def _to_dict(a: UserAgent) -> dict:
    return {
        "id": a.id,
        "user_id": a.user_id,
        "name": a.name,
        "avatar": a.avatar,
        "persona": a.persona,
        "tools": _load_json(a.tools),
        "is_public": a.is_public,
        "enabled": a.enabled,
        "is_system": getattr(a, "is_system", False),
        "schedule": _load_json(a.schedule, {}),
        "created_at": str(a.created_at),
        "updated_at": str(a.updated_at),
    }


def _to_brief(a: UserAgent) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "avatar": a.avatar,
        "persona": a.persona[:120],
        "tool_count": len(_load_json(a.tools)),
        "is_public": a.is_public,
        "is_system": getattr(a, "is_system", False),
        "created_at": str(a.created_at),
        "updated_at": str(a.updated_at),
    }
