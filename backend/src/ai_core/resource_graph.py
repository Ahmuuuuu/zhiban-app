"""
LangGraph 多智能体编排 — 学习资源生成
LeaderAgent → [ExecutorAgent × N 线程并行] → ReviewerAgent
"""
import asyncio
import concurrent.futures
import json
import logging
import time
from typing import TypedDict, NotRequired

from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, START, END

from backend.src.ai_core.llm_config import llm
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

# 资源类型 → 默认 prompt 路径
PROMPT_MAP = {
    "document": "resource/document",
    "ppt": "resource/ppt",
    "ppt_apply": "resource/ppt_apply",
    "mindmap": "resource/mindmap",
    "exercise": "resource/exam",
    "case": "resource/document",
    "reading": "resource/document",
    "image": "resource/image_prompt",
}


# ═══════════════════════════════════════
#  State
# ═══════════════════════════════════════

class ResourceState(TypedDict):
    user_id: str
    topic: str
    resource_types: list[str]
    portrait_context: str
    kb_context: str
    learning_guidance: str
    user_notes: str
    custom_prompts: dict
    generated_resources: dict
    review_feedback: str
    review_passed: bool
    retry_count: int
    exam_question_types: str
    exam_count: str
    exam_difficulty: str
    reviewer_questions: list[dict]
    file_urls: NotRequired[dict[str, str]]
    answers: NotRequired[dict]
    skip_review: NotRequired[bool]


# ═══════════════════════════════════════
#  Nodes
# ═══════════════════════════════════════

async def leader_node(state: ResourceState) -> dict:
    """LeaderAgent: 分析需求，决定生成哪些资源类型（用户已指定则跳过 LLM）"""
    requested = state.get("resource_types") or []
    if requested:
        return {"resource_types": requested}

    topic = state["topic"]
    portrait = state.get("portrait_context", "")
    kb = state.get("kb_context", "")
    guidance = state.get("learning_guidance", "")
    prompt_text = fill_prompt(load_prompt("agent/leader"), topic=topic, portrait_context=portrait, kb_context=kb, learning_guidance=guidance)

    try:
        response = await llm.ainvoke(prompt_text)
    except Exception as e:
        logger.exception("LeaderAgent LLM 调用失败")
        return {"resource_types": ["document"]}

    try:
        plan = parse_llm_json(response.content)
    except json.JSONDecodeError:
        plan = {"resource_types": ["document"], "topic": topic, "outline": response.content.strip()}

    resource_types = plan.get("resource_types", ["document"])
    return {"resource_types": resource_types}


def build_resource_prompt(
    rt: str, topic: str, portrait: str = "", kb: str = "",
    guidance: str = "", feedback: str = "", user_notes: str = "",
    exam_count: str = "5", question_types: str = "single_choice, multi_choice, true_false",
    difficulty: str = "medium", custom_prompts: dict | None = None,
    focus_guidance: str = "",
    section: str = "",
) -> str:
    """构建单个资源类型的生成 prompt，可从 executor_node 或 generate_stream 直接调用"""
    custom_prompts = custom_prompts or {}
    custom = custom_prompts.get(rt, "")
    if custom.strip():
        template = custom
    else:
        prompt_path = PROMPT_MAP.get(rt, "resource/document")
        template = load_prompt(prompt_path)
    rt_kb = kb
    base = fill_prompt(
        template,
        topic=topic,
        resource_type=rt,
        portrait_context=portrait,
        kb_context=rt_kb,
        learning_guidance=guidance,
        user_notes=user_notes,
        feedback=feedback,
        count=exam_count,
        question_types=question_types,
        difficulty=difficulty,
        section=section,
    )
    return base + focus_guidance if focus_guidance else base


# PPT 并行生成参数
PPT_PAGES_PER_SECTION = 2  # 每个章节生成 2 页
PPT_MAX_SECTIONS = 10      # 最多 10 章节（20 页上限）


