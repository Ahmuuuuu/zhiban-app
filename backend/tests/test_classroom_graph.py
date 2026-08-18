# -*- coding: utf-8 -*-
"""
classroom_graph 双智能体编排测试

测试目标：backend/src/ai_core/classroom_graph.py
覆盖：Writer(规划+并行分幕) → Reviewer(审核) → 重写循环的三种路径。
所有 LLM 调用用 FakeLLM 模拟（不联网、不烧钱）。
"""
import json

import pytest

import backend.src.ai_core.classroom_graph as cg
from backend.src.service.path.classroom import _fallback_lesson

# ── 罐头数据 ──

PLAN = {
    "title": "BCD与ASCII编码",
    "personal_summary": "结合计算机专业，从数字表示与字符编号的差异入手。",
    "main_thread": "数字如何保存 vs 字符如何编号，是两条不同的编码线。",
    "segments": [
        {"id": "lead-in", "goal": "导入", "focus": "数字表示与字符编号的区别", "style": "类比引导"},
        {"id": "concept", "goal": "讲解", "focus": "BCD 表示十进制数字", "style": "分步拆解"},
        {"id": "resource-link", "goal": "佐证", "focus": "用资料验证 BCD 定义", "style": "查证引导"},
        {"id": "checkpoint", "goal": "检查", "focus": "字符5的ASCII不等于数值5", "style": "提问"},
        {"id": "feynman", "goal": "反讲", "focus": "三句话讲清BCD与ASCII", "style": "费曼"},
    ],
    "question_plan": {"checkpoint": {"prompt": "字符'5'的ASCII码为什么不是二进制数5？", "options": ["A", "B", "C"], "answer": "A", "feedback": "解析"}},
}

SEG_TPL = {
    "lead-in": {"id": "lead-in", "type": "hook", "title": "情境导入", "subtitle": "先判断它解决什么", "intent": "建立问题意识",
                "teacher_speech": "这节从一个问题进入：数字在机器里怎么保存，字符又怎么编号。两者是不同的编码线，不要混为一谈。理解这个区别，后面的BCD和ASCII就不会绕晕。", "script": "x",
                "board_title": "问题入口", "board_items": ["数字表示", "字符编号", "两条编码线"], "points": ["数字按值保存", "字符按编号保存", "两者不同"],
                "visual_hint": "数字 vs 字符", "example": "59 按 BCD 是 0101 1001，字符5是35H。", "resource_refs": [], "duration_seconds": 20,
                "question": {"prompt": "先分清什么？", "options": ["定义边界", "步骤关系", "易错对比"], "answer": "定义边界", "feedback": "对。"}},
    "concept": {"id": "concept", "type": "concept", "title": "核心讲解", "subtitle": "BCD 拆解", "intent": "讲清关键概念",
                "teacher_speech": "BCD 用四位二进制表示一位十进制数字，每一位的位权是8421，所以叫8421BCD。十进制59的压缩BCD是0101 1001B。注意BCD服务的是数字，不是字符。", "script": "x",
                "board_title": "概念主线", "board_items": ["8421权值", "压缩BCD一字节两位", "BCD只表示0-9"], "points": ["8421按权相加", "一字节两位", "只服务数字"],
                "visual_hint": "8421BCD", "example": "59 → 0101 1001B", "resource_refs": [], "duration_seconds": 24,
                "question": {"prompt": "8421BCD的位权是？", "options": ["8 4 2 1", "1 2 4 8", "无位权"], "answer": "8 4 2 1", "feedback": "正确。"}},
    "resource-link": {"id": "resource-link", "type": "resource", "title": "资料佐证", "subtitle": "查证主线", "intent": "学会查证",
                "teacher_speech": "现在用资料验证刚才的板书：在资料里找 BCD 定义和 8421 权值说明，确认数字表示与字符编号是两回事。资料是用来查证的，不是用来背的。", "script": "x",
                "board_title": "查证路径", "board_items": ["查BCD定义", "查8421权值", "查ASCII码表"], "points": ["先找定义", "再找权值", "最后对比码表"],
                "visual_hint": "资料查证", "example": "资料里同时出现BCD和ASCII，重点看服务对象。", "resource_refs": [{"title": "微机原理讲义", "type": "document", "how_to_use": "核对BCD定义"}], "duration_seconds": 22,
                "question": {"prompt": "看资料优先验证什么？", "options": ["关键关系", "排版", "页数"], "answer": "关键关系", "feedback": "对。"}},
    "checkpoint": {"id": "checkpoint", "type": "quiz", "title": "即时检查", "subtitle": "暴露薄弱点", "intent": "短问卡薄弱点",
                "teacher_speech": "做一次短检查：字符'5'的ASCII码为什么不是二进制数5？因为ASCII是字符编号，编码值不等于数值。答不上来就回看板书。", "script": "x",
                "board_title": "检查路径", "board_items": ["用一句话概括", "举一个例子", "指出易错点"], "points": ["ASCII编码值不等于数值", "回看板书", "例题定位"],
                "visual_hint": "短检查", "example": "字符5的ASCII是35H，不是5。", "resource_refs": [], "duration_seconds": 18,
                "question": {"prompt": "字符'5'的ASCII为什么不是数5？", "options": ["编码值不等于数值", "等于数值", "没区别"], "answer": "编码值不等于数值", "feedback": "对，编码≠数值。"}},
    "feynman": {"id": "feynman", "type": "feynman", "title": "费曼反讲", "subtitle": "换你当老师", "intent": "三句话反讲",
                "teacher_speech": "最后换你讲：用三句话讲清BCD和ASCII的区别。讲不顺的地方，就是下一轮最该补的位置。", "script": "x",
                "board_title": "三句话反讲", "board_items": ["是什么", "为什么重要", "怎么用"], "points": ["是什么", "为什么重要", "怎么用"],
                "visual_hint": "讲不顺处即补强点", "example": "BCD服务数字，ASCII服务字符。", "resource_refs": [], "duration_seconds": 20,
                "question": {"prompt": "你准备怎么讲？", "options": ["三句话总结", "举例", "先说不懂处"], "answer": "三句话总结", "feedback": "可以。"}},
}


