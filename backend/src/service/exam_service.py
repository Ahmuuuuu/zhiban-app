"""题库服务 — 生成(走graph)、答题、掌握度追踪"""

import json
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

from tortoise.expressions import Q

from backend.src.models.exam_model import ExamQuestion, ExamRecord, KnowledgeMastery
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.usermodel import User
from backend.src.utils.database import init_db
from backend.src.utils.json_parser import parse_llm_json


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
    async def _save_questions(questions: list[dict], user, difficulty: str, node_id: int | None = None) -> tuple[str, list[dict]]:
        """将解析好的题目存库 + 创建 ExamRecord 占位，返回 (session_id, questions)"""
        if not questions:
            return str(uuid.uuid4())[:12], []
        session_id = str(uuid.uuid4())[:12]
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
            # 创建占位记录，使 session 立即可查询
            await ExamRecord.create(
                question=record,
                user_id=user.id,
                session_id=session_id,
                node_id=node_id,
            )
            saved.append(_question_to_dict(record))
        return session_id, saved

    @staticmethod
    async def generate_and_save(
        topic: str, user_id: int,
        question_types: list[str] | None = None, count: int = 5, difficulty: str = "medium",
        node_id: int | None = None,
    ) -> dict:
        """走 graph 出题（Leader→Executor→Reviewer→retry）→ 存库 → 返回 session_id + questions"""
        await init_db()

        user = await User.filter(id=user_id).first()
        if not user:
            return {"session_id": None, "questions": []}

        from backend.src.service.resource_service import ResourceService  # deferred: circular exam<->resource

        types = question_types or ["single_choice", "multi_choice", "true_false"]
        types_str = ", ".join(types)

        saved_resources = await ResourceService.generate_and_save(
            topic=topic, user_id=user_id, resource_types=["exercise"],
            exam_question_types=types_str, exam_count=count, exam_difficulty=difficulty,
        )

        for r in saved_resources:
            if r.get("resource_type") == "exercise":
                content = r.get("content", "")
                try:
                    questions = parse_llm_json(content)
                    if not isinstance(questions, list):
                        questions = []
                except Exception:
                    logger.exception("题目 JSON 解析失败 resource_id=%s", r.get("resource_id"))
                    questions = []
                if not questions:
                    return {"session_id": None, "questions": []}

                # 按题型/数量/难度过滤
                types = question_types or ["single_choice"]
                filtered = [q for q in questions if q.get("question_type") in types]
                filtered = [q for q in filtered if q.get("difficulty", "medium") == difficulty]
                filtered = filtered[:count]

                session_id, saved = await ExamService._save_questions(filtered, user, difficulty, node_id=node_id)
                return {"session_id": session_id, "questions": saved}

        return {"session_id": None, "questions": []}

    @staticmethod
    async def generate_and_save_stream(
        topic: str, user_id: int,
        question_types: list[str] | None = None, count: int = 5, difficulty: str = "medium",
        node_id: int | None = None,
    ):
        """流式走 graph 出题 → SSE 推送进度 → 存库 → 返回 session"""
        await init_db()

        user = await User.filter(id=user_id).first()
        if not user:
            yield f"data: {json.dumps({'type': 'error', 'detail': '用户不存在'}, ensure_ascii=False)}\n\n"
            return

        from backend.src.service.resource_service import ResourceService  # deferred: circular exam<->resource

        types = question_types or ["single_choice", "multi_choice", "true_false"]
        types_str = ", ".join(types)

        yield f"data: {json.dumps({'type': 'status', 'msg': '正在分析知识点并生成题目...'}, ensure_ascii=False)}\n\n"

        async for event in ResourceService.generate_stream(
            topic=topic, user_id=user_id, resource_types=["exercise"],
            chat_group_id=0,
            exam_question_types=types_str, exam_count=count, exam_difficulty=difficulty,
        ):
            if isinstance(event, str) and event.startswith("data:"):
                data_str = event[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    payload = json.loads(data_str)
                    if payload.get("type") == "file":
                        rt = payload.get("file_type", "")
                        if rt == "exercise":
                            yield f"data: {json.dumps({'type': 'progress', 'msg': '题目内容已生成，正在审核...'}, ensure_ascii=False)}\n\n"
                    elif "review_passed" in payload:
                        passed = payload.get("review_passed", True)
                        yield f"data: {json.dumps({'type': 'progress', 'msg': f'审核{"通过" if passed else "未通过，重新生成"}...'}, ensure_ascii=False)}\n\n"
                except json.JSONDecodeError:
                    pass

        # 查已保存的 exercise 资源，解析题目并保存
        saved_resources = await GeneratedResource.filter(
            user_id=user_id, topic=topic, resource_type="exercise"
        ).order_by("-created_at").limit(1).all()

        session_id = None
        saved_questions = []
        for r in saved_resources:
            if r.content:
                try:
                    questions = parse_llm_json(r.content)
                    if not isinstance(questions, list):
                        questions = []
                except Exception:
                    logger.exception("题目 JSON 解析失败 resource_id=%s", r.id)
                    questions = []
                if questions:
                    filtered = [q for q in questions if q.get("question_type") in types]
                    filtered = [q for q in filtered if q.get("difficulty", "medium") == difficulty]
                    filtered = filtered[:count]
                    if filtered:
                        session_id, saved_questions = await ExamService._save_questions(
                            filtered, user, difficulty, node_id=node_id
                        )
                        yield f"data: {json.dumps({'type': 'progress', 'msg': f'已保存 {len(saved_questions)} 道题目'}, ensure_ascii=False)}\n\n"
                break

        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'quiz_config': {'count': count, 'threshold': 0.7}, 'question_count': len(saved_questions)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

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
    async def submit_answer(question_id: int, user_id: int, user_answer: str, time_spent: int | None = None, session_id: str | None = None, node_id: int | None = None) -> dict:
        question = await ExamQuestion.filter(id=question_id).first()
        if not question:
            raise ValueError("题目不存在")

        correct_answer = question.answer

        # 判断对错
        if question.question_type == "true_false":
            is_correct = user_answer.strip().upper() == correct_answer.strip().upper()
        elif question.question_type in ("single_choice", "fill_blank"):
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
            is_correct = None  # 简答题不自动判分

        score = 100.0 if is_correct is True else (0.0 if is_correct is False else None)
        sid = session_id or str(uuid.uuid4())[:12]

        # 从已有占位记录继承 node_id（如果未显式传入）
        if node_id is None and session_id:
            placeholder = await ExamRecord.filter(session_id=session_id, question_id=question_id, user_answer__isnull=True).first()
            if placeholder and placeholder.node_id:
                node_id = placeholder.node_id

        await ExamRecord.create(
            question=question,
            user_id=user_id,
            user_answer=user_answer,
            is_correct=is_correct,
            score=score,
            time_spent=time_spent,
            session_id=sid,
            node_id=node_id,
        )

        # 更新知识点掌握度
        if question.knowledge_tags:
            try:
                tags = json.loads(question.knowledge_tags)
            except (json.JSONDecodeError, TypeError):
                logger.warning("知识点标签 JSON 解析失败 question_id=%s", question_id)
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

        # 汇总本轮会话成绩
        session_records = await ExamRecord.filter(session_id=sid).all()
        judged = [r for r in session_records if r.is_correct is not None]
        total_questions = len(session_records)
        correct_count = sum(1 for r in judged if r.is_correct)
        judged_count = len(judged)
        session_score = round(sum(r.score for r in judged) / judged_count, 1) if judged_count else None

        return {
            "question_id": question_id,
            "is_correct": is_correct,
            "score": score,
            "correct_answer": correct_answer if not is_correct else None,
            "analysis": question.analysis if not is_correct else None,
            "session_id": sid,
            "session_summary": {
                "total_questions": total_questions,
                "correct_count": correct_count,
                "incorrect_count": judged_count - correct_count,
                "pending_count": total_questions - judged_count,
                "score": session_score,
            },
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
                "score": r.score,
                "time_spent": r.time_spent,
                "session_id": r.session_id,
                "created_at": str(r.created_at),
            })
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    @staticmethod
    async def get_session(session_id: str, user_id: int) -> dict | None:
        """查询一次练习会话的完整状态：所有答题记录 + 汇总"""
        records = await (
            ExamRecord.filter(session_id=session_id, user_id=user_id)
            .order_by("created_at")
            .prefetch_related("question")
            .all()
        )
        if not records:
            return None

        items = []
        for r in records:
            items.append({
                "record_id": r.id,
                "question": _question_to_dict(r.question) if r.question else None,
                "user_answer": r.user_answer,
                "is_correct": r.is_correct,
                "score": r.score,
                "time_spent": r.time_spent,
                "created_at": str(r.created_at),
            })

        judged = [r for r in records if r.is_correct is not None]
        correct_count = sum(1 for r in judged if r.is_correct)
        judged_count = len(judged)

        return {
            "session_id": session_id,
            "total_questions": len(records),
            "correct_count": correct_count,
            "incorrect_count": judged_count - correct_count,
            "pending_count": len(records) - judged_count,
            "score": round(sum(r.score for r in judged) / judged_count, 1) if judged_count else None,
            "records": items,
        }

    @staticmethod
    async def list_sessions(user_id: int) -> list[dict]:
        """列出用户的所有练习会话摘要"""
        records = await (
            ExamRecord.filter(user_id=user_id)
            .order_by("-created_at")
            .prefetch_related("question")
            .all()
        )

        sessions: dict[str, dict] = {}
        for r in records:
            if r.session_id not in sessions:
                sessions[r.session_id] = {
                    "session_id": r.session_id,
                    "total": 0,
                    "correct": 0,
                    "judged": 0,
                    "first_at": str(r.created_at),
                    "last_at": str(r.created_at),
                }
            s = sessions[r.session_id]
            s["total"] += 1
            if r.is_correct is True:
                s["correct"] += 1
                s["judged"] += 1
            elif r.is_correct is False:
                s["judged"] += 1
            s["last_at"] = str(r.created_at)

        for s in sessions.values():
            s["score"] = round(s["correct"] / s["judged"] * 100, 1) if s["judged"] else None

        return sorted(sessions.values(), key=lambda x: x["last_at"], reverse=True)

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