async def generate_ppt_outline(topic: str, kb: str = "", guidance: str = "") -> list[str]:
    """快速生成 PPT 章节大纲，固定 10 章节 20 页"""
    prompt = f"""你是一个课程规划师。为以下主题设计PPT章节大纲。

主题：{topic}
学习指导：{guidance}

要求：
- 固定 10 个章节（必须恰好 10 个），每个章节生成 2 页幻灯片，总共 20 页
- 章节标题简洁（10 字以内），由浅入深，逻辑连贯，形成完整的课程体系
- 覆盖主题的：定义概念 → 原理推导 → 方法技巧 → 典型案例 → 应用实践 → 总结回顾
- 只返回 JSON 字符串数组，不要任何其他文字

返回示例：["矩阵的定义与表示", "矩阵基本运算", "矩阵乘法详解", "特殊矩阵", "行列式计算", "逆矩阵与伴随矩阵", "矩阵的秩与线性方程组", "特征值与特征向量", "矩阵分解与应用", "综合回顾与总结"]
"""
    try:
        t0 = time.perf_counter()
        response = await llm.ainvoke(prompt)
        sections = parse_llm_json(response.content)
        if isinstance(sections, list) and len(sections) >= 1:
            # 不足 10 个时用默认标题补齐
            defaults = ["核心概念入门", "基本原理推导", "关键方法解析", "典型案例分析", "进阶知识拓展", "实际应用场景", "常见误区辨析", "与其他知识的联系", "综合练习与思考", "课程总结与回顾"]
            while len(sections) < 10:
                sections.append(defaults[len(sections)])
            sections = sections[:PPT_MAX_SECTIONS]
            logger.info("[PPT-Outline] 大纲生成 章节数=%d 耗时=%.2fs", len(sections), time.perf_counter() - t0)
            return sections
    except Exception:
        logger.exception("[PPT-Outline] 大纲生成失败，使用默认章节")
    return ["核心概念入门", "基本原理推导", "关键方法解析", "典型案例分析", "进阶知识拓展", "实际应用场景", "常见误区辨析", "与其他知识的联系", "综合练习与思考", "课程总结与回顾"]


