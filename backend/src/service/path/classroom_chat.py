# -*- coding: utf-8 -*-
"""
互动课堂对话 — 复用 Brain 现成聊天逻辑（独立课堂组落 ChatHistory）

每用户懒创建一个"课堂小知" persona agent（工具白名单），课堂内容通过 path_context
注入，流式回复由前端 streamClassroomChatMessage 消费；完成后复用现有画像提取链路。
"""
import asyncio
import hashlib
import json
import logging
from collections import OrderedDict

from backend.src.ai_core.brain import Brain
from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User
from backend.src.models.user_agent_model import UserAgent
from backend.src.models.path_model import PathNode
from backend.src.service.agent.service import create as _agent_create
from backend.src.service.chat.service import (
    _build_portrait_context as _build_global_portrait_context,
    invalidate_portrait_cache,
)
from backend.src.service.portrait.service import extract_portrait_from_chat
from backend.src.service.path.classroom import _clip
from backend.src.service.path.generation_locks import get_node_generation_lock

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════
#  课堂小知 agent 定义
# ═══════════════════════════════════════

_CLASSROOM_AGENT_NAME = "课堂小知"

# 工具白名单：只留知识库 / 搜索 / 画像 / 记忆，剔除生成资源、出题、PPT、图片、动画、视频、路径与 skill 管理
_CLASSROOM_TOOLS = [
    "search_knowledge_base",
    "web_search",
    "read_portrait",
    "search_memory",
    "get_used_history",
]

_CLASSROOM_PERSONA = """你是知伴 App 里的"课堂小知"，一位专属于互动课堂的亲切助教。
## 你的角色
- 你正在陪用户上一节实时互动课。本节课内容、当前幕板书、讲解和提问，由系统放在下方【课堂上下文】里。
- 你的职责是围绕这节课做点评、追问、答疑，帮用户把当前知识点真正学会。
## 行为准则
- 学生做出选择、反讲或提问时，先针对他说的具体内容回应：哪里对、哪里含糊、下一步怎么补。
- 根据学生当前所处的幕（情景导入/核心讲解/随堂练习/费曼反讲）调整回应方式；小知此刻的具体职责见【课堂上下文】。
- 多用追问引导，少直接给完整答案；像课堂助教一样一步步把学生带明白。
- 学生答开放问题时：先点评是否抓住要点、哪里模糊，再引导补一步，不要直接替他把话讲完。
- 费曼反讲时：一次只追问一个薄弱点，先肯定再追问，引导他补例子或反例。
- 回答简洁、口语化、有温度，中文为主，一次说清一个点，不要一次倒太多。
- 使用 Markdown 排版，数学公式用 $...$，禁止输出 HTML 标签。
- 涉及位数、编码范围、公式、标准或历史事实时，先核对【课堂上下文】；上下文不足就调用知识库或搜索工具查证，不凭记忆补数值。要明确区分定义、例子和推论。
## 边界
- 不要主动推荐生成学习资料，不要出题，不要生成 PPT、图片、动画、视频。
- 不要改动学习路径或用户设置，不要管理技能。
- 只在学生明确问到相关知识时才调用知识库、搜索、画像或记忆工具查证，平时直接对话。"""

# 固定四幕：随堂练习展示题目，费曼反讲统一在右侧对话区完成
_SEGMENT_IDS = ("lead-in", "concept", "exercise", "feynman")
_SEGMENT_NAMES = {
    "lead-in": "情景导入",
    "concept": "核心讲解",
    "exercise": "随堂练习",
    "feynman": "费曼反讲",
}
_SEGMENT_ROLE_HINTS = {
    "lead-in": "学生刚进入本课，先引导建立问题意识、抓住本课要解决什么问题，不要急着深入细节。",
    "concept": "正在讲解核心概念，学生提问时对照板书拆解关键关系，分步讲清。",
    "exercise": "正在用一道题检查刚才的知识主线，先让学生独立判断，再围绕答案解释依据。",
    "feynman": "学生在费曼反讲（用自己的话讲知识点），你的任务是边听边追问：一次只挑一个漏洞，先肯定再追问，引导他补例子或反例，不要替他把内容讲完。",
}

# agent 缓存：user_id -> (agent_id, 定义 hash)（进程内）。
# 存 hash 是为了检测 persona/tools 定义变化（代码升级），避免已缓存用户继续用旧 persona。
_CLASSROOM_AGENT_IDS: dict[int, tuple[int, str]] = {}
_CLASSROOM_AGENT_GUARD = asyncio.Lock()


