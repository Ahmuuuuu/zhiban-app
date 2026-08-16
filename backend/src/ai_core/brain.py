# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import weakref
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from backend.src.ai_core.llm_config import llm
from backend.src.ai_core.tools.knowledge import (
    search_knowledge_base, ingest_document,
    search_web_and_stage_knowledge,
    list_knowledge, update_knowledge, delete_knowledge,
)
from backend.src.ai_core.tools.portrait import read_portrait, update_portrait
from backend.src.ai_core.tools.skill import (
    read_skill, upsert_skill, list_skills, delete_skill, create_action_skill,
)
from backend.src.ai_core.tools.resource import generate_learning_resource
from backend.src.ai_core.tools.search import web_search
from backend.src.ai_core.tools.mcp_external import load_external_mcp_tools
from backend.src.ai_core.tools.image import generate_image
from backend.src.ai_core.tools.exam import generate_exam_questions
from backend.src.ai_core.tools.path import (
    list_learning_paths, get_learning_path_detail, enroll_learning_path,
    regenerate_learning_path, update_path_node, add_path_node, delete_path_node,
)
from backend.src.ai_core.tools.animation import generate_slide_animation
from backend.src.ai_core.tools.video_search import search_online_video
from backend.src.ai_core.tools.history import get_used_history
from backend.src.ai_core.tools.memory import search_memory
from backend.src.utils.prompt_loader import load_prompt
from pydantic import create_model, Field as PydanticField
try:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
except ModuleNotFoundError:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage


def _inject_user_id(tool, user_id: str):
    """拷贝一个 tool，移除 user_id 参数并自动注入当前用户 ID"""
    original_coro = tool.coroutine
    if tool.args_schema:
        fields = {}
        for name, field_info in tool.args_schema.model_fields.items():
            if name != "user_id":
                fields[name] = (field_info.annotation, field_info)
        new_schema = create_model(f"{tool.name}_input", **fields) if fields else None
    else:
        new_schema = None

    desc = (tool.description or "").replace("user_id用户数字ID", "")
    desc = desc.replace("，，", "，").replace("，。", "。").replace("参数：，", "参数：").strip()

    async def _scoped(**kwargs):
        kwargs["user_id"] = user_id
        return await original_coro(**kwargs)

    _scoped.__name__ = tool.name
    return StructuredTool.from_function(
        coroutine=_scoped,
        name=tool.name,
        description=desc,
        args_schema=new_schema,
    )


def _inject_chat_group_id(tool, chat_group_id: int):
    """为 get_used_history 注入当前聊天组 ID"""
    original_coro = tool.coroutine
    if tool.args_schema:
        fields = {}
        for name, field_info in tool.args_schema.model_fields.items():
            if name not in ("chat_group_id",):
                fields[name] = (field_info.annotation, field_info)
        new_schema = create_model(f"{tool.name}_scoped_input", **fields) if fields else None
    else:
        new_schema = None

    async def _scoped(**kwargs):
        kwargs["chat_group_id"] = chat_group_id
        return await original_coro(**kwargs)

    _scoped.__name__ = tool.name
    return StructuredTool.from_function(
        coroutine=_scoped,
        name=tool.name,
        description=(tool.description or ""),
        args_schema=new_schema,
    )


_MAX_HISTORY_TURNS = 20

# ── 消息分类：按需加载工具行为指南 ──

_CREATE_TRIGGERS = [
    "生成学习", "生成资料", "生成文档", "做个PPT", "做PPT", "生成PPT",
    "整理成文档", "整理成PPT", "做成文档", "做成PPT",
    "生成思维导图", "生成脑图", "做思维导图", "做脑图",
    "帮我整理", "帮我总结", "帮我生成",
    "出题", "出几道", "出一些题", "练习题", "测验", "考试模拟",
    "做几道题", "来几道题", "做题", "习题", "试卷",
    "画一张", "画个", "生成图片", "生成一张图", "配图", "插图",
    "帮我画", "帮我生成图",
    "生成动画", "播放PPT", "演示PPT", "旁白", "念给我听",
    "搜视频", "找视频", "视频教程",
]