async def generate_ppt_parallel(
    topic: str,
    portrait: str = "",
    kb: str = "",
    guidance: str = "",
    feedback: str = "",
    user_notes: str = "",
    custom_prompts: dict | None = None,
    sections: list[str] | None = None,
    stream_writer=None,
) -> str:
    """按章节并行生成 PPT：大纲（固定10章节） → 10 条线并行（每条 2 页），共 20 页 + 2 页画像应用场景 = 22 页"""
    # 立即通知前端，避免长时间无反馈
    if stream_writer:
        try:
            stream_writer({"type": "stream_start", "file_type": "ppt"})
        except Exception:
            stream_writer = None

    if sections is None:
        if stream_writer:
            try:
                stream_writer({"type": "stream_progress", "file_type": "ppt", "message": "正在规划课程大纲..."})
            except Exception:
                stream_writer = None
        sections = await generate_ppt_outline(topic, kb=kb, guidance=guidance)

    # 追加画像应用场景章节（如果画像数据可用）
    has_portrait = portrait and portrait != "暂无画像数据"
    if has_portrait:
        sections = list(sections) + ["应用场景与个性化实践"]

    # 构建课程全景描述，让每个章节知道自己在哪里
    outline_lines = [f"第{i+1}章「{s}」" for i, s in enumerate(sections)]
    course_overview = "\n".join(outline_lines)

    def _quick_check_ppt(content: str) -> bool:
        """启发式快检：内容明显合格则跳过 LLM 审核，节省 token"""
        slides = content.split("\n---\n")
        for slide in slides:
            slide = slide.strip()
            if not slide or not slide.startswith("##"):
                continue
            if len(slide) < 200:
                return False
            if "（上）" in slide or "（下）" in slide:
                return False
            bullets = [l for l in slide.split("\n") if l.strip().startswith("-")]
            if len(bullets) < 4:
                return False
            # $ 符号是否成对
            dollars = slide.count("$")
            if dollars % 2 != 0:
                return False
        return True

    async def gen_section(idx: int, section_title: str) -> tuple[int, str]:
        # 推送开始生成通知
        if stream_writer:
            try:
                stream_writer({
                    "type": "stream_progress",
                    "file_type": "ppt",
                    "message": f"正在生成第 {idx + 1}/{total} 章「{section_title}」...",
                    "current": idx + 1,
                    "total": total,
                })
            except Exception:
                pass

        base_prompt = build_resource_prompt(
            "ppt", topic,
            portrait=portrait, kb=kb, guidance=guidance,
            feedback=feedback, user_notes=user_notes,
            custom_prompts=custom_prompts,
            section=section_title,
        )
        prev_section = sections[idx - 1] if idx > 0 else "（无，这是第一章）"
        next_section = sections[idx + 1] if idx < len(sections) - 1 else "（无，这是最后一章）"
        is_portrait_section = has_portrait and idx == len(sections) - 1

        if is_portrait_section:
            # 画像应用场景：结合学科与用户画像，展示实际应用
            base_prompt = build_resource_prompt(
                "ppt_apply", topic,
                portrait=portrait, kb=kb, guidance=guidance,
                feedback=feedback, user_notes=user_notes,
                custom_prompts=custom_prompts,
                section=section_title,
            )
            context = (
                f"\n\n【你的任务】为「{topic}」撰写 2 页应用场景幻灯片，标题为「应用场景与个性化实践」。"
                f"\n\n## 核心要求"
                f"\n你必须将学科知识与用户画像深度融合，让用户感受到'这门课是为我定制的'："
                f"\n1. 第1页：从画像中的学习目标/兴趣出发，举 3 个具体的生活或职业场景，展示本课程知识如何解决实际问题"
                f"\n2. 第2页：画像中的薄弱知识点如何通过本课程内容得到加强，规划一个简短的学习路径或实操建议"
                f"\n3. 场景举例必须用到画像中的具体信息（年级、目标、兴趣、性格等），不要泛泛而谈"
                f"\n4. 语气亲切，让学生觉得'这个老师了解我'"
                f"\n\n## 画像数据\n{portrait}"
                f"\n\n## 课程已覆盖的知识点（前面各章）\n{course_overview}"
            )
            prompt_with_context = base_prompt + context
        else:
            context = (
                f"\n\n【课程全景 — 共 {len(sections)} 章 20 页】\n{course_overview}"
                f"\n\n【你的任务】只负责第 {idx + 1} 章「{section_title}」的恰好 2 页幻灯片。"
                f"\n- 前一章：{prev_section}（你的内容需自然承接）"
                f"\n- 后一章：{next_section}（你的内容需为后面做铺垫）"
                f"\n- 严禁重复其他章节的内容，每章内容独立且有明确边界"
            )
            prompt_with_context = base_prompt + context

        t0 = time.perf_counter()
        for attempt in range(2):
            try:
                response = await llm.ainvoke(prompt_with_context)
                content = response.content
                elapsed = time.perf_counter() - t0
            except Exception:
                elapsed = time.perf_counter() - t0
                logger.exception("[PPT-Section] idx=%d section=%s LLM 失败 耗时=%.2fs", idx, section_title, elapsed)
                return idx, f"## {section_title}\n- 生成失败"

            # 快检通过则跳过 LLM 审核
            if _quick_check_ppt(content):
                logger.info("[PPT-Section] idx=%d section=%s 快检通过，跳过审核 耗时=%.2fs",
                            idx, section_title, elapsed)
                _push_section(idx, content)
                return idx, content

            # LLM 审核
            try:
                review_prompt = fill_prompt(
                    load_prompt("agent/reviewer_ppt"),
                    content=content[:3000],
                    topic=topic,
                )
                review_response = await llm.ainvoke(review_prompt)
                result = _parse_review_response(review_response.content)
                passed = result.get("passed", False)
                if isinstance(passed, str):
                    passed = passed.lower() in ("true", "yes", "1", "是", "pass")
                score = result.get("score", 0)
                review_feedback = result.get("feedback", "")

                if passed:
                    logger.info("[PPT-Section] idx=%d section=%s 审核通过 score=%d 耗时=%.2fs attempt=%d",
                                idx, section_title, score, elapsed, attempt + 1)
                    _push_section(idx, content)
                    return idx, content

                logger.info("[PPT-Section] idx=%d section=%s 审核未通过 score=%d attempt=%d feedback=%s",
                            idx, section_title, score, attempt + 1, review_feedback[:120])
                prompt_with_context = base_prompt + context + f"\n\n【审核未通过，必须修改】\n{review_feedback}\n请根据以上反馈重新生成。"
            except Exception:
                logger.exception("[PPT-Section] idx=%d section=%s 审核异常，跳过", idx, section_title)
                _push_section(idx, content)
                return idx, content

        # 两次尝试均未通过，返回最后一次结果
        logger.info("[PPT-Section] idx=%d section=%s 两次审核均未通过，使用最后一次结果 耗时=%.2fs",
                    idx, section_title, time.perf_counter() - t0)
        _push_section(idx, content)
        return idx, content

    completed_count = 0
    total = len(sections)

    def _push_section(idx: int, content: str):
        """将章节的幻灯片逐页推送给前端"""
        nonlocal completed_count
        if not stream_writer:
            return
        try:
            for slide in content.split("\n---\n"):
                slide = slide.strip()
                if slide:
                    if slide.startswith("# ") and not slide.startswith("## "):
                        slide = slide.replace("# ", "## ", 1)
                    stream_writer({"type": "stream_slide", "file_type": "ppt", "content": slide})
            completed_count += 1
            stream_writer({
                "type": "stream_progress",
                "file_type": "ppt",
                "message": f"已生成 {completed_count}/{total} 章节",
                "current": completed_count,
                "total": total,
            })
        except Exception:
            logger.exception("[PPT-Parallel] 章节 %d 推送异常", idx)

    tasks = [gen_section(i, s) for i, s in enumerate(sections)]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda x: x[0])

    # 组装全部幻灯片
    parts: list[str] = []
    for _, content in results:
        for slide in content.split("\n---\n"):
            slide = slide.strip()
            if not slide:
                continue
            if slide.startswith("# ") and not slide.startswith("## "):
                slide = slide.replace("# ", "## ", 1)
            parts.append(slide)

    combined = "\n---\n".join(parts)
    logger.info("[PPT-Parallel] 合并完成 章节数=%d 总页数≈%d", len(sections), len(parts))

    return combined