def _classroom_agent_definition_hash() -> str:
    """当前课堂小知定义的指纹：name/persona/tools 任一变化都会导致 hash 变化。"""
    blob = json.dumps(
        {
            "name": _CLASSROOM_AGENT_NAME,
            "persona": _CLASSROOM_PERSONA,
            "tools": _CLASSROOM_TOOLS,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.md5(blob.encode("utf-8")).hexdigest()[:16]


async def get_or_create_classroom_agent(user_id: int) -> int | None:
    """懒创建课堂小知 agent，进程内缓存 agent_id。返回 None 表示用户不存在。

    身份识别用 is_system 标记（用户无法伪造/编辑/删除），而不是 name 字符串；
    每次调用都会用定义 hash 快速校验 persona/tools 是否与当前代码一致，
    不一致时重置并触发 Brain.rebuild_for_user，让旧 persona 立即失效。
    """
    def_hash = _classroom_agent_definition_hash()
    cached = _CLASSROOM_AGENT_IDS.get(user_id)
    if cached is not None and cached[1] == def_hash:
        return cached[0]
    async with _CLASSROOM_AGENT_GUARD:
        cached = _CLASSROOM_AGENT_IDS.get(user_id)
        if cached is not None and cached[1] == def_hash:
            return cached[0]
        user = await User.filter(id=user_id).first()
        if not user:
            return None
        existing = await UserAgent.filter(user_id=user_id, is_system=True).first()
        expected_tools = json.dumps(list(_CLASSROOM_TOOLS), ensure_ascii=False)
        if existing and (
            existing.name != _CLASSROOM_AGENT_NAME
            or existing.persona != _CLASSROOM_PERSONA
            or existing.tools != expected_tools
        ):
            existing.name = _CLASSROOM_AGENT_NAME
            existing.persona = _CLASSROOM_PERSONA
            existing.tools = expected_tools
            await existing.save()
            # 重置该用户所有 Brain（含课堂实例）的工具/agent 配置缓存，新 persona 立即生效
            Brain.rebuild_for_user(user_id)
        if existing:
            _CLASSROOM_AGENT_IDS[user_id] = (existing.id, def_hash)
            return existing.id
        created = await _agent_create(
            user_id=user_id,
            name=_CLASSROOM_AGENT_NAME,
            persona=_CLASSROOM_PERSONA,
            tools=list(_CLASSROOM_TOOLS),
            is_system=True,
        )
        _CLASSROOM_AGENT_IDS[user_id] = (created["id"], def_hash)
        return created["id"]


# ═══════════════════════════════════════
#  Brain 实例缓存（课堂独立，不串历史）
# ═══════════════════════════════════════

_CLASSROOM_BRAINS: OrderedDict[str, Brain] = OrderedDict()
_CLASSROOM_BRAIN_LIMIT = 40


def _classroom_group_id(user_id: int, path_id: int, node_id: int) -> int:
    """合成稳定正数组号，仅用于 Brain 实例 key 与 get_used_history 注入，不落库。"""
    raw = (user_id * 1000003) ^ (path_id * 100003) ^ node_id
    return (raw % 2_000_000_000) + 1


def _get_classroom_brain(user_id: int, path_id: int, node_id: int, agent_id: int) -> Brain:
    key = f"classroom_{user_id}_{path_id}_{node_id}_{agent_id or 0}"
    if key in _CLASSROOM_BRAINS:
        _CLASSROOM_BRAINS.move_to_end(key)
        return _CLASSROOM_BRAINS[key]
    if len(_CLASSROOM_BRAINS) >= _CLASSROOM_BRAIN_LIMIT:
        _CLASSROOM_BRAINS.popitem(last=False)
    brain = Brain(
        user_id=user_id,
        chat_group_id=_classroom_group_id(user_id, path_id, node_id),
        agent_id=agent_id,
    )
    _CLASSROOM_BRAINS[key] = brain
    return brain


# ═══════════════════════════════════════
#  课堂上下文 / 用户提示词
# ═══════════════════════════════════════

async def _build_classroom_path_context(path_id: int, node_id: int, segment: dict) -> str:
    """从 DB 读节点 + 前端当前幕快照，拼出"【课堂上下文】"，走 persona 分支的 {path_context}。"""
    node = await PathNode.filter(id=node_id, path_id=path_id).first()
    topic = (node.topic if node else None) or _clip(segment.get("title")) or "当前知识点"
    question = segment.get("question") or {}
    seg_id = str(segment.get("id") or "")
    seg_idx = _SEGMENT_IDS.index(seg_id) + 1 if seg_id in _SEGMENT_IDS else None
    if seg_idx:
        lines = [
            "【课堂上下文】",
            f"当前课程：{_clip(topic, 80)}",
            f"当前幕（第 {seg_idx}/{len(_SEGMENT_IDS)} 幕·{_SEGMENT_NAMES[seg_id]}）：{_SEGMENT_ROLE_HINTS[seg_id]}",
            f"讲解要点：{_clip(segment.get('script') or segment.get('subtitle'), 500)}",
        ]
    else:
        lines = [
            "【课堂上下文】",
            f"当前课程：{_clip(topic, 80)}",
            f"当前幕：「{_clip(segment.get('title'))}」，类型：{_clip(segment.get('type'))}",
            f"讲解要点：{_clip(segment.get('script') or segment.get('subtitle'), 500)}",
        ]
    board = segment.get("board_items") or segment.get("points") or []
    if board:
        lines.append("板书：" + "、".join(_clip(str(b), 40) for b in board[:6]))
    if segment.get("example"):
        lines.append(f"例子：{_clip(segment['example'], 160)}")
    if question:
        lines.append(f"课堂提问：{_clip(question.get('prompt'), 120)}")
        options = question.get("options")
        if options:
            lines.append("选项：" + "、".join(str(o) for o in options[:4]))
    lines.append("以上是当前课堂正在讲的内容，请围绕它回应用户。")
    return "\n".join(lines)


def _compose_user_prompt(scenario: str, text: str, segment: dict) -> str:
    """把学生的反讲、开放回答或提问翻译成给模型的输入。"""
    text = str(text or "").strip()
    question = segment.get("question") or {}
    if scenario == "open":
        prompt = _clip(question.get("prompt"), 120) or "（课堂开放问题）"
        return (
            "【课堂追问】刚才讲完概念提了一个开放问题，学生用自己的话回答了：\n"
            f"问题：{prompt}\n"
            f"学生的回答：「{_clip(text, 800)}」\n"
            "请点评：是否抓住要点、哪里模糊、怎么补一步，再追问一句帮助他把概念压实；不要直接替他把话讲完。"
        )
    if scenario == "feynman":
        return (
            "【费曼反讲】学生用自己的话把这段讲给你听：\n"
            f"{_clip(text, 800)}\n"
            "请点评：哪里到位、哪里含糊或漏了关键关系，并引导他补一个例子或反例。"
        )
    return text or "……"


_FALLBACK_REPLIES = {
    "open": "你已经说到点子上了。再补一步：这个知识点和它解决的实际问题怎么对应，会更完整。",
    "feynman": "你的表达已经有雏形了。再补一句：它解决了什么问题、和前后知识点什么关系，会更完整。",
    "free": "可以继续往下想：试着把这个知识点套到一个具体的例子里，理解会更稳。",
}


# ═══════════════════════════════════════
#  SSE 流式生成器
# ═══════════════════════════════════════

async def stream_classroom_chat(
    user_id: int,
    path_id: int,
    node_id: int,
    segment: dict,
    scenario: str,
    text: str,
):
    """async generator：复用 Brain.stream 产出课堂对话 SSE 事件。"""
    fallback = _FALLBACK_REPLIES.get(scenario, _FALLBACK_REPLIES["free"])
    try:
        agent_id = await get_or_create_classroom_agent(user_id)
        if agent_id is None:
            yield _sse({"error": "用户不存在，无法进入课堂对话"})
            yield _sse(None, done=True)
            return

        lock = await get_node_generation_lock(user_id, path_id, node_id, "classroom_chat")
        async with lock:
            brain = _get_classroom_brain(user_id, path_id, node_id, agent_id)
            user_prompt = _compose_user_prompt(scenario, text, segment)
            path_ctx = await _build_classroom_path_context(path_id, node_id, segment)
            portrait_ctx = await _build_global_portrait_context(user_id)

            got_chunk = False
            full_response = ""
            async for event in brain.stream(
                user_prompt,
                path_context=path_ctx,
                portrait_context=portrait_ctx,
                memory_context="",
            ):
                if not isinstance(event, dict):
                    continue
                if event.get("type") in ("chunk", "content") and event.get("content"):
                    got_chunk = True
                    full_response += str(event["content"])
                yield _sse(event)

            if not got_chunk:
                full_response = fallback
                yield _sse({"role": "assistant", "type": "chunk", "content": full_response})

            # 课堂小知不使用普通聊天组的生成流程，但画像提取复用现有
            # extract_portrait_from_chat，因此把已完成的一轮写入同一个稳定课堂组。
            chat_group_id = _classroom_group_id(user_id, path_id, node_id)
            await ChatHistory.create(
                user_id=user_id,
                chat_group_id=chat_group_id,
                agent_id=agent_id,
                req=str(text or "").strip(),
                res=full_response,
            )
            asyncio.create_task(_refresh_portrait_after_classroom_chat(user_id, chat_group_id))
            yield _sse(None, done=True)
    except Exception:
        logger.exception("classroom chat failed user_id=%s path_id=%s node_id=%s", user_id, path_id, node_id)
        yield _sse({"error": "小知暂时走神了，稍后再问一次吧"})
        yield _sse(None, done=True)


async def _refresh_portrait_after_classroom_chat(user_id: int, chat_group_id: int) -> None:
    """课堂问答结束后复用普通聊天的画像提取链路，不阻塞 SSE 收尾。"""
    try:
        await extract_portrait_from_chat(user_id, chat_group_id)
    except Exception:
        logger.exception(
            "classroom portrait extraction failed user_id=%s chat_group_id=%s",
            user_id,
            chat_group_id,
        )
    finally:
        invalidate_portrait_cache(user_id)


def _sse(payload: dict | None, done: bool = False) -> str:
    """把事件包成 SSE 文本；done=True 时发结束事件 + [DONE]。"""
    if done:
        return "data: {\"role\":\"system\",\"type\":\"done\"}\n\ndata: [DONE]\n\n"
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
