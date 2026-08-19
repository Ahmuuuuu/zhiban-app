# -*- coding: utf-8 -*-
"""
classroom_graph 双智能体编排测试

测试目标：backend/src/ai_core/classroom_graph.py
覆盖：Writer(规划+并行分幕) → 分幕审核智能体 → 定向重写。
所有 LLM 调用用 FakeLLM 模拟（不联网、不烧钱）。
"""
import json

import pytest

import backend.src.ai_core.classroom_graph as cg
from backend.src.service.path.classroom import _fallback_lesson, _normalize_lesson


@pytest.fixture(autouse=True)
def _disable_tts_prewarm(monkeypatch):
    """课堂图测试只验证分幕编排，不触发真实 EdgeTTS 网络请求。"""
    async def fake_prewarm(*args, **kwargs):
        return None

    monkeypatch.setattr(cg, "_prewarm_segment_audio", fake_prewarm)

# ── 罐头数据 ──

PLAN = {
    "title": "BCD与ASCII编码",
    "personal_summary": "结合计算机专业，从数字表示与字符编号的差异入手。",
    "main_thread": "数字如何保存 vs 字符如何编号，是两条不同的编码线。",
    "segments": [
        {"id": "lead-in", "goal": "导入", "focus": "数字表示与字符编号的区别", "style": "类比引导"},
        {"id": "concept", "goal": "讲解", "focus": "BCD 表示十进制数字", "style": "分步拆解"},
        {"id": "exercise", "goal": "练习", "focus": "用题目检查 BCD 定义", "style": "做题引导"},
        {"id": "feynman", "goal": "反讲", "focus": "三句话讲清BCD与ASCII", "style": "费曼"},
    ],
    "question_plan": {"exercise": {"prompt": "字符'5'的ASCII码为什么不是二进制数5？", "options": ["A", "B", "C"], "answer": "A", "feedback": "解析"}},
}

