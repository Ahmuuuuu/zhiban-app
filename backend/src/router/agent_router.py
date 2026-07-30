# -*- coding: utf-8 -*-
"""用户自建智能体 API"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import List, Optional

from backend.src.service.agent.service import (
    create, update, delete, get, list_by_user, list_public, copy,
    append_memory,
)
from backend.src.utils.jwt import get_user_id_from_token

router = APIRouter(prefix="/api/agents", tags=["用户智能体"])
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════
#  Request Schemas
# ═══════════════════════════════════════

class CreateAgentBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    persona: str = Field(default="")
    tools: List[str] = Field(default_factory=list)
    avatar: str = Field(default="")
    schedule: Optional[dict] = None


class UpdateAgentBody(BaseModel):
    name: Optional[str] = Field(default=None, max_length=64)
    persona: Optional[str] = None
    tools: Optional[List[str]] = None
    avatar: Optional[str] = None
    is_public: Optional[bool] = None
    enabled: Optional[bool] = None
    schedule: Optional[dict] = None


class AppendMemoryBody(BaseModel):
    entry: str = Field(..., min_length=1)


# ═══════════════════════════════════════
#  Endpoints — 静态路径必须在 /{agent_id} 之前
# ═══════════════════════════════════════

@router.post("")
async def create_agent(
    data: CreateAgentBody = Body(...),
    user_id: int = Depends(get_user_id_from_token),
):
    agent = await create(
        user_id=user_id, name=data.name, persona=data.persona,
        tools=data.tools, avatar=data.avatar, schedule=data.schedule,
    )
    return {"code": 200, "msg": "智能体创建成功", "data": agent}


@router.get("")
async def list_my_agents(user_id: int = Depends(get_user_id_from_token)):
    agents = await list_by_user(user_id)
    return {"code": 200, "data": agents}


@router.get("/tools")
async def list_available_tools():
    """返回所有可供智能体勾选的工具列表"""
    tools = [
        {"name": "search_knowledge_base", "label": "知识库检索", "desc": "从本地知识库中搜索资料"},
        {"name": "ingest_document", "label": "文档入库", "desc": "保存用户提供的学习资料到知识库"},
        {"name": "search_web_and_stage_knowledge", "label": "联网补库", "desc": "联网搜索并暂存资料到待审核区"},
        {"name": "list_knowledge", "label": "知识库列表", "desc": "查看知识库中的所有资料"},
        {"name": "update_knowledge", "label": "更新资料", "desc": "修改知识库中的资料"},
        {"name": "delete_knowledge", "label": "删除资料", "desc": "删除知识库中的私有资料"},
        {"name": "read_portrait", "label": "读取画像", "desc": "查看用户的学习画像和六维雷达"},
        {"name": "update_portrait", "label": "更新画像", "desc": "记录或更新用户的学习特征"},
        {"name": "get_used_history", "label": "历史记录", "desc": "查看当前对话组的历史消息"},
        {"name": "web_search", "label": "联网搜索", "desc": "通过搜索引擎查找公开资料"},
        {"name": "read_skill", "label": "查看Skill", "desc": "查看自定义生成提示词详情"},
        {"name": "upsert_skill", "label": "创建Skill", "desc": "创建或更新资源生成提示词模板"},
        {"name": "list_skills", "label": "Skill列表", "desc": "列出所有自定义技能"},
        {"name": "delete_skill", "label": "删除Skill", "desc": "删除某个自定义技能"},
        {"name": "create_action_skill", "label": "创建动作Skill", "desc": "创建可执行的HTTP工具"},
        {"name": "generate_learning_resource", "label": "生成学习资源", "desc": "生成文档、PPT、脑图等学习资料"},
        {"name": "generate_image", "label": "生成图片", "desc": "AI生成配图或插图"},
        {"name": "generate_exam_questions", "label": "生成习题", "desc": "生成练习题目"},
        {"name": "generate_slide_animation", "label": "生成幻灯片动画", "desc": "为PPT生成播放动画和旁白"},
        {"name": "search_online_video", "label": "搜索视频", "desc": "搜索在线视频教程"},
        {"name": "list_learning_paths", "label": "路径列表", "desc": "查看可用的学习路径"},
        {"name": "get_learning_path_detail", "label": "路径详情", "desc": "查看某条学习路径的节点详情"},
        {"name": "enroll_learning_path", "label": "加入路径", "desc": "将用户加入某条学习路径"},
        {"name": "regenerate_learning_path", "label": "重新规划路径", "desc": "根据当前画像重新生成学习路径"},
        {"name": "update_path_node", "label": "修改节点", "desc": "修改学习路径中的某个节点"},
        {"name": "add_path_node", "label": "添加节点", "desc": "向学习路径中插入新节点"},
        {"name": "delete_path_node", "label": "删除节点", "desc": "从学习路径中移除节点"},
    ]
    return {"code": 200, "data": tools}


@router.get("/market/public")
async def list_public_agents(user_id: int = Depends(get_user_id_from_token)):
    agents = await list_public(user_id)
    return {"code": 200, "data": agents}


@router.get("/chat/{chat_group_id}")
async def get_chat_agent(
    chat_group_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    """查询某个聊天组绑定的智能体（返回 null 表示默认小知）"""
    from backend.src.models.chat_history_model import ChatHistory
    record = await ChatHistory.filter(
        user_id=user_id, chat_group_id=chat_group_id
    ).order_by("-created_at").first()
    if not record or not record.agent_id:
        return {"code": 200, "data": None}
    agent = await get(user_id, record.agent_id)
    return {"code": 200, "data": agent}


# ═══════════════════════════════════════
#  /{agent_id} 必须在所有静态路径之后
# ═══════════════════════════════════════

@router.get("/{agent_id}")
async def get_agent(
    agent_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    agent = await get(user_id, agent_id)
    if not agent:
        raise HTTPException(404, "智能体不存在")
    return {"code": 200, "data": agent}


@router.put("/{agent_id}")
async def update_agent(
    agent_id: int,
    data: UpdateAgentBody = Body(...),
    user_id: int = Depends(get_user_id_from_token),
):
    kwargs = {k: v for k, v in data.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(400, "无更新字段")
    agent = await update(user_id, agent_id, **kwargs)
    if not agent:
        raise HTTPException(404, "智能体不存在")
    return {"code": 200, "msg": "智能体已更新", "data": agent}


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    ok = await delete(user_id, agent_id)
    if not ok:
        raise HTTPException(404, "智能体不存在")
    return {"code": 200, "msg": "智能体已删除"}


@router.post("/{agent_id}/copy")
async def copy_agent(
    agent_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    agent = await copy(user_id, agent_id)
    if not agent:
        raise HTTPException(404, "源智能体不存在或未公开")
    return {"code": 200, "msg": "智能体已复制到我的空间", "data": agent}


@router.post("/{agent_id}/memory")
async def add_memory(
    agent_id: int,
    data: AppendMemoryBody = Body(...),
    user_id: int = Depends(get_user_id_from_token),
):
    agent = await get(user_id, agent_id)
    if not agent:
        raise HTTPException(404, "智能体不存在")
    await append_memory(user_id, agent_id, data.entry)
    return {"code": 200, "msg": "记忆已追加"}
