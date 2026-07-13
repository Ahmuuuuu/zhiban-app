"""PPT course planning helpers for resource generation."""

from __future__ import annotations

import logging
import re
import time

from backend.src.ai_core.llm_config import llm
from backend.src.utils.formula_builder import build_formula_sheet
from backend.src.utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

# PPT 并行生成参数
PPT_PAGES_PER_SECTION = 2    # 每个章节 1-3 页（AI 按内容复杂度自行决定）
PPT_DEFAULT_SECTIONS = 11    # 默认 11 章节（22 页左右，更接近完整学习课件）
PPT_SECTION_COUNT_BY_DEPTH = {
    "overview": 7,            # 快速概览 → 14 页左右
    "standard": 11,           # 标准讲解 → 22 页左右
    "deep": 14,               # 逐页详解 → 28 页左右
}
PPT_SECTION_COUNT_BOUNDS = {
    "overview": (7, 9),
    "standard": (11, 14),
    "deep": (14, 18),
}


def estimate_ppt_section_count(topic: str, depth: str = "standard") -> int:
    """根据课程主题广度估算 PPT 章节数，避免学科型主题页数过薄。"""
    base = PPT_SECTION_COUNT_BY_DEPTH.get(depth, PPT_DEFAULT_SECTIONS)
    low, high = PPT_SECTION_COUNT_BOUNDS.get(depth, (10, 13))
    text = str(topic or "").strip()
    normalized = text.lower()

    broad_patterns = [
        r"导论|概论|基础|入门|体系|全景|综述|历史|发展|原理|课程",
        r"线性代数|高等数学|概率论|统计学|机器学习|人工智能|数据结构|操作系统|计算机网络|组成原理",
        r"数据库|编译原理|软件工程|数字电路|模拟电路|微机原理|信号与系统",
    ]
    narrow_patterns = [
        r"单页|快速|速览|复习|小结|清单|一个例子|一道题|某一步|某个",
        r"定义|概念辨析|公式推导|例题|实现|代码|步骤|算法",
    ]

    score = 0
    if len(text) >= 10:
        score += 1
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in broad_patterns):
        score += 2
    if any(token in normalized for token in ("chapter", "course", "overview", "intro")):
        score += 1
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in narrow_patterns):
        score -= 1
    if re.search(r"[、,，/]|与|和|及|到", text):
        score += 1

    estimated = base + score
    return max(low, min(high, estimated))

# 文档并行生成参数
DOC_DEFAULT_SECTIONS = 6    # 默认 6 章节，与 PPT 对齐
DOC_SECTION_COUNT_BY_DEPTH = {
    "overview": 3,            # 与 PPT 对齐
    "standard": 6,
    "deep": 10,
}


