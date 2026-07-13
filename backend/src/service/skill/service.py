import json

from backend.src.models.agent_skill_model import AgentSkill

ALLOWED_RESOURCE_TYPES = {"document", "ppt", "mindmap", "exercise", "case", "reading"}
ALLOWED_ACTION_TYPES = {"http"}



# ═══════════════════════════════════════
#  生成 skill（原有）
# ═══════════════════════════════════════

async def upsert_generation(user_id: int, resource_type: str, name: str, system_prompt: str) -> dict:
    if resource_type not in ALLOWED_RESOURCE_TYPES:
        raise ValueError(f"不支持的资源类型: {resource_type}，可选: {', '.join(sorted(ALLOWED_RESOURCE_TYPES))}")

    skill = await AgentSkill.filter(user_id=user_id, resource_type=resource_type, skill_type="generation").first()

    if skill:
        skill.name = name
        skill.system_prompt = system_prompt
        skill.enabled = True
        await skill.save()
        action = "updated"
    else:
        skill = await AgentSkill.create(
            user_id=user_id,
            skill_type="generation",
            resource_type=resource_type,
            name=name,
            system_prompt=system_prompt,
        )
        action = "created"

    return {"skill_id": skill.id, "resource_type": skill.resource_type, "name": skill.name, "action": action}

# ═══════════════════════════════════════
#  动作 skill（新增）
# ═══════════════════════════════════════

async def upsert_action(
    user_id: int,
    name: str,
    action_type: str,
    action_config: dict,
    tool_description: str,
) -> dict:
    if action_type not in ALLOWED_ACTION_TYPES:
        raise ValueError(f"不支持的动作类型: {action_type}，可选: {', '.join(sorted(ALLOWED_ACTION_TYPES))}")

    if action_type == "http":
        if "url" not in action_config:
            raise ValueError("HTTP skill 必须包含 url")
        action_config.setdefault("method", "GET")

    resource_type = f"action:{name}"
    skill = await AgentSkill.filter(user_id=user_id, resource_type=resource_type, skill_type="action").first()

    if skill:
        skill.name = name
        skill.action_type = action_type
        skill.action_config = json.dumps(action_config, ensure_ascii=False)
        skill.tool_description = tool_description
        skill.enabled = True
        await skill.save()
        action = "updated"
    else:
        skill = await AgentSkill.create(
            user_id=user_id,
            skill_type="action",
            resource_type=resource_type,
            name=name,
            system_prompt="",
            action_type=action_type,
            action_config=json.dumps(action_config, ensure_ascii=False),
            tool_description=tool_description,
        )
        action = "created"

    return {"skill_id": skill.id, "name": skill.name, "action_type": skill.action_type, "action": action}

# ═══════════════════════════════════════
#  通用 upsert（兼容旧接口）
# ═══════════════════════════════════════

async def upsert(user_id: int, resource_type: str, name: str, system_prompt: str) -> dict:
    """兼容旧的 generation skill upsert 接口"""
    return await upsert_generation(user_id, resource_type, name, system_prompt)

# ═══════════════════════════════════════
#  查询
# ═══════════════════════════════════════

async def get(user_id: int, resource_type: str) -> dict | None:
    skill = await AgentSkill.filter(user_id=user_id, resource_type=resource_type, enabled=True).first()
    if not skill:
        return None
    result = {
        "skill_id": skill.id,
        "skill_type": skill.skill_type,
        "name": skill.name,
        "created_at": str(skill.created_at),
        "updated_at": str(skill.updated_at),
    }
    if skill.skill_type == "generation":
        result["resource_type"] = skill.resource_type
        result["system_prompt"] = skill.system_prompt
    elif skill.skill_type == "action":
        result["action_type"] = skill.action_type
        result["action_config"] = skill.action_config
        result["tool_description"] = skill.tool_description
    return result

async def list_all(user_id: int) -> list[dict]:
    skills = await AgentSkill.filter(user_id=user_id, enabled=True).all()
    result = []
    for s in skills:
        item = {
            "skill_id": s.id,
            "skill_type": s.skill_type,
            "name": s.name,
            "updated_at": str(s.updated_at),
        }
        if s.skill_type == "generation":
            item["resource_type"] = s.resource_type
            item["prompt_length"] = len(s.system_prompt or "")
        elif s.skill_type == "action":
            item["action_type"] = s.action_type
            item["tool_description"] = s.tool_description
        result.append(item)
    return result

async def list_actions(user_id: int) -> list[dict]:
    """仅返回启用的 action skill，供动态 tool 加载"""
    skills = await AgentSkill.filter(user_id=user_id, skill_type="action", enabled=True).all()
    return [
        {
            "skill_id": s.id,
            "name": s.name,
            "action_type": s.action_type,
            "action_config": s.action_config,
            "tool_description": s.tool_description,
        }
        for s in skills
    ]

async def delete(user_id: int, resource_type: str) -> str:
    skill = await AgentSkill.filter(user_id=user_id, resource_type=resource_type).first()
    if not skill:
        return "技能不存在"
    label = skill.name
    await skill.delete()
    return f"技能 '{label}' 已删除"