SEG_TPL = {
    "lead-in": {"id": "lead-in", "type": "hook", "title": "情境导入", "subtitle": "先判断它解决什么", "intent": "建立问题意识",
                "teacher_speech": "这节从一个问题进入：数字在机器里怎么保存，字符又怎么编号。两者是不同的编码线，不要混为一谈。理解这个区别，后面的BCD和ASCII就不会绕晕。", "script": "x",
                "board_title": "问题入口", "board_items": ["数字表示", "字符编号", "两条编码线"], "points": ["数字按值保存", "字符按编号保存", "两者不同"],
                "visual_hint": "数字 vs 字符", "example": "59 按 BCD 是 0101 1001，字符5是35H。", "resource_refs": [], "duration_seconds": 20,
                "interaction": "reflect",
                "question": {"prompt": "先分清什么？", "options": [], "answer": "", "feedback": ""}},
    "concept": {"id": "concept", "type": "concept", "title": "核心讲解", "subtitle": "BCD 拆解", "intent": "讲清关键概念",
                "teacher_speech": "BCD是一种十进制数字编码，用四位二进制表示一位十进制数字，8421是它的位权。ASCII是一种字符编码，用编号表示字符。十进制59的压缩BCD是0101 1001B，注意BCD服务数字，不服务字符。", "script": "x",
                "board_title": "概念主线", "board_items": ["8421权值", "压缩BCD一字节两位", "BCD只表示0-9"], "points": ["8421按权相加", "一字节两位", "只服务数字"],
                "visual_hint": "8421BCD", "example": "59 → 0101 1001B", "resource_refs": [], "duration_seconds": 24,
                "interaction": "open",
                "question": {"prompt": "用你自己的话说说 8421BCD 为什么一字节能存两位十进制？", "options": [], "answer": "", "feedback": ""}},
    "exercise": {"id": "exercise", "type": "exercise", "title": "随堂练习", "subtitle": "检查主线", "intent": "检查理解",
                "teacher_speech": "现在做一道题检查刚才的主线：字符5的ASCII码为什么不是数值5？先看题干中的对象，再判断它代表数字还是字符，最后说清判断依据。", "script": "x",
                "board_title": "解题检查", "board_items": ["读题干", "定位概念", "说明依据"], "points": ["先独立判断", "找题干依据", "解释选择原因"],
                "visual_hint": "随堂练习", "example": "先做题，再用一句话解释选择依据。", "resource_refs": [], "duration_seconds": 22,
                "interaction": "open",
                "question": {"prompt": "完成下方随堂练习，并说明你的判断依据。", "options": [], "answer": "", "feedback": ""}},
    "feynman": {"id": "feynman", "type": "feynman", "title": "费曼反讲", "subtitle": "换你当老师", "intent": "三句话反讲",
                "teacher_speech": "最后换你讲：用三句话讲清BCD和ASCII的区别。讲不顺的地方，就是下一轮最该补的位置。", "script": "x",
                "board_title": "三句话反讲", "board_items": ["是什么", "为什么重要", "怎么用"], "points": ["是什么", "为什么重要", "怎么用"],
                "visual_hint": "讲不顺处即补强点", "example": "BCD服务数字，ASCII服务字符。", "resource_refs": [], "duration_seconds": 20,
                "interaction": "feynman",
                "question": {"prompt": "用三句话讲清BCD和ASCII的区别：各是什么、为什么重要、怎么用。", "options": [], "answer": "", "feedback": ""}},
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
        if "课堂分幕审核员（ClassroomSceneReviewer）" in prompt:
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
    assert isinstance(segs, list) and len(segs) == 4, f"segments 应为4段, got {len(segs) if segs else 0}"
    assert [s.get("id") for s in segs] == list(cg._SEGMENT_IDS), "id 顺序必须为固定四幕"
    for s in segs:
        for field in ("type", "title", "subtitle", "intent", "teacher_speech", "script",
                      "board_title", "board_items", "points", "visual_hint", "example",
                      "resource_refs", "duration_seconds", "interaction", "question"):
            assert field in s, f"segment 缺少字段 {field}"
        interaction = s.get("interaction")
        assert interaction in ("reflect", "open", "choice", "feynman"), f"interaction 非法: {interaction}"
        assert "prompt" in s["question"], "question 缺少 prompt"
        if interaction == "choice":
            for field in ("options", "answer", "feedback"):
                assert field in s["question"], f"choice 幕 question 缺少字段 {field}"
        else:
            assert s["question"].get("options") == [], f"{interaction} 幕 options 应为空数组"


def test_interaction_default_when_missing():
    """LLM 漏给 interaction 时按幕类型回退默认值；非 choice 幕 question 无选项。"""
    fallback = _fallback_lesson("数制转换", "基数决定可用数字、位权决定每位价值", [], "暂无画像数据")
    raw = {
        "title": "数制转换",
        "segments": [
            {"id": sid, "type": cg._SEGMENT_TYPES[sid], "title": f"幕{sid}", "script": f"围绕{sid}的具体讲解内容",
             "teacher_speech": f"围绕{sid}的具体讲解内容", "board_items": ["基数定义", "位权计算", "分组互转"],
             "points": ["按权展开", "除基取余", "分组互转"], "example": "1011B按位权展开为11D"}
            for sid in cg._SEGMENT_IDS
        ],
    }
    lesson = _normalize_lesson(raw, fallback)
    by_id = {s["id"]: s for s in lesson["segments"]}
    assert by_id["lead-in"]["interaction"] == "reflect"
    assert by_id["concept"]["interaction"] == "open"
    assert by_id["exercise"]["interaction"] == "open"
    assert by_id["feynman"]["interaction"] == "feynman"
    for sid in ("lead-in", "concept", "exercise", "feynman"):
        assert by_id[sid]["question"]["options"] == [], f"{sid} 幕不应有选项"


def test_concept_definition_contract_rejects_examples_without_definition():
    issue = cg._concept_definition_contract_issue(
        {"teacher_speech": "同一字节0x53按ASCII是S，按BCD是53，按纯二进制是83。规则不同，含义就不同。"},
        ["ASCII", "BCD", "奇偶校验"],
    )
    assert issue is not None
    assert issue["category"] == "concept_definition"

    assert cg._concept_definition_contract_issue(
        {"teacher_speech": "ASCII是一种字符编码，用编号表示字符。BCD是一种十进制数字编码，每位数字用四位二进制表示。随后再比较两者的对象和边界。"},
        ["ASCII", "BCD"],
    ) is None


@pytest.mark.asyncio
async def test_passed_first_try(monkeypatch):
    """首轮通过：1 规划 + 4 幕生成 + 4 个并行分幕审核。"""
    fake = FakeLLM([])
    monkeypatch.setattr(cg, "llm", fake)
    final = await cg.classroom_graph.ainvoke(make_state())
    assert final.get("review_passed") is True
    assert final.get("retry_count") == 0
    assert_lesson_contract(final.get("lesson"))
    assert set(fake.calls) == {"classroom"}, "所有调用必须走 classroom pool"
    assert len(fake.calls) == 9, f"首轮应为规划、四幕、四个并行审核，共 9 次调用，got {len(fake.calls)}"


@pytest.mark.asyncio
async def test_targeted_review_rewrites_only_failed_scene(monkeypatch):
    """分幕审核不通过时只重写被点名的模块，不重写完整四幕。"""
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
    assert len(fake.calls) == 14, f"只应重写一个模块后再次审核，got {len(fake.calls)}"


@pytest.mark.asyncio
async def test_invalid_lesson_stops_without_retry(monkeypatch):
    """单幕缺字段时只允许一轮定向修复，随后立即结束。"""
    fake = FakeLLM([])
    monkeypatch.setattr(cg, "llm", fake)
    broken = {key: dict(value) for key, value in SEG_TPL.items()}
    broken["concept"] = {"id": "concept", "type": "concept", "title": "核心概念"}
    original = cg._generate_segments

    async def generate_broken(*args, **kwargs):
        return {"title": "BCD与ASCII编码", "learning_summary": "本节理解数字保存与字符编号的差别，并能用例子说明两者。", "key_takeaways": ["BCD表示数字", "ASCII表示字符"], "segments": list(broken.values())}

    monkeypatch.setattr(cg, "_generate_segments", generate_broken)
    final = await cg.classroom_graph.ainvoke(make_state())
    monkeypatch.setattr(cg, "_generate_segments", original)
    assert final.get("retry_count") == 1
    assert final.get("review_passed") is False
    assert len(fake.calls) == 1, f"只应调用规划, got {len(fake.calls)}"
