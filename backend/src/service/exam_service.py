"""题库服务 — 生成、答题、掌握度追踪"""

import json
import uuid
from datetime import datetime

from tortoise.expressions import Q

from backend.src.ai_core.llm_config import llm
from backend.src.models.exam_model import ExamQuestion, ExamRecord, KnowledgeMastery
from backend.src.models.usermodel import User
from backend.src.models.agent_skill_model import AgentSkill
from backend.src.utils.database import init_db
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.service.portrait_service import format_portrait
from backend.src.utils.knowledge_base import search as kb_search



def _parse_json_response(text: str) -> list:
    """从 LLM 响应中提取 JSON 数组，自动处理 markdown 代码块包裹"""
    content = text.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        if len(lines) > 1:
            content = "\n".join(lines[1:])
        if content.endswith("```"):
            content = content[:-3]
    try:
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _question_to_dict(q: ExamQuestion) -> dict:
    def _safe_parse(text: str | None):
        if not text:
            return text
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text

    return {
        "question_id": q.id,
        "question_type": q.question_type,
        "content": q.content,
        "options": _safe_parse(q.options),
        "answer": _safe_parse(q.answer),
        "analysis": q.analysis,
        "difficulty": q.difficulty,
        "knowledge_tags": _safe_parse(q.knowledge_tags) or [],
        "created_at": str(q.created_at),
    }


