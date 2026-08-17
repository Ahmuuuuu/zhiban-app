"""Scoring logic for mock classroom reports."""

import json
import logging
import re
from typing import Any

from backend.src.models.mock_classroom_model import MockClassroomSession
from backend.src.utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)


class MockClassroomScoring:
    @staticmethod
    async def score(
        session: MockClassroomSession,
        transcript: str,
        vision_summary: dict[str, Any],
        asr_result: dict[str, Any],
        user_id: int,
    ) -> dict[str, Any]:
        transcript = (transcript or "").strip()
        if transcript:
            try:
                return await MockClassroomScoring._llm_score(
                    session=session,
                    transcript=transcript,
                    vision_summary=vision_summary,
                    asr_result=asr_result,
                    user_id=user_id,
                )
            except Exception:
                logger.warning("[MockClassroom] LLM scoring fallback session=%s", session.session_key, exc_info=True)

        return MockClassroomScoring._heuristic_score(
            session=session,
            transcript=transcript,
            vision_summary=vision_summary,
            asr_result=asr_result,
        )

    @staticmethod
    async def _llm_score(
        session: MockClassroomSession,
        transcript: str,
        vision_summary: dict[str, Any],
        asr_result: dict[str, Any],
        user_id: int,
    ) -> dict[str, Any]:
        prompt = f"""你是一个客观、克制的学习讲解评分助手。请根据学生的模拟讲课文字稿、后台知识库检索到的参考资料和课堂画面统计，评价他对知识点的理解和表达熟练度。

评分权重：
- knowledge_score 知识理解：60 分权重，关注概念覆盖、准确性、逻辑结构、例子、遗漏。
- fluency_score 讲解熟练度：25 分权重，关注连贯性、重复、讲解长度是否合理。
- presentation_score 表达状态：15 分权重，只依据客观画面统计，不做焦虑、自信、情绪异常等主观判断。

请只输出 JSON，不要输出 Markdown。

课堂主题：{session.topic}
计划时长：{session.planned_minutes} 分钟
实际时长：{session.elapsed_seconds} 秒
知识库参考资料：
{session.reference_text or "未检索到相关知识库资料，请主要根据课堂主题、讲课文字稿和客观画面统计做保守评分。"}

ASR 状态：{asr_result.get("status")}
讲课文字稿：
{transcript[:6000]}

课堂画面统计：
{json.dumps(vision_summary, ensure_ascii=False)}

输出格式：
{{
  "overall_score": 0-100,
  "knowledge_score": 0-100,
  "fluency_score": 0-100,
  "presentation_score": 0-100,
  "strengths": ["..."],
  "gaps": ["..."],
  "suggestions": ["..."],
  "rubric": {{
    "coverage_score": 0-20,
    "accuracy_score": 0-20,
    "structure_score": 0-10,
    "example_score": 0-5,
    "omission_score": 0-5,
    "continuity_score": 0-8,
    "pause_control_score": 0-6,
    "repeat_control_score": 0-5,
    "pace_score": 0-4,
    "duration_score": 0-2
  }}
}}"""

        from backend.src.ai_core.llm_config import llm

        response = await llm.ainvoke(prompt, priority="high", user_id=int(user_id or 0), pool="leader")
        parsed = parse_llm_json(response.content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM scoring result is not a JSON object")
        return MockClassroomScoring._normalize_result(parsed, vision_summary, source="llm")

    @staticmethod
    def _heuristic_score(
        session: MockClassroomSession,
        transcript: str,
        vision_summary: dict[str, Any],
        asr_result: dict[str, Any],
    ) -> dict[str, Any]:
        words = MockClassroomScoring._token_count(transcript)
        reference_keywords = MockClassroomScoring._keywords(session.reference_text or session.topic)
        hit_count = sum(1 for word in reference_keywords if word in transcript) if transcript else 0
        coverage_rate = hit_count / max(len(reference_keywords), 1) if reference_keywords else 0

        if transcript:
            knowledge_score = 52 + min(28, words // 18) + round(coverage_rate * 20)
            gaps = [] if coverage_rate >= 0.5 else ["讲解中和知识库参考资料的重合还不够，建议补充关键概念和例子。"]
        else:
            knowledge_score = 35
            gaps = ["当前没有可用文字稿，知识理解分只能作为占位估计。"]

        duration_score = MockClassroomScoring._duration_score(session.elapsed_seconds, session.planned_minutes)
        if transcript:
            fluency_score = 52 + min(24, words // 25) + round(duration_score * 24)
        else:
            fluency_score = 48 + round(duration_score * 32)

        presentation_score = int(vision_summary.get("presentation_score") or 60)
        knowledge_score = MockClassroomScoring._clamp(knowledge_score)
        fluency_score = MockClassroomScoring._clamp(fluency_score)
        presentation_score = MockClassroomScoring._clamp(presentation_score)
        overall_score = MockClassroomScoring._weighted(knowledge_score, fluency_score, presentation_score)

        strengths = []
        if session.elapsed_seconds >= 60:
            strengths.append("完成了一段连续讲解，具备输出练习的基本样本。")
        if presentation_score >= 80:
            strengths.append(vision_summary.get("summary") or "课堂画面比较稳定。")
        if transcript and words >= 80:
            strengths.append("文字稿长度足够，后续可以进一步做知识点覆盖分析。")
        if not strengths:
            strengths.append("已经完成一次模拟讲课记录，后续可以在此基础上复盘。")

        suggestions = []
        if asr_result.get("status") not in {"ready", "client_transcript"} and not transcript:
            suggestions.append("本次没有拿到有效讲课文字稿，知识理解评分会偏保守。")
        suggestions.append("下一次讲解时可以按“定义-推导-例子-易错点-总结”的顺序组织内容。")
        if presentation_score < 75:
            suggestions.append(vision_summary.get("summary") or "讲解时尽量保持人像在镜头中稳定可见。")

        return {
            "overall_score": overall_score,
            "knowledge_score": knowledge_score,
            "fluency_score": fluency_score,
            "presentation_score": presentation_score,
            "strengths": strengths[:4],
            "gaps": gaps[:4],
            "suggestions": suggestions[:4],
            "rubric": {
                "source": "heuristic",
                "asr_status": asr_result.get("status"),
                "keyword_count": len(reference_keywords),
                "keyword_hit_count": hit_count,
                "coverage_rate": round(coverage_rate, 4),
                "word_count": words,
                "duration_completion": round(duration_score, 4),
                "vision_summary": vision_summary,
            },
        }

    @staticmethod
    def _normalize_result(payload: dict[str, Any], vision_summary: dict[str, Any], source: str) -> dict[str, Any]:
        knowledge_score = MockClassroomScoring._clamp(payload.get("knowledge_score"))
        fluency_score = MockClassroomScoring._clamp(payload.get("fluency_score"))
        model_presentation_score = MockClassroomScoring._clamp(payload.get("presentation_score"))
        camera_presentation_score = MockClassroomScoring._clamp(vision_summary.get("presentation_score"))
        presentation_score = round(model_presentation_score * 0.45 + camera_presentation_score * 0.55)
        overall_score = MockClassroomScoring._weighted(knowledge_score, fluency_score, presentation_score)

        rubric = payload.get("rubric") if isinstance(payload.get("rubric"), dict) else {}
        rubric.update({
            "source": source,
            "vision_summary": vision_summary,
            "model_overall_score": MockClassroomScoring._clamp(payload.get("overall_score")),
        })

        return {
            "overall_score": overall_score,
            "knowledge_score": knowledge_score,
            "fluency_score": fluency_score,
            "presentation_score": presentation_score,
            "strengths": MockClassroomScoring._clean_list(payload.get("strengths")),
            "gaps": MockClassroomScoring._clean_list(payload.get("gaps")),
            "suggestions": MockClassroomScoring._clean_list(payload.get("suggestions")),
            "rubric": rubric,
        }

    @staticmethod
    def _duration_score(elapsed_seconds: int, planned_minutes: int) -> float:
        target_seconds = max(60, int(planned_minutes or 5) * 60)
        ratio = max(0, int(elapsed_seconds or 0)) / target_seconds
        if 0.65 <= ratio <= 1.3:
            return 1
        if ratio < 0.65:
            return max(0, ratio / 0.65)
        return max(0.35, 1 - min(0.65, (ratio - 1.3) * 0.45))

    @staticmethod
    def _keywords(text: str) -> list[str]:
        chunks = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_+-]{2,}", text or "")
        seen = set()
        keywords = []
        for chunk in chunks:
            if chunk in seen:
                continue
            seen.add(chunk)
            keywords.append(chunk)
            if len(keywords) >= 24:
                break
        return keywords

    @staticmethod
    def _token_count(text: str) -> int:
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text or ""))
        words = len(re.findall(r"[A-Za-z0-9_+-]+", text or ""))
        return chinese_chars + words

    @staticmethod
    def _weighted(knowledge_score: int, fluency_score: int, presentation_score: int) -> int:
        return MockClassroomScoring._clamp(
            round(knowledge_score * 0.6 + fluency_score * 0.25 + presentation_score * 0.15)
        )

    @staticmethod
    def _clamp(value: Any, default: int = 0) -> int:
        try:
            number = round(float(value))
        except (TypeError, ValueError):
            number = default
        return max(0, min(100, number))

    @staticmethod
    def _clean_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned[:5]