async def executor_node(state: ResourceState) -> dict:
    """并行生成所有资源类型，PPT 通过 get_stream_writer 逐页流式推送"""
    topic = state["topic"]
    resource_types = state.get("resource_types", ["document"])
    portrait = state.get("portrait_context", "")
    kb = state.get("kb_context", "")
    guidance = state.get("learning_guidance", "")
    custom_prompts = state.get("custom_prompts", {}) or {}
    feedback = state.get("review_feedback", "")
    focus_guidance = _build_focus_guidance(state.get("answers", {}) or {})
    user_notes = state.get("user_notes", "")

    writer = get_stream_writer()

    # 分离 PPT 和其他类型
    has_ppt = "ppt" in resource_types
    non_ppt_types = [rt for rt in resource_types if rt != "ppt"]

    # 非 PPT 类型线程池并行
    prompts = {
        rt: build_resource_prompt(
            rt, topic, portrait=portrait, kb=kb, guidance=guidance,
            feedback=feedback, user_notes=user_notes,
            exam_count=state.get("exam_count", "5"),
            question_types=state.get("exam_question_types", "single_choice, multi_choice, true_false"),
            difficulty=state.get("exam_difficulty", "medium"),
            custom_prompts=custom_prompts, focus_guidance=focus_guidance,
        )
        for rt in non_ppt_types
    }

    user_id = state.get("user_id", "0")
    max_workers = min(len(non_ppt_types), 5)

    def gen_one_sync(rt: str) -> tuple[str, str]:
        t_start = time.perf_counter()
        try:
            if rt == "image":
                result = _generate_image_sync(prompts[rt], user_id)
            else:
                response = llm.invoke(prompts[rt])
                result = rt, response.content
            elapsed = time.perf_counter() - t_start
            logger.info(f"[Executor] {rt} 生成完成 耗时={elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - t_start
            logger.exception(f"[Executor] {rt} 调用失败 耗时={elapsed:.2f}s")
            return rt, f"[生成失败: {e}]"

    t_gen_start = time.perf_counter()

    # PPT 与非 PPT 并行执行
    ppt_task = None
    other_futures = None
    loop = asyncio.get_running_loop()

    async def _run_ppt():
        if not has_ppt:
            return None
        return await generate_ppt_parallel(
            topic, portrait=portrait, kb=kb, guidance=guidance,
            feedback=feedback, user_notes=user_notes,
            custom_prompts=custom_prompts,
            stream_writer=writer,
        )

    ppt_coro = _run_ppt()

    if non_ppt_types:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            other_futures = asyncio.gather(
                *[loop.run_in_executor(pool, gen_one_sync, rt) for rt in non_ppt_types]
            )
            ppt_content, other_results = await asyncio.gather(ppt_coro, other_futures)
    else:
        other_results = []
        ppt_content = await ppt_coro

    logger.info("[Executor] 全部生成完成 并行总耗时=%.2fs types=%s", time.perf_counter() - t_gen_start, resource_types)

    retry = state.get("retry_count", 0)
    if feedback:
        retry += 1

    generated = {}
    file_urls = {}
    for rt, content in other_results:
        if rt.startswith("image:"):
            actual_rt = rt.replace("image:", "")
            generated[actual_rt] = content.get("prompt", "")
            if content.get("url"):
                file_urls[actual_rt] = content["url"]
        else:
            generated[rt] = content
    if ppt_content:
        generated["ppt"] = ppt_content

    return {
        "generated_resources": generated,
        "file_urls": file_urls,
        "retry_count": retry,
        "review_feedback": "",
    }


def _generate_image_sync(prompt_text: str, user_id: str) -> tuple[str, dict]:
    """两阶段图片生成：LLM 产出 prompt → ImageService 生图（线程内）"""
    try:
        response = llm.invoke(prompt_text)
        image_prompt = response.content.strip()
    except Exception as e:
        logger.exception("图片 prompt 生成失败")
        return ("image:error", {"prompt": "", "url": ""})

    try:
        from backend.src.service.image_service import ImageService
        image_prompt = image_prompt[:900]
        images = asyncio.run(ImageService.generate(image_prompt, user_id, aspect_ratio="16:9", img_count=2))
        if images and len(images) > 0:
            return ("image:image", {"prompt": image_prompt, "url": images[0].get("url", "")})
    except Exception as e:
        logger.exception(f"图片生成失败: {e}")

    return ("image:image", {"prompt": image_prompt, "url": ""})


def _parse_review_response(raw: str) -> dict:
    """解析 reviewer 返回的 JSON，容错处理。
    支持新格式（逐题）和旧格式（整批），统一返回含 questions 字段的 dict。"""
    try:
        result = parse_llm_json(raw)
        if not isinstance(result, dict):
            return {"passed": True, "score": 70, "feedback": raw, "questions": []}
        # exercise 新格式：包含逐题结果
        if "questions" in result and isinstance(result["questions"], list):
            return {
                "passed": result.get("overall_passed", True),
                "score": result.get("overall_score", 70),
                "feedback": result.get("overall_feedback", ""),
                "questions": result["questions"],
            }
        # 旧格式兼容（其他资源类型）
        return {
            "passed": result.get("passed", True),
            "score": result.get("score", 70),
            "feedback": result.get("feedback", ""),
            "questions": [],
        }
    except json.JSONDecodeError:
        return {"passed": True, "score": 70, "feedback": raw, "questions": []}


# 资源类型 → 专用审核员
_REVIEWER_MAP = {
    "document": "agent/reviewer_document",
    "case": "agent/reviewer_document",
    "reading": "agent/reviewer_document",
    "ppt": "agent/reviewer_ppt",
    "exercise": "agent/reviewer_exam",
    "mindmap": "agent/mindmap_reviewer",
    "image": "agent/reviewer_image",
}


async def reviewer_node(state: ResourceState) -> dict:
    """ReviewerAgent: 每种资源类型由专用审核员独立审查，并行执行"""
    generated = state.get("generated_resources", {})

    async def review_one(rt: str, content: str) -> dict:
        # PPT 已在 generate_ppt_parallel 内部逐章节审核，此处跳过
        if rt == "ppt":
            return {"passed": True, "score": 100, "feedback": ""}
        # API 生成的图片跳过文本审核
        file_urls = state.get("file_urls", {})
        if file_urls.get(rt):
            return {"passed": True, "score": 100, "feedback": "API 生成，自动通过"}
        reviewer_path = _REVIEWER_MAP.get(rt, "agent/reviewer_document")
        if not content:
            return {"passed": True, "score": 100, "feedback": ""}
        try:
            content_snippet = content[:3000]
            prompt_text = fill_prompt(
                load_prompt(reviewer_path),
                content=content_snippet,
                topic=state.get("topic", ""),
                kb_context=state.get("kb_context", "暂无相关知识库资料"),
            )
            response = await llm.ainvoke(prompt_text)
            result = _parse_review_response(response.content)
            logger.info(f"[审核] {rt}: passed={result.get('passed')} score={result.get('score')}")
            return result
        except Exception as e:
            logger.exception(f"[审核] {rt} 失败")
            return {"passed": True, "score": 0, "feedback": f"审核异常: {e}"}

    tasks = [review_one(rt, content) for rt, content in generated.items()]
    if not tasks:
        return {"review_passed": True, "review_feedback": ""}

    results = await asyncio.gather(*tasks)

    # 汇总
    feedback_parts = []
    all_passed = True
    question_results = []
    for (rt, _), result in zip(generated.items(), results):
        passed = result.get("passed", False)
        if isinstance(passed, str):
            passed = passed.lower() in ("true", "yes", "1", "是", "pass")
        if not passed:
            all_passed = False
            feedback_parts.append(f"[{rt}] {result.get('feedback', '')}")
        # 收集 per-question 审核结果（exercise 类型）
        for q in result.get("questions", []):
            question_results.append(q)

    return {
        "review_passed": all_passed,
        "review_feedback": "\n".join(feedback_parts),
        "reviewer_questions": question_results,
    }


def _build_focus_guidance(answers: dict) -> str:
    """从追问答案提取聚焦方向和深度，构建 prompt 约束指令。
    无 answers 时返回空字符串，不影响常规生成。
    """
    if not answers:
        return ""

    # 提取所有 focus 值
    focus_vals: list[str] = []
    for key, val in answers.items():
        if key.startswith("focus") or key == "focus":
            if isinstance(val, list):
                focus_vals.extend(str(v) for v in val)
            elif val:
                focus_vals.append(str(val))

    depth = answers.get("depth", "")
    if not focus_vals and not depth:
        return ""

    parts: list[str] = ["\n\n【学习方向与深度约束 — 必须严格遵守】"]
    if focus_vals:
        kw = "、".join(focus_vals)
        parts.append(f"- 聚焦主题：{kw}")
        parts.append("- 仅生成上述方向的内容，不要展开无关话题")
    if depth:
        depth_map = {
            "overview": "- 深度：5分钟快速概览，只讲核心概念和关键结论，省略推导和案例",
            "standard": "- 深度：标准讲解，涵盖原理和应用，适量举例",
            "deep": "- 深度：逐页详解，包含完整推导、案例分析和深入讨论",
        }
        parts.append(depth_map.get(depth, f"- 深度：{depth}"))

    parts.append("- 请根据以上约束减少内容体量，精简字数，不要为凑篇幅而添加无关信息")
    return "\n".join(parts)


# ═══════════════════════════════════════
#  Router
# ═══════════════════════════════════════

def should_continue(state: ResourceState) -> str:
    if state.get("review_passed"):
        return "end"
    if state.get("retry_count", 0) >= 2:
        return "end"
    return "executor"


def should_review(state: ResourceState) -> str:
    """跳过审核可省掉一轮 LLM 调用，适用于学习路径等对质量要求不极端的场景"""
    if state.get("skip_review"):
        return "end"
    return "reviewer"


# ═══════════════════════════════════════
#  Graph
# ═══════════════════════════════════════

def build_graph():
    workflow = StateGraph(ResourceState)

    workflow.add_node("leader", leader_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.add_edge(START, "leader")
    workflow.add_edge("leader", "executor")
    workflow.add_conditional_edges(
        "executor",
        should_review,
        {"reviewer": "reviewer", "end": END},
    )
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {"executor": "executor", "end": END},
    )

    return workflow.compile()


resource_graph = build_graph()