async def generate_ppt_outline(topic: str, kb: str = "", guidance: str = "", count: int = PPT_DEFAULT_SECTIONS, llm_priority: str = "high", user_id: int = 0) -> tuple[list[str], dict[str, str], str]:
    """生成 PPT 课程地图与章节大纲。

    不依赖 RAG 时，planner 也要像老师备课一样先排学科结构，再下发给章节 executor。
    """
    total_pages = count * PPT_PAGES_PER_SECTION
    prompt = f"""你是一个资深学科课程设计师和 PPT 总导演。请为以下主题设计一份可直接下发给并行章节生成器的课程地图。

主题：{topic}
学习指导：{guidance}
知识库参考：{kb[:1200] if kb and "暂无" not in kb else "无；请使用你作为教师的通用学科知识进行规划，但不要编造具体来源"}

## 课程规划原则
- 固定 {count} 个章节（必须恰好 {count} 个），每章后续生成 2 页幻灯片，总共约 {total_pages} 页。
- 章节数是根据课程内容广度估算的，不要主动压缩；如果主题是完整学科或课程导论，必须覆盖足够多的核心模块，不能只做 5-8 页式速览。
- 即使没有知识库，也要按该学科的经典教学顺序规划：先修概念 → 核心定义 → 基本规则/原理 → 方法步骤 → 小例题 → 应用场景 → 易错辨析 → 总结迁移。
- 不要平均分配“概念名”；每章必须有明确教学角色，例如：概念奠基、规则推导、方法操作、对比辨析、案例应用、综合检查。
- 数学/计算机/工程类主题必须安排最小例子或维度/条件检查；人文社科类主题必须安排时间线、概念对比、文本/案例分析或观点辨析。
- 章节标题简洁（建议 6-14 字），但不要为了短而丢掉学科对象。

## 输出格式
你的回复必须是纯 JSON，第一个字符是 `{{`，最后一个字符是 `}}`。禁止 markdown 代码块、禁止说明文字。

{{
  "course_type": "学科类型，例如 math_foundation/cs_core/history_survey/general",
  "course_goal": "整套 PPT 学完后学习者应能完成的任务，40-80字",
  "prerequisite_chain": ["最必要的前置知识1", "最必要的前置知识2"],
  "section_outline": [
    {{
      "title": "章节标题",
      "role": "概念奠基/规则推导/方法操作/对比辨析/案例应用/误区检查/总结迁移",
      "learning_goal": "本章学完能做什么，必须可验证",
      "prerequisites": ["本章依赖的前置概念"],
      "key_points": ["必须讲的知识点1", "必须讲的知识点2", "必须讲的知识点3"],
      "micro_example": "本章建议使用的最小例子、案例或检查任务",
      "assessment": "本章自查标准",
      "bloom": "记忆/理解/应用/分析/评价/创造"
    }}
  ]
}}
"""
    defaults = [
        {
            "title": "核心概念入门",
            "role": "概念奠基",
            "learning_goal": "说清主题中的核心对象、基本问题和学习边界。",
            "prerequisites": [],
            "key_points": ["核心对象", "基本定义", "适用场景"],
            "micro_example": "用一个最小场景说明概念解决什么问题。",
            "assessment": "能用自己的话解释本章概念并举出一个例子。",
            "bloom": "理解",
        },
        {
            "title": "基本原理推导",
            "role": "规则推导",
            "learning_goal": "解释核心规则为什么成立，并知道使用前提。",
            "prerequisites": ["核心概念入门"],
            "key_points": ["关键规则", "成立条件", "变量含义"],
            "micro_example": "用小规模例子逐步验证规则。",
            "assessment": "能指出规则适用和不适用的情况。",
            "bloom": "理解",
        },
        {
            "title": "关键方法解析",
            "role": "方法操作",
            "learning_goal": "按步骤完成一个典型任务，并能检查每一步。",
            "prerequisites": ["基本原理"],
            "key_points": ["操作步骤", "中间结果", "检查标准"],
            "micro_example": "完成一道最小例题或流程演示。",
            "assessment": "能复述方法流程并发现常见错误。",
            "bloom": "应用",
        },
        {
            "title": "典型案例分析",
            "role": "案例应用",
            "learning_goal": "把方法应用到具体案例，并解释选择该方法的原因。",
            "prerequisites": ["关键方法"],
            "key_points": ["案例输入", "方法选择", "结果解释"],
            "micro_example": "分析一个短案例或小数据例子。",
            "assessment": "能从题目信息判断使用哪种方法。",
            "bloom": "应用",
        },
        {
            "title": "常见误区辨析",
            "role": "误区检查",
            "learning_goal": "识别常见错误，并说明错误发生的原因。",
            "prerequisites": ["案例应用"],
            "key_points": ["错误条件", "对比判断", "修正方法"],
            "micro_example": "对比一个正确做法和一个错误做法。",
            "assessment": "能用检查清单排除至少两类错误。",
            "bloom": "分析",
        },
        {
            "title": "总结迁移练习",
            "role": "总结迁移",
            "learning_goal": "串联全课知识，并迁移到一个新任务。",
            "prerequisites": ["前面章节"],
            "key_points": ["知识链路", "迁移场景", "复习策略"],
            "micro_example": "完成一个综合判断或小练习。",
            "assessment": "能画出知识链路并说明下一步学习方向。",
            "bloom": "评价",
        },
    ]

    def _normalize_section(item, idx: int) -> dict:
        base = defaults[idx % len(defaults)]
        if not isinstance(item, dict):
            item = {"title": str(item or base["title"])}
        title = re.sub(r"[#<>`$]", "", str(item.get("title") or base["title"])).strip() or base["title"]
        return {
            **base,
            **item,
            "title": title[:24],
            "key_points": item.get("key_points") if isinstance(item.get("key_points"), list) else base["key_points"],
            "prerequisites": item.get("prerequisites") if isinstance(item.get("prerequisites"), list) else base["prerequisites"],
        }

    def _pack_plan(data) -> tuple[list[str], dict[str, str], str]:
        if isinstance(data, list):
            section_items = [_normalize_section(item, i) for i, item in enumerate(data)]
            course_goal = f"围绕「{topic}」建立从概念、规则、方法到应用检查的完整学习链条。"
            prerequisite_chain = []
            course_type = "general"
        elif isinstance(data, dict):
            raw_sections = data.get("section_outline") or data.get("sections") or data.get("outline") or []
            section_items = [_normalize_section(item, i) for i, item in enumerate(raw_sections)]
            course_goal = str(data.get("course_goal") or f"围绕「{topic}」建立从概念到应用的学习链条。").strip()
            prerequisite_chain = data.get("prerequisite_chain") if isinstance(data.get("prerequisite_chain"), list) else []
            course_type = str(data.get("course_type") or "general").strip()
        else:
            section_items = []
            course_goal = f"围绕「{topic}」建立从概念到应用的学习链条。"
            prerequisite_chain = []
            course_type = "general"

        while len(section_items) < count:
            section_items.append(_normalize_section(defaults[len(section_items) % len(defaults)], len(section_items)))
        section_items = section_items[:count]
        titles = [item["title"] for item in section_items]

        guidance_map: dict[str, str] = {}
        for i, item in enumerate(section_items):
            key_points = "、".join(str(x) for x in item.get("key_points", [])[:5])
            prereqs = "、".join(str(x) for x in item.get("prerequisites", [])[:4]) or "无特殊前置"
            guidance_map[item["title"]] = (
                f"## 本章教学规划\n"
                f"- 课程类型：{course_type}\n"
                f"- 章节位置：第 {i + 1}/{count} 章\n"
                f"- 教学角色：{item.get('role', '')}\n"
                f"- 学习目标：{item.get('learning_goal', '')}\n"
                f"- 前置依赖：{prereqs}\n"
                f"- 必讲要点：{key_points}\n"
                f"- 最小例子：{item.get('micro_example', '')}\n"
                f"- 自查标准：{item.get('assessment', '')}\n"
                f"- Bloom 层级：{item.get('bloom', '')}"
            )

        sequence = "\n".join(
            f"{i + 1}. {item['title']}｜{item.get('role', '')}｜{item.get('learning_goal', '')}"
            for i, item in enumerate(section_items)
        )
        prereq_text = "、".join(str(x) for x in prerequisite_chain[:6]) or "无特殊前置"
        course_plan = (
            f"【课程地图】\n"
            f"课程类型：{course_type}\n"
            f"课程目标：{course_goal}\n"
            f"先修链：{prereq_text}\n"
            f"章节序列：\n{sequence}"
        )
        return titles, guidance_map, course_plan

    try:
        t0 = time.perf_counter()
        response = await llm.ainvoke(prompt, priority=llm_priority, user_id=user_id, pool="ppt")
        plan = parse_llm_json(response.content)
        sections, guidance_map, course_plan = _pack_plan(plan)
        if sections:
            logger.info("[PPT-Outline] 大纲生成 章节数=%d 耗时=%.2fs", len(sections), time.perf_counter() - t0)
            return sections, guidance_map, course_plan
    except Exception:
        logger.exception("[PPT-Outline] 大纲生成失败，使用默认章节")
    return _pack_plan(defaults)