class FakeResp:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """根据 prompt 内容返回对应的罐头 JSON：规划 / 单幕 / 审核。记录调用次数。"""

    def __init__(self, reviewer_results):
        self.reviewer_results = list(reviewer_results)
        self.calls = []

    async def ainvoke(self, prompt, priority="high", user_id=0, pool="default"):
        self.calls.append(pool)
        if "总导演（ClassroomDirector）" in prompt:
            return FakeResp(json.dumps(PLAN, ensure_ascii=False))
        if "课堂脚本审核员（ClassroomReviewer）" in prompt:
            result = self.reviewer_results.pop(0) if self.reviewer_results else {"passed": True, "score": 90, "feedback": "", "issues": []}
            return FakeResp(json.dumps(result, ensure_ascii=False))
        for sid in cg._SEGMENT_IDS:
            if f"幕 id：{sid}" in prompt:
                return FakeResp(json.dumps(SEG_TPL[sid], ensure_ascii=False))
        return FakeResp("{}")


def make_state(user_id=1):
    fallback = _fallback_lesson("BCD与ASCII编码", "数字如何保存、字符如何编号", [], "暂无画像数据")
    return cg.ClassroomState(
        path_id=1, node_id=1, user_id=user_id, subject="微机原理",
        topic="BCD与ASCII编码", summary="数字如何保存、字符如何编号",
        knowledge_tags=["BCD", "ASCII"], quiz_config={}, quiz_snapshot={},
        resources=[], portrait_context="暂无画像数据", fallback_lesson=fallback, llm_priority="high",
    )


def assert_lesson_contract(lesson):
    """断言 lesson 满足前端 segment 契约（LearningClassroomView 深度依赖）。"""
    segs = lesson.get("segments")
    assert isinstance(segs, list) and len(segs) == 5, f"segments 应为5段, got {len(segs) if segs else 0}"
    assert [s.get("id") for s in segs] == list(cg._SEGMENT_IDS), "id 顺序必须为固定五幕"
    for s in segs:
        for field in ("type", "title", "subtitle", "intent", "teacher_speech", "script",
                      "board_title", "board_items", "points", "visual_hint", "example",
                      "resource_refs", "duration_seconds", "question"):
            assert field in s, f"segment 缺少字段 {field}"
        for field in ("prompt", "options", "answer", "feedback"):
            assert field in s["question"], f"question 缺少字段 {field}"


@pytest.mark.asyncio
async def test_passed_first_try(monkeypatch):
    """审核首轮通过：1 规划 + 5 幕并行 + 1 审核 = 7 次调用，retry=0。"""
    fake = FakeLLM([])
    monkeypatch.setattr(cg, "llm", fake)
    final = await cg.classroom_graph.ainvoke(make_state())
    assert final.get("review_passed") is True
    assert final.get("retry_count") == 0
    assert_lesson_contract(final.get("lesson"))
    assert set(fake.calls) == {"classroom"}, "所有调用必须走 classroom pool"
    assert len(fake.calls) == 7, f"首轮应 7 次调用, got {len(fake.calls)}"


@pytest.mark.asyncio
async def test_retry_then_pass(monkeypatch):
    """首轮未通过 → 带反馈重写（跳过规划）→ 次轮通过，retry=1。"""
    fake = FakeLLM([
        {"passed": False, "score": 62, "feedback": "concept 幕知识讲解不够具体，需给出8421权值表达式。",
         "issues": [{"segment_id": "concept", "category": "accuracy", "message": "concept 幕缺少具体表达式，请补充 8421 权值示例。"}]},
        {"passed": True, "score": 86, "feedback": "", "issues": []},
    ])
    monkeypatch.setattr(cg, "llm", fake)
    final = await cg.classroom_graph.ainvoke(make_state())
    assert final.get("retry_count") == 1
    assert final.get("review_passed") is True
    assert_lesson_contract(final.get("lesson"))
    # 1 规划 + 5 幕 + 1 审 + 5 幕重写 + 1 审 = 13
    assert len(fake.calls) == 13, f"应 13 次调用, got {len(fake.calls)}"


@pytest.mark.asyncio
async def test_max_retries_stop(monkeypatch):
    """连续未通过 → retry=2 达上限强制结束，返回最后一次归一化 lesson（不回退模板）。"""
    fake = FakeLLM([
        {"passed": False, "score": 50, "feedback": "问题1", "issues": [{"segment_id": None, "category": "generic", "message": "整体模板化"}]},
        {"passed": False, "score": 55, "feedback": "问题2", "issues": [{"segment_id": None, "category": "generic", "message": "仍模板化"}]},
    ])
    monkeypatch.setattr(cg, "llm", fake)
    final = await cg.classroom_graph.ainvoke(make_state())
    assert final.get("retry_count") == 2
    assert final.get("review_passed") is False
    assert_lesson_contract(final.get("lesson"))
    assert len(fake.calls) == 13, f"应 13 次调用（2 轮）, got {len(fake.calls)}"
