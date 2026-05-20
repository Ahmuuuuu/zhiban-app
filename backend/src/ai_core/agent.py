import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

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
from backend.src.ai_core.tools.history import get_used_history
from backend.src.utils.prompt_loader import load_prompt
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory


class UnifiedChat:
    _instances: list["UnifiedChat"] = []

    def __init__(self, user_id: int, session_id: str = None):
        self.user_id = user_id
        self.session_id = session_id or f"unified_{user_id}"
        self.store = {}
        self._raw_executor = None
        self._action_tools_loaded = False
        self.agent_with_memory = self._build_agent(action_tools=[])
        UnifiedChat._instances.append(self)

    def _get_session_history(self, session_id: str):
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]

    # ── 动态工具工厂 ──

    @staticmethod
    def _make_http_tool(skill: dict):
        """将 HTTP 类型的 action skill 包装成 LangChain StructuredTool"""
        from pydantic import create_model, Field as PydanticField

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

        tools = [
            search_knowledge_base, ingest_document,
            list_knowledge, update_knowledge, delete_knowledge,
            read_portrait, update_portrait,
            get_used_history, web_search,
            read_skill, upsert_skill, list_skills, delete_skill,
            create_action_skill,
            generate_learning_resource,
            generate_image,
        ]
        tools.extend(action_tools)

        agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
        agent_executor = AgentExecutor(
            agent=agent, tools=tools,
            verbose=True, handle_parsing_errors=True, max_iterations=5,
        )
        self._raw_executor = agent_executor
        return RunnableWithMessageHistory(
            runnable=agent_executor,
            get_session_history=self._get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    async def _ensure_action_tools(self):
        """首次调用或 rebuild_for_user 后，异步加载 action tools 并重建 agent"""
        if self._action_tools_loaded:
            return
        action_tools = await self._load_action_tools_async()
        self.agent_with_memory = self._build_agent(action_tools)
        self._action_tools_loaded = True

    async def chat(self, message: str, resource_context: str = "") -> str:
        await self._ensure_action_tools()
        response = await self.agent_with_memory.ainvoke(
            {"input": message, "current_user_id": str(self.user_id), "resource_context": resource_context},
            config={"configurable": {"session_id": self.session_id}},
        )
        return response["output"]

    async def stream(self, message: str, resource_context: str = ""):
        """逐 token 流式输出 — yield dict: type=content"""
        await self._ensure_action_tools()

        history = self._get_session_history(self.session_id)
        history_messages = list(history.messages)

        full_response = ""

        try:
            async for event in self._raw_executor.astream_events(
                {
                    "input": message,
                    "history": history_messages,
                    "current_user_id": str(self.user_id),
                    "resource_context": resource_context,
                },
                version="v2",
            ):
                if event.get("event") == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", None)
                        if content:
                            full_response += content
                            yield {"type": "content", "content": content}
        except (TypeError, NotImplementedError):
            async for event in self._raw_executor.astream_events(
                {
                    "input": message,
                    "history": history_messages,
                    "current_user_id": str(self.user_id),
                    "resource_context": resource_context,
                },
                version="v1",
            ):
                if event.get("event") == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", None)
                        if content:
                            full_response += content
                            yield {"type": "content", "content": content}

        history.add_user_message(message)
        history.add_ai_message(full_response)
