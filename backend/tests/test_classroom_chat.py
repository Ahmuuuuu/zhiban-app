# -*- coding: utf-8 -*-
"""
classroom_chat 课堂对话服务测试

测试目标：backend/src/service/path/classroom_chat.py
覆盖：prompt 组装、课堂上下文、agent 懒创建缓存、SSE 事件序列、异常兜底。
所有 DB / Brain / LLM 依赖用 monkeypatch 模拟，不碰真实数据库和 LLM。
"""
import pytest

from backend.src.service.path import classroom_chat as cg_chat
from backend.src.service.chat import service as chat_service


# ── 测试替身 ──

class FakeNode:
    topic = "BCD与ASCII编码"


class FakeQuerySet:
    def __init__(self, item=None):
        self._item = item

    async def first(self):
        return self._item


class FakeUser:
    id = 1


class StubBrain:
    def __init__(self, events, raise_error=False):
        self._events = events
        self._raise_error = raise_error
        self.hydrated_before_ids = []

    async def hydrate_history(self, before_id=None):
        self.hydrated_before_ids.append(before_id)

    async def stream(self, user_prompt, path_context="", portrait_context="", memory_context=""):
        if self._raise_error:
            raise RuntimeError("brain boom")
        for ev in self._events:
            yield ev


async def _collect(generator):
    return [chunk async for chunk in generator]


@pytest.fixture(autouse=True)
def _stub_classroom_chat_persistence(monkeypatch):
    """课堂流测试不连接真实 MySQL，同时保留对话落库行为的可观察性。"""
    records = []

    class FakeRecord:
        id = 88

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.saved = False

        async def save(self):
            self.saved = True

    async def fake_create(**kwargs):
        records.append(kwargs)
        return FakeRecord(**kwargs)

    scheduled = []

    def fake_schedule(*args, **kwargs):
        scheduled.append((args, kwargs))

    monkeypatch.setattr(cg_chat.ChatHistory, "create", fake_create)
    monkeypatch.setattr(cg_chat, "schedule_post_chat_enrichment", fake_schedule)
    return records, scheduled


# ── _compose_user_prompt ──

def test_compose_user_prompt_open():
    segment = {"question": {"prompt": "用你自己的话说说补码为什么能把减法变加法？"}}
    prompt = cg_chat._compose_user_prompt("open", "因为补码取反加一", segment)
    assert "课堂追问" in prompt
    assert "用你自己的话说说补码为什么能把减法变加法" in prompt
    assert "因为补码取反加一" in prompt


def test_compose_user_prompt_feynman():
    prompt = cg_chat._compose_user_prompt("feynman", "我觉得补码能把减法变成加法", {})
    assert "费曼反讲" in prompt
    assert "我觉得补码能把减法变成加法" in prompt


def test_compose_user_prompt_free():
    assert cg_chat._compose_user_prompt("free", "为什么补码能统一加减？", {}) == "为什么补码能统一加减？"


# ── _build_classroom_path_context ──

@pytest.mark.asyncio
async def test_build_classroom_path_context(monkeypatch):
    monkeypatch.setattr(cg_chat.PathNode, "filter", lambda *a, **k: FakeQuerySet(FakeNode()))
    segment = {
        "title": "补码",
        "type": "concept",
        "script": "补码把减法转换为加法",
        "board_items": ["补码等于反码加一", "统一加减运算"],
        "example": "-5 的补码是 11111011",
        "question": {"prompt": "补码为什么能省减法电路？", "options": ["A", "B"]},
    }
    ctx = await cg_chat._build_classroom_path_context(1, 1, segment)
    assert "BCD与ASCII编码" in ctx          # 从 DB 节点 topic
    assert "补码" in ctx                     # 当前幕
    assert "补码把减法转换为加法" in ctx     # 讲解要点
    assert "补码等于反码加一" in ctx         # 板书
    assert "-5 的补码是 11111011" in ctx     # 例子
    assert "补码为什么能省减法电路" in ctx   # 课堂提问


@pytest.mark.asyncio
async def test_build_classroom_path_context_knows_segment_position(monkeypatch):
    # 小知必须知道学生在哪一幕（费曼反讲）以及自己此刻的职责
    monkeypatch.setattr(cg_chat.PathNode, "filter", lambda *a, **k: FakeQuerySet(FakeNode()))
    segment = {"id": "feynman", "title": "费曼反讲", "type": "feynman", "script": "讲给小知听"}
    ctx = await cg_chat._build_classroom_path_context(1, 1, segment)
    assert "第 4/4 幕" in ctx
    assert "费曼反讲" in ctx
    assert "挑一个漏洞" in ctx
    assert "不要替他把内容讲完" in ctx


@pytest.mark.asyncio
async def test_build_classroom_path_context_empty_node(monkeypatch):
    # 节点查不到时退化为 segment.title
    monkeypatch.setattr(cg_chat.PathNode, "filter", lambda *a, **k: FakeQuerySet(None))
    ctx = await cg_chat._build_classroom_path_context(1, 1, {"title": "数制", "script": "基数决定可用数字"})
    assert "数制" in ctx


# ── get_or_create_classroom_agent 缓存幂等 ──