async def generate_formula_sheet(
    topic: str, kb: str = "", guidance: str = "",
    llm_priority: str = "high", user_id: int = 0,
) -> str:
    """从知识库提取关键公式，生成公式速查表，供各章节 executor 直接引用"""
    template_sheet = build_formula_sheet(topic)
    if not kb or kb == "暂无相关知识库资料":
        return template_sheet

    prompt = f"""你是一个数学公式整理专家。从以下知识库资料中提取与「{topic}」相关的关键公式。

## 要求
- 只提取与主题直接相关的公式，无关的不要
- 每个公式独立一行，格式：`- 公式名称：$LaTeX表达式$`
- LaTeX 必须严格正确，变量、上下标、符号准确
- 按逻辑顺序排列（从基础到进阶）
- 总共 5-15 条公式，宁缺毋滥
- 如果知识库中没有相关公式，返回"无"

## 知识库资料
{kb[:3000]}

## 返回格式
直接返回纯文本，每行一条：
- 公式名称：$...$
- 公式名称：$...$
"""
    try:
        t0 = time.perf_counter()
        response = await llm.ainvoke(prompt, priority=llm_priority, user_id=user_id, pool="ppt")
        sheet = response.content.strip()
        if sheet == "无":
            sheet = ""
        logger.info("[Formula-Sheet] 公式提取 耗时=%.2fs 条数≈%d", time.perf_counter() - t0, sheet.count('\n') + 1 if sheet else 0)
        if template_sheet and sheet:
            return f"{template_sheet}\n\nAdditional formulas extracted from reference materials:\n{sheet}"
        return template_sheet or sheet
    except Exception:
        logger.exception("[Formula-Sheet] 提取失败")
        return template_sheet


async def generate_learning_objectives(
    topic: str, sections: list[str], kb: str = "", guidance: str = "",
    llm_priority: str = "high", user_id: int = 0,
) -> str:
    """为课程生成 Bloom 分类的学习目标注册表（LO Registry），返回格式化文本"""
    sections_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sections))
    prompt = f"""你是一个课程教学设计专家。为以下课程设计学习目标注册表。

课程主题：{topic}
学习指导：{guidance}
知识库：{kb or '无'}

## 课程章节
{sections_text}

## 要求
- 为整个课程设计 8-15 条学习目标，编号 LO-01 到 LO-15
- 每条目标标注 Bloom 认知层次（记忆/理解/应用/分析/评价/创造）
- 确保覆盖 ≥4 个 Bloom 层次，其中必须有「应用」和「分析」
- 每条 ≤30 字，使用可测量的行为动词（定义、解释、计算、对比、判断等）
- 每条标注对应的章节编号，确保每个章节至少被 1 条目标覆盖

## 返回格式
直接返回纯文本，格式如下（不要 JSON）：
LO-01: [目标描述]（[Bloom层次]）— 对应章节：[章节号]
LO-02: ...
...
"""
    try:
        t0 = time.perf_counter()
        response = await llm.ainvoke(prompt, priority=llm_priority, user_id=user_id, pool="ppt")
        lo_text = response.content.strip()
        logger.info("[LO-Registry] 学习目标生成 耗时=%.2fs", time.perf_counter() - t0)
        return lo_text
    except Exception:
        logger.exception("[LO-Registry] 生成失败")
        return "暂无学习目标数据"


