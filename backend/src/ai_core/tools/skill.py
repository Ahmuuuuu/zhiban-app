"""Skill 管理工具"""

import json
from langchain_core.tools import tool


@tool
async def read_skill(resource_type: str, user_id: str):
    """查看某个 skill 的详情。参数：resource_type 可以是资源类型(document/ppt/mindmap/exercise/case/reading)或 action skill 名如 action:技能名，user_id用户ID"""
    from backend.src.service.skill_service import SkillService
    skill = await SkillService.get(user_id=int(user_id), resource_type=resource_type)
    if not skill:
        return f"'{resource_type}' 暂无自定义 skill"
    if skill["skill_type"] == "generation":
        return (
            f"【生成 Skill】\n"
            f"- 名称：{skill['name']}\n"
            f"- 资源类型：{skill['resource_type']}\n"
            f"- 提示词：{skill['system_prompt'][:500]}\n"
            f"- 更新时间：{skill['updated_at']}"
        )
    else:
        return (
            f"【动作 Skill】\n"
            f"- 名称：{skill['name']}\n"
            f"- 动作类型：{skill['action_type']}\n"
            f"- 配置：{skill['action_config']}\n"
            f"- 描述：{skill['tool_description']}\n"
            f"- 更新时间：{skill['updated_at']}"
        )


@tool
async def upsert_skill(resource_type: str, name: str, system_prompt: str, user_id: str):
    """创建或更新某个资源类型的生成 skill。参数：resource_type资源类型，name技能名称，system_prompt自定义提示词(支持 topic/portrait_context/kb_context 占位符)，user_id用户ID"""
    from backend.src.service.skill_service import SkillService
    try:
        result = await SkillService.upsert(
            user_id=int(user_id), resource_type=resource_type,
            name=name, system_prompt=system_prompt,
        )
        return f"生成 Skill '{result['resource_type']}' 已{ '更新' if result['action'] == 'updated' else '创建' }（名称：{result['name']}）"
    except ValueError as e:
        return str(e)


@tool
async def create_action_skill(
    name: str,
    action_type: str,
    action_config: str,
    tool_description: str,
    user_id: str,
):
    """创建一个可执行的动作 skill（如查天气、翻译等）。创建后 agent 获得对应的新工具。
    注意：必须使用真实可用的 API 地址，不知道就老实说需要用户提供，不准编造！
    参数：name 技能英文名(如check_weather)，action_type 动作类型(目前仅http)，
    action_config JSON格式的动作配置，包含 url(含{{参数名}}占位符)、method(GET/POST)、params(参数名映射描述)，
    tool_description 工具描述，告诉 LLM 何时及如何调用，
    user_id用户ID"""
    from backend.src.service.skill_service import SkillService
    try:
        config = json.loads(action_config)
    except json.JSONDecodeError:
        return "action_config 不是合法的 JSON，请修正后重试"
    try:
        result = await SkillService.upsert_action(
            user_id=int(user_id),
            name=name,
            action_type=action_type,
            action_config=config,
            tool_description=tool_description,
        )
        # 通知 UnifiedChat 实例刷新工具列表
        from backend.src.ai_core.brain import Brain  # deferred: circular brain<->skill
        Brain.rebuild_for_user(int(user_id))
        return f"动作 Skill '{result['name']}' 已{ '更新' if result['action'] == 'updated' else '创建' }，现在可以使用了！"
    except ValueError as e:
        return str(e)


@tool
async def list_skills(user_id: str):
    """列出当前用户的所有 skill（含生成 skill 和动作 skill）。参数：user_id用户ID"""
    from backend.src.service.skill_service import SkillService
    skills = await SkillService.list_all(user_id=int(user_id))
    if not skills:
        return "暂无自定义 skill，全部使用默认"
    lines = [f"当前共 {len(skills)} 个 skill："]
    for s in skills:
        if s["skill_type"] == "generation":
            lines.append(f"- [生成] {s['resource_type']}: {s['name']}（提示词长度：{s['prompt_length']}，更新于 {s['updated_at']}）")
        else:
            lines.append(f"- [动作] {s['name']} ({s['action_type']}) — {s.get('tool_description', '')[:60]}（更新于 {s['updated_at']}）")
    return "\n".join(lines)


@tool
async def delete_skill(resource_type: str, user_id: str):
    """删除某个 skill。参数：resource_type 可以是资源类型(document/ppt等)或 action:技能名，user_id用户ID"""
    from backend.src.service.skill_service import SkillService
    result = await SkillService.delete(user_id=int(user_id), resource_type=resource_type)
    if resource_type.startswith("action:"):
        from backend.src.ai_core.brain import Brain  # deferred: circular brain<->skill
        Brain.rebuild_for_user(int(user_id))
    return result