class ExamService:

    @staticmethod
    async def generate_and_save(
        topic: str, user_id: int,
        question_types: list[str] | None = None, count: int = 5, difficulty: str = "medium",
    ) -> list[dict]:
        """直接 LLM 出题 → 解析 JSON → 存库"""
        await init_db()
        types = question_types or ["single_choice"]
        types_str = ", ".join(types)

        portrait_context = "暂无画像数据"
        kb_context = "暂无相关知识库资料"
        custom_prompt = None

        user = await User.filter(id=user_id).first()
        if user:
            picture = await user.picture
            if picture:
                portrait_context = "\n".join(format_portrait(picture, show_missing=False))

        try:
            kb_result = await kb_search(topic, top_k=5, user_id=user_id)
            if kb_result and "暂无" not in kb_result:
                kb_context = kb_result
        except Exception:
            pass

        # 查自定义出题 skill
        skill = await AgentSkill.filter(user_id=user_id, resource_type="exam", enabled=True).first()
        if skill and skill.system_prompt:
            custom_prompt = skill.system_prompt

        template = custom_prompt or load_prompt("resource/exam")
        prompt_text = fill_prompt(
            template,
            topic=topic,
            question_types=types_str,
            count=str(count),
            difficulty=difficulty,
            portrait_context=portrait_context,
            kb_context=kb_context,
            feedback="",
        )

        try:
            response = await llm.ainvoke(prompt_text)
            questions = _parse_json_response(response.content)
        except Exception:
            return []
        if not questions:
            return []

        saved = []
        for q in questions:
            record = await ExamQuestion.create(
                question_type=q.get("question_type", "single_choice"),
                content=q.get("content", ""),
                options=json.dumps(q.get("options"), ensure_ascii=False) if q.get("options") else None,
                answer=json.dumps(q.get("answer"), ensure_ascii=False) if isinstance(q.get("answer"), list) else str(q.get("answer") or ""),
                analysis=q.get("analysis", ""),
                difficulty=q.get("difficulty", difficulty),
                knowledge_tags=json.dumps(q.get("knowledge_tags", []), ensure_ascii=False),
                user=user,
            )
            saved.append(_question_to_dict(record))
        return saved

    @staticmethod
    async def list_questions(user_id: int, question_type: str | None = None, difficulty: str | None = None, knowledge_tag: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        qs = ExamQuestion.filter(Q(is_public=True) | Q(user_id=user_id))
        if question_type:
            qs = qs.filter(question_type=question_type)
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        if knowledge_tag:
            qs = qs.filter(knowledge_tags__contains=knowledge_tag)
        total = await qs.count()
        records = await qs.order_by("-created_at").offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total, "page": page, "page_size": page_size,
            "items": [_question_to_dict(r) for r in records],
        }

    @staticmethod
    async def get_question(question_id: int, user_id: int) -> dict | None:
        record = await ExamQuestion.filter(id=question_id).first()
        if not record:
            return None
        if not record.is_public and (record.user_id is None or record.user_id != user_id):
            return None
        return _question_to_dict(record)

    @staticmethod
    async def delete_question(question_id: int, user_id: int) -> bool:
        record = await ExamQuestion.filter(id=question_id, user_id=user_id).first()
        if not record:
            return False
        await record.delete()
        return True

    @staticmethod
    async def submit_answer(question_id: int, user_id: int, user_answer: str, time_spent: int | None = None) -> dict:
        question = await ExamQuestion.filter(id=question_id).first()
        if not question:
            raise ValueError("题目不存在")

        correct_answer = question.answer
        if question.question_type in ("single_choice", "true_false"):
            is_correct = (user_answer.strip() == correct_answer.strip())
        elif question.question_type == "multi_choice":
            try:
                def _normalize(ans: str) -> set:
                    if ans.startswith("["):
                        return set(json.loads(ans))
                    return set(ans.strip().upper().replace(" ", "").split(","))
                is_correct = _normalize(user_answer) == _normalize(correct_answer)
            except Exception:
                is_correct = user_answer.strip().upper() == correct_answer.strip().upper()
        else:
            is_correct = None

        session_id = str(uuid.uuid4())[:12]
        await ExamRecord.create(
            question=question,
            user_id=user_id,
            user_answer=user_answer,
            is_correct=is_correct,
            time_spent=time_spent,
            session_id=session_id,
        )

        if question.knowledge_tags:
            try:
                tags = json.loads(question.knowledge_tags)
            except Exception:
                tags = []
            for tag in tags:
                mastery, _ = await KnowledgeMastery.get_or_create(
                    user_id=user_id, knowledge_tag=tag,
                    defaults={"total_attempts": 0, "correct_count": 0, "mastery_level": "beginner", "last_practiced_at": datetime.now()},
                )
                mastery.total_attempts += 1
                if is_correct:
                    mastery.correct_count += 1
                rate = mastery.correct_count / max(mastery.total_attempts, 1)
                if rate >= 0.9:
                    mastery.mastery_level = "mastered"
                elif rate >= 0.7:
                    mastery.mastery_level = "proficient"
                elif rate >= 0.4:
                    mastery.mastery_level = "learning"
                else:
                    mastery.mastery_level = "beginner"
                mastery.last_practiced_at = datetime.now()
                await mastery.save()

        return {
            "question_id": question_id,
            "is_correct": is_correct,
            "correct_answer": correct_answer if not is_correct else None,
            "analysis": question.analysis if not is_correct else None,
        }

    @staticmethod
    async def get_records(user_id: int, page: int = 1, page_size: int = 20) -> dict:
        qs = ExamRecord.filter(user_id=user_id)
        total = await qs.count()
        records = await qs.order_by("-created_at").offset((page - 1) * page_size).limit(page_size).prefetch_related("question").all()
        items = []
        for r in records:
            items.append({
                "record_id": r.id,
                "question": _question_to_dict(r.question) if r.question else None,
                "user_answer": r.user_answer,
                "is_correct": r.is_correct,
                "time_spent": r.time_spent,
                "session_id": r.session_id,
                "created_at": str(r.created_at),
            })
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    @staticmethod
    async def get_mastery(user_id: int) -> list[dict]:
        records = await KnowledgeMastery.filter(user_id=user_id).order_by("-last_practiced_at").all()
        return [
            {
                "knowledge_tag": r.knowledge_tag,
                "total_attempts": r.total_attempts,
                "correct_count": r.correct_count,
                "accuracy": round(r.correct_count / max(r.total_attempts, 1), 2),
                "mastery_level": r.mastery_level,
                "last_practiced_at": str(r.last_practiced_at),
            }
            for r in records
        ]