_MANAGE_TRIGGERS = [
    "学习路径", "课程路径", "学习计划", "选课", "有哪些路径",
    "加入路径", "路径管理", "修改节点", "添加节点", "删除节点",
    "重新规划路径", "路径不合适", "路径查看",
    "skill", "Skill", "自定义提示词", "修改提示词", "设置提示词",
    "恢复默认", "升级生成", "删除skill", "创建skill",
    "动作skill", "action skill", "添加能力", "添加工具",
]


def _classify_message(message: str) -> set[str]:
    """根据用户消息判断需要加载哪些工具行为指南"""
    cats = set()
    for t in _CREATE_TRIGGERS:
        if t in message:
            cats.add("create")
            break
    for t in _MANAGE_TRIGGERS:
        if t in message:
            cats.add("manage")
            break
    return cats


# ── 工具注册表：工具名 → 工厂函数(uid, gid) → 已注入的 LangChain Tool ──
TOOL_REGISTRY: dict[str, callable] = {
    "search_knowledge_base":      lambda uid, gid: _inject_user_id(search_knowledge_base, uid),
    "ingest_document":             lambda uid, gid: _inject_user_id(ingest_document, uid),
    "search_web_and_stage_knowledge": lambda uid, gid: _inject_user_id(search_web_and_stage_knowledge, uid),
    "list_knowledge":              lambda uid, gid: _inject_user_id(list_knowledge, uid),
    "update_knowledge":            lambda uid, gid: _inject_user_id(update_knowledge, uid),
    "delete_knowledge":            lambda uid, gid: _inject_user_id(delete_knowledge, uid),
    "read_portrait":               lambda uid, gid: _inject_user_id(read_portrait, uid),
    "update_portrait":             lambda uid, gid: _inject_user_id(update_portrait, uid),
    "get_used_history":            lambda uid, gid: _inject_chat_group_id(_inject_user_id(get_used_history, uid), gid),
    "search_memory":               lambda uid, gid: _inject_user_id(search_memory, uid),
    "web_search":                  lambda uid, gid: web_search,
    "read_skill":                  lambda uid, gid: _inject_user_id(read_skill, uid),
    "upsert_skill":                lambda uid, gid: _inject_user_id(upsert_skill, uid),
    "list_skills":                 lambda uid, gid: _inject_user_id(list_skills, uid),
    "delete_skill":                lambda uid, gid: _inject_user_id(delete_skill, uid),
    "create_action_skill":         lambda uid, gid: _inject_user_id(create_action_skill, uid),
    "generate_learning_resource":  lambda uid, gid: _inject_chat_group_id(_inject_user_id(generate_learning_resource, uid), gid),
    "generate_image":              lambda uid, gid: _inject_chat_group_id(_inject_user_id(generate_image, uid), gid),
    "generate_exam_questions":     lambda uid, gid: _inject_chat_group_id(_inject_user_id(generate_exam_questions, uid), gid),
    "generate_slide_animation":    lambda uid, gid: _inject_chat_group_id(_inject_user_id(generate_slide_animation, uid), gid),
    "search_online_video":         lambda uid, gid: _inject_chat_group_id(_inject_user_id(search_online_video, uid), gid),
    "list_learning_paths":         lambda uid, gid: _inject_user_id(list_learning_paths, uid),
    "get_learning_path_detail":    lambda uid, gid: _inject_user_id(get_learning_path_detail, uid),
    "enroll_learning_path":        lambda uid, gid: _inject_user_id(enroll_learning_path, uid),
    "regenerate_learning_path":    lambda uid, gid: _inject_user_id(regenerate_learning_path, uid),
    "update_path_node":            lambda uid, gid: _inject_user_id(update_path_node, uid),
    "add_path_node":               lambda uid, gid: _inject_user_id(add_path_node, uid),
    "delete_path_node":            lambda uid, gid: _inject_user_id(delete_path_node, uid),
}


