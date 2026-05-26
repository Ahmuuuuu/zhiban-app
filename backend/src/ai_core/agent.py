import json
import logging

import httpx
from backend.src.ai_core.llm_config import llm
from backend.src.ai_core.tools.knowledge import (
    search_knowledge_base, ingest_document,
    list_knowledge, update_knowledge, delete_knowledge,
)
from backend.src.ai_core.tools.portrait import read_portrait, update_portrait
from backend.src.ai_core.tools.skill import (
    read_skill, upsert_skill, list_skills, delete_skill, create_action_skill,
)
from backend.src.ai_core.tools.resource import generate_learning_resource
from backend.src.ai_core.tools.search import web_search
from backend.src.ai_core.tools.image import generate_image
from backend.src.ai_core.tools.exam import generate_exam_questions
from backend.src.ai_core.tools.path import (
    list_learning_paths, get_learning_path_detail, enroll_learning_path,
    regenerate_learning_path, update_path_node, add_path_node, delete_path_node,
)
from backend.src.ai_core.tools.history import get_used_history
from backend.src.utils.prompt_loader import load_prompt
from pydantic import create_model, Field as PydanticField
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
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


class UnifiedChat:
    _instances: list["UnifiedChat"] = []

    def __init__(self, user_id: int, session_id: str | None = None):
        self.user_id = user_id
        self.session_id = session_id or f"unified_{user_id}"
        self._raw_executor = None
        self._action_tools_loaded = False
        self._history: list = []
        UnifiedChat._instances.append(self)

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
            timeout = httpx.Timeout(15.0)
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
                fields[pname] = (str, PydanticField(description=pdesc))
            args_schema = create_model(f"{safe_name}_input", **fields)

        return StructuredTool.from_function(
            coroutine=_handler,
            name=safe_name,
            description=skill.get("tool_description", "") or f"自定义技能: {skill['name']}",
            args_schema=args_schema,
        )

    async def _load_action_tools_async(self):
        """在正确的 async 上下文中从 DB 加载 action skill"""
        from backend.src.service.skill_service import SkillService
        skills = await SkillService.list_actions(user_id=self.user_id)
        return [self._make_http_tool(s) for s in skills if s["action_type"] == "http"]

    # ── 热刷新 ──

    @classmethod
    def rebuild_for_user(cls, user_id: int):
        """创建/删除 action skill 后标记需要刷新，下次对话时自动重建"""
        for inst in cls._instances:
            if inst.user_id == user_id:
                inst._action_tools_loaded = False

    def _build_agent(self, action_tools: list):
        system_prompt = load_prompt("chat/unified")

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        uid = str(self.user_id)
        tools = [
            _inject_user_id(search_knowledge_base, uid),
            _inject_user_id(ingest_document, uid),
            _inject_user_id(list_knowledge, uid),
            _inject_user_id(update_knowledge, uid),
            _inject_user_id(delete_knowledge, uid),
            _inject_user_id(read_portrait, uid),
            _inject_user_id(update_portrait, uid),
            _inject_user_id(get_used_history, uid),
            web_search,
            _inject_user_id(read_skill, uid),
            _inject_user_id(upsert_skill, uid),
            _inject_user_id(list_skills, uid),
            _inject_user_id(delete_skill, uid),
            _inject_user_id(create_action_skill, uid),
            _inject_user_id(generate_learning_resource, uid),
            _inject_user_id(generate_image, uid),
            _inject_user_id(generate_exam_questions, uid),
            _inject_user_id(list_learning_paths, uid),
            _inject_user_id(get_learning_path_detail, uid),
            _inject_user_id(enroll_learning_path, uid),
            _inject_user_id(regenerate_learning_path, uid),
            _inject_user_id(update_path_node, uid),
            _inject_user_id(add_path_node, uid),
            _inject_user_id(delete_path_node, uid),
        ]
        tools.extend(_inject_user_id(t, uid) for t in action_tools)

        agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
        self._raw_executor = AgentExecutor(
            agent=agent, tools=tools,
            verbose=True, handle_parsing_errors=True, max_iterations=5,
        )

    async def _ensure_action_tools(self):
        """首次调用或 rebuild_for_user 后，异步加载 action tools 并重建 agent"""
        if self._action_tools_loaded:
            return
        try:
            action_tools = await self._load_action_tools_async()
        except Exception:
            logging.getLogger(__name__).exception("加载 action tools 失败")
            action_tools = []
        self._build_agent(action_tools)
        self._action_tools_loaded = True

    async def chat(self, message: str, resource_context: str = "", path_context: str = "", portrait_context: str = "") -> str:
        await self._ensure_action_tools()
        response = await self._raw_executor.ainvoke({
            "input": message,
            "history": list(self._history),
            "current_user_id": str(self.user_id),
            "resource_context": resource_context,
            "path_context": path_context,
            "portrait_context": portrait_context,
        })
        self._history.append(HumanMessage(content=message))
        self._history.append(AIMessage(content=response["output"]))
        return response["output"]

    async def stream(self, message: str, resource_context: str = "", path_context: str = "", portrait_context: str = ""):
        """逐 token 流式输出 — 包含工具调用事件"""
        await self._ensure_action_tools()

        full_response = ""

        try:
            async for event in self._raw_executor.astream_events(
                {
                    "input": message,
                    "history": list(self._history),
                    "current_user_id": str(self.user_id),
                    "resource_context": resource_context,
                    "path_context": path_context,
                    "portrait_context": portrait_context,
                },
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    yield {"role": "tool", "type": "tool_start", "tool": tool_name}

                elif kind == "on_tool_end":
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
            async for event in self._raw_executor.astream_events(
                {
                    "input": message,
                    "history": list(self._history),
                    "current_user_id": str(self.user_id),
                    "resource_context": resource_context,
                    "path_context": path_context,
                    "portrait_context": portrait_context,
                },
                version="v1",
            ):
                kind = event.get("event", "")

                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    yield {"role": "tool", "type": "tool_start", "tool": tool_name}

                elif kind == "on_tool_end":
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