@pytest.mark.asyncio
async def test_get_or_create_classroom_agent_cached(monkeypatch):
    cg_chat._CLASSROOM_AGENT_IDS.clear()
    monkeypatch.setattr(cg_chat.User, "filter", lambda *a, **k: FakeQuerySet(FakeUser()))
    monkeypatch.setattr(cg_chat.UserAgent, "filter", lambda *a, **k: FakeQuerySet(None))  # 不存在 → 走 create
    created = {"id": 123}
    calls = {"n": 0}

    async def fake_create(user_id, name, persona, tools, **kwargs):
        calls["n"] += 1
        return created

    monkeypatch.setattr(cg_chat, "_agent_create", fake_create)

    first = await cg_chat.get_or_create_classroom_agent(1)
    second = await cg_chat.get_or_create_classroom_agent(1)
    assert first == 123 and second == 123
    assert calls["n"] == 1, "create 应只调用一次（第二次命中缓存）"


@pytest.mark.asyncio
async def test_get_or_create_classroom_agent_missing_user(monkeypatch):
    cg_chat._CLASSROOM_AGENT_IDS.clear()
    monkeypatch.setattr(cg_chat.User, "filter", lambda *a, **k: FakeQuerySet(None))
    assert await cg_chat.get_or_create_classroom_agent(999) is None


# ── stream_classroom_chat 事件序列 ──

@pytest.mark.asyncio
async def test_stream_classroom_chat_events(monkeypatch, _stub_classroom_chat_persistence):
    monkeypatch.setattr(cg_chat, "get_or_create_classroom_agent", _async_value(123))
    brain = StubBrain([
        {"role": "assistant", "type": "chunk", "content": "你理解对了，"},
        {"role": "assistant", "type": "chunk", "content": "再补一个例子更稳。"},
    ])
    monkeypatch.setattr(cg_chat, "_get_classroom_brain", lambda *a, **k: brain)
    monkeypatch.setattr(cg_chat, "_build_classroom_path_context", _async_value("【课堂上下文】补码"))
    monkeypatch.setattr(cg_chat, "_build_global_portrait_context", _async_value("计算机专业"))

    events = await _collect(cg_chat.stream_classroom_chat(1, 1, 1, {}, "free", "为什么补码能统一加减？"))
    joined = "\n".join(events)
    assert "你理解对了" in joined
    assert "再补一个例子更稳" in joined
    assert '"type":"done"' in joined
    assert "[DONE]" in joined
    records, scheduled = _stub_classroom_chat_persistence
    assert records == [{
        "user_id": 1,
        "chat_group_id": cg_chat._classroom_group_id(1, 1, 1),
        "agent_id": 123,
        "req": "为什么补码能统一加减？",
        "res": "",
    }]
    assert brain.hydrated_before_ids == [88]
    assert scheduled == [
        ((1, cg_chat._classroom_group_id(1, 1, 1), 123), {
            "portrait_minimum_records": 1,
            "persist_memory": False,
        })
    ]


@pytest.mark.asyncio
async def test_classroom_portrait_enrichment_accepts_one_complete_turn(monkeypatch):
    """课堂每个节点独立成组，一问一答也必须能进入同一画像提取器。"""
    calls = []

    async def fake_extract(user_id, chat_group_id, *, minimum_records=2):
        calls.append((user_id, chat_group_id, minimum_records))

    monkeypatch.setattr(chat_service, "extract_portrait_from_chat", fake_extract)
    monkeypatch.setattr(chat_service, "invalidate_portrait_cache", lambda user_id: None)

    await chat_service._extract_portrait_and_refresh(1, 321, portrait_minimum_records=1)
    assert calls == [(1, 321, 1)]


@pytest.mark.asyncio
async def test_stream_classroom_chat_empty_brain_fallback(monkeypatch):
    # Brain 无文本输出 → 下发兜底文案
    monkeypatch.setattr(cg_chat, "get_or_create_classroom_agent", _async_value(123))
    monkeypatch.setattr(cg_chat, "_get_classroom_brain", lambda *a, **k: StubBrain([
        {"role": "tool", "type": "tool_start", "tool": "web_search"},
    ]))
    monkeypatch.setattr(cg_chat, "_build_classroom_path_context", _async_value("ctx"))
    monkeypatch.setattr(cg_chat, "_build_global_portrait_context", _async_value("portrait"))

    events = await _collect(cg_chat.stream_classroom_chat(1, 1, 1, {}, "free", "xxx"))
    joined = "\n".join(events)
    assert cg_chat._FALLBACK_REPLIES["free"] in joined
    assert "[DONE]" in joined


@pytest.mark.asyncio
async def test_stream_classroom_chat_error(monkeypatch):
    # Brain 抛异常 → error 事件 + [DONE]，不静默中断
    monkeypatch.setattr(cg_chat, "get_or_create_classroom_agent", _async_value(123))
    monkeypatch.setattr(cg_chat, "_get_classroom_brain", lambda *a, **k: StubBrain([], raise_error=True))
    monkeypatch.setattr(cg_chat, "_build_classroom_path_context", _async_value("ctx"))
    monkeypatch.setattr(cg_chat, "_build_global_portrait_context", _async_value("portrait"))

    events = await _collect(cg_chat.stream_classroom_chat(1, 1, 1, {}, "free", "xxx"))
    joined = "\n".join(events)
    assert '"error"' in joined
    assert "[DONE]" in joined


def _async_value(value):
    async def _inner(*args, **kwargs):
        return value
    return _inner