class Brain:
    _instances: weakref.WeakSet = weakref.WeakSet()

    def __init__(self, user_id: int, chat_group_id: int | None = None,
                 session_id: str | None = None, agent_id: int | None = None):
        self.user_id = user_id
        self.chat_group_id = chat_group_id
        self.session_id = session_id or f"brain_{user_id}"
        self.agent_id = agent_id
        self._agent_persona: str | None = None
        self._agent_tool_names: set[str] | None = None
        self._agent_memory_text: str = ""
        self._raw_executor = None
        self._action_tools_loaded = False
        self._agent_config_loaded = False
        self._history: list = []
        self._history_hydrated = False   # 是否已从 DB 水合最近 N 轮（幂等）
        Brain._instances.add(self)

    # ── 记忆水合 ──

    async def hydrate_history(self, before_id: int | None = None):
        """冷启动时从 DB 水合最近 N 轮历史（幂等）。

        配合多级记忆系统：跨会话恢复短期记忆。before_id 用于截止（如当前
        消息 id），避免把正在处理的这一轮当成历史重放。
        """
        if self._history_hydrated:
            return
        self._history_hydrated = True
        try:
            from backend.src.models.chat_history_model import ChatHistory
            qs = ChatHistory.filter(
                user_id=self.user_id, chat_group_id=self.chat_group_id or 0
            )
            if before_id:
                qs = qs.filter(id__lt=before_id)
            records = await qs.order_by("-id").limit(_MAX_HISTORY_TURNS).all()
            for r in reversed(records):
                if r.req:
                    self._history.append(HumanMessage(content=r.req))
                if r.res:
                    self._history.append(AIMessage(content=r.res))
        except Exception:
            logging.getLogger(__name__).exception("水合历史失败 user_id=%s", self.user_id)

    # ── 动态工具工厂 ──

    @staticmethod
    def _make_http_tool(skill: dict):
        """将 HTTP 类型的 action skill 包装成 LangChain StructuredTool"""
        config = json.loads(skill["action_config"]) if isinstance(skill["action_config"], str) else skill["action_config"]
        safe_name = skill["name"].replace("-", "_").replace(" ", "_")

        async def _handler(**kwargs):
            url = config["url"]
            for k, v in kwargs.items():
                url = url.replace(f"{{{{{k}}}}}", str(v))
            timeout = httpx.Timeout(30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                method = config.get("method", "GET").upper()
                resp = await client.request(method, url)
                text = resp.text[:3000]
                if resp.status_code >= 400:
                    return f"请求失败 (HTTP {resp.status_code}): {text}"
                return text

        _handler.__name__ = safe_name

        params_schema = config.get("params", {})
        args_schema = None
        if params_schema:
            fields = {}
            for pname, pdesc in params_schema.items():
                if isinstance(pdesc, dict):
                    desc = str(pdesc.get("description") or pdesc.get("desc") or "")
                else:
                    desc = str(pdesc or "")
                fields[pname] = (str, PydanticField(description=desc))
            args_schema = create_model(f"{safe_name}_input", **fields)

        return StructuredTool.from_function(
            coroutine=_handler,
            name=safe_name,
            description=skill.get("tool_description", "") or f"自定义技能: {skill['name']}",
            args_schema=args_schema,
        )

    async def _load_action_tools_async(self):
        """在正确的 async 上下文中从 DB 加载 action skill"""
        from backend.src.service.skill import service as skill_service
        skills = await skill_service.list_actions(user_id=self.user_id)
        tools = []
        for s in skills:
            if s.get("action_type") != "http":
                continue
            try:
                tools.append(self._make_http_tool(s))
            except Exception:
                logging.getLogger(__name__).exception("action skill 构造失败，已跳过: %s", s.get("name"))
        return tools

    # ── 热刷新 ──

    @classmethod
    def rebuild_for_user(cls, user_id: int):
        """创建/删除 action skill 后标记需要刷新，下次对话时自动重建"""
        for inst in cls._instances:
            if inst.user_id == user_id:
                inst._action_tools_loaded = False
                inst._agent_config_loaded = False

    async def _load_agent_config(self):
        """Load user-defined agent config: persona, tool whitelist, memory.
        Only runs once when agent_id is set and not yet loaded."""
        if self.agent_id is None or self._agent_config_loaded:
            return
        try:
            from backend.src.service.agent.service import get as get_agent, get_memory_text
            agent_config = await get_agent(self.user_id, self.agent_id)
            if agent_config:
                self._agent_persona = agent_config.get("persona", "") or None
                tool_names = agent_config.get("tools", [])
                self._agent_tool_names = set(tool_names) if tool_names else None
                self._agent_memory_text = await get_memory_text(self.user_id, self.agent_id)
        except Exception:
            logging.getLogger(__name__).exception("加载智能体配置失败 agent_id=%s", self.agent_id)
            self._agent_persona = None
            self._agent_tool_names = None
            self._agent_memory_text = ""
        self._agent_config_loaded = True

    def _build_agent(self, action_tools: list, mcp_tools: list):
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        tz_name = "Asia/Shanghai"
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        current_time_context = (
            f"\n\n### Current Time Anchor\n"
            f"- Date: {date_str}\n"
            f"- Time: {time_str}\n"
            f"- Timezone: {tz_name}\n"
            f"- Always use this date as reference for time-sensitive queries.\n"
        )

        if self._agent_persona:
            system_prompt = (
                self._agent_persona
                + current_time_context
                + (("\n" + self._agent_memory_text) if self._agent_memory_text else "")
                + "\n\n{path_context}\n\n{portrait_context}\n\n{memory_context}"
                + "\n\n## Output Rules\n"
                + "- Use Markdown for formatting, NOT raw HTML tags.\n"
                + "- Wrap inline math in $...$ and display math in $$...$$.\n"
                + "- Never output <br>, <div>, <span> or other HTML tags.\n"
            )
        else:
            system_prompt = load_prompt("chat/unified") + current_time_context

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        uid = str(self.user_id)
        gid = self.chat_group_id or 0

        if self._agent_tool_names is not None:
            tool_names_to_load = self._agent_tool_names
        else:
            tool_names_to_load = set(TOOL_REGISTRY.keys())

        tools = []
        for name in tool_names_to_load:
            factory = TOOL_REGISTRY.get(name)
            if factory:
                tools.append(factory(uid, gid))

        tools.extend(_inject_user_id(t, uid) for t in action_tools)
        tools.extend(mcp_tools)

        agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
        max_iters = max(8, len(tools) * 2)
        self._raw_executor = AgentExecutor(
            agent=agent, tools=tools,
            verbose=True, handle_parsing_errors=True, max_iterations=max_iters,
        )

    def _load_tool_guides(self, message: str) -> str:
        """根据消息内容按需加载工具行为指南；未命中则返回空字符串"""
        cats = _classify_message(message)
        parts: list[str] = []
        if "create" in cats:
            parts.append(load_prompt("chat/guide_create"))
        if "manage" in cats:
            parts.append(load_prompt("chat/guide_manage"))
        return "\n".join(parts)

    async def _ensure_action_tools(self):
        """首次调用或 rebuild_for_user 后，异步加载 agent 配置、action tools 并重建 agent"""
        if self._action_tools_loaded:
            return
        await self._load_agent_config()
        try:
            action_tools = await self._load_action_tools_async()
        except Exception:
            logging.getLogger(__name__).exception("加载 action tools 失败")
            action_tools = []
        try:
            mcp_tools = await load_external_mcp_tools()
        except Exception:
            logging.getLogger(__name__).exception('Failed to load MCP tools')
            mcp_tools = []
        self._build_agent(action_tools, mcp_tools)
        self._action_tools_loaded = True

    async def chat(self, message: str, resource_context: str = "", path_context: str = "", portrait_context: str = "", memory_context: str = "") -> str:
        await self._ensure_action_tools()
        tool_guides = self._load_tool_guides(message)
        response = await self._raw_executor.ainvoke({
            "input": message,
            "history": list(self._history),
            "current_user_id": str(self.user_id),
            "resource_context": resource_context,
            "path_context": path_context,
            "portrait_context": portrait_context,
            "memory_context": memory_context,
            "tool_guides": tool_guides,
        })
        self._history.append(HumanMessage(content=message))
        self._history.append(AIMessage(content=response["output"]))
        if len(self._history) > _MAX_HISTORY_TURNS * 2:
            self._history = self._history[-_MAX_HISTORY_TURNS * 2:]
        return response["output"]

    async def stream(self, message: str, resource_context: str = "", path_context: str = "", portrait_context: str = "", memory_context: str = ""):
        """逐 token 流式输出 — 包含工具调用事件，工具执行期间自动心跳保活"""
        await self._ensure_action_tools()

        full_response = ""
        tool_running = False
        tool_guides = self._load_tool_guides(message)

        async def _stream_events(version: str):
            nonlocal tool_running
            agen = self._raw_executor.astream_events(
                {
                    "input": message,
                    "history": list(self._history),
                    "current_user_id": str(self.user_id),
                    "resource_context": resource_context,
                    "path_context": path_context,
                    "portrait_context": portrait_context,
                    "memory_context": memory_context,
                    "tool_guides": tool_guides,
                },
                version=version,
            )
            while True:
                try:
                    event = await asyncio.wait_for(agen.__anext__(), timeout=30 if tool_running else 120)
                except asyncio.TimeoutError:
                    yield {"type": "keepalive"}
                    continue
                except StopAsyncIteration:
                    break
                yield event

        try:
            async for event in _stream_events("v2"):
                kind = event.get("event", "")

                if kind == "on_tool_start":
                    tool_running = True
                    tool_name = event.get("name", "")
                    yield {"role": "tool", "type": "tool_start", "tool": tool_name}

                elif kind == "on_tool_end":
                    tool_running = False
                    tool_name = event.get("name", "")
                    tool_output = event.get("data", {}).get("output", "")
                    if isinstance(tool_output, str) and len(tool_output) > 500:
                        tool_output = tool_output[:500] + "..."
                    yield {"role": "tool", "type": "tool_end", "tool": tool_name, "output": str(tool_output)}

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", None)
                        if content:
                            full_response += content
                            yield {"role": "assistant", "type": "chunk", "content": content}
        except (TypeError, NotImplementedError):
            async for event in _stream_events("v1"):
                kind = event.get("event", "")

                if kind == "on_tool_start":
                    tool_running = True
                    tool_name = event.get("name", "")
                    yield {"role": "tool", "type": "tool_start", "tool": tool_name}

                elif kind == "on_tool_end":
                    tool_running = False
                    tool_name = event.get("name", "")
                    tool_output = event.get("data", {}).get("output", "")
                    if isinstance(tool_output, str) and len(tool_output) > 500:
                        tool_output = tool_output[:500] + "..."
                    yield {"role": "tool", "type": "tool_end", "tool": tool_name, "output": str(tool_output)}

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", None)
                        if content:
                            full_response += content
                            yield {"role": "assistant", "type": "chunk", "content": content}

        self._history.append(HumanMessage(content=message))
        self._history.append(AIMessage(content=full_response))
        if len(self._history) > _MAX_HISTORY_TURNS * 2:
            self._history = self._history[-_MAX_HISTORY_TURNS * 2:]
