"""学习路径服务 — 生成、资源、测验、进度追踪"""

import json
from datetime import datetime

from backend.src.ai_core.llm_config import llm
from backend.src.models.path_model import LearningPath, PathNode, UserPathProgress
from backend.src.models.exam_model import ExamRecord
from backend.src.models.usermodel import User
from backend.src.utils.database import init_db
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.service.portrait_service import format_portrait
from backend.src.service.exam_service import ExamService
from backend.src.service.resource_service import ResourceService
from backend.src.utils.knowledge_base import search as kb_search
from backend.src.utils.json_parser import parse_llm_json


class PathService:

    @staticmethod
    async def generate_path(subject: str, user_id: int, difficulty: str = "medium", node_count: int = 5) -> dict:
        """LLM 生成路径结构 → 存库"""
        await init_db()

        portrait_context = "暂无画像数据"
        mastery_context = "暂无掌握度数据"
        kb_context = "暂无相关知识库"

        user = await User.filter(id=user_id).first()
        if user:
            picture = await user.picture
            if picture:
                portrait_context = "\n".join(format_portrait(picture, show_missing=False))

        try:
            kb_result = await kb_search(subject, top_k=5, user_id=user_id)
            if kb_result and "暂无" not in kb_result:
                kb_context = kb_result
        except Exception:
            pass

        template = load_prompt("path/path_generation")
        prompt_text = fill_prompt(
            template,
            subject=subject,
            difficulty=difficulty,
            node_count=str(node_count),
            portrait_context=portrait_context,
            mastery_context=mastery_context,
            kb_context=kb_context,
        )

        try:
            response = await llm.ainvoke(prompt_text)
            result = parse_llm_json(response.content)
            if not isinstance(result, dict):
                result = {}
        except Exception:
            return {"error": "路径生成失败"}

        nodes_data = result.get("nodes", [])
        if not nodes_data:
            return {"error": "LLM 未返回有效节点"}

        path = await LearningPath.create(
            subject=subject,
            difficulty=difficulty,
            node_count=len(nodes_data),
            cover_tags=json.dumps([n.get("topic") for n in nodes_data], ensure_ascii=False),
            user=user,
        )

        nodes = []
        for nd in nodes_data:
            node = await PathNode.create(
                path=path,
                topic=nd.get("topic", ""),
                knowledge_tags=json.dumps(nd.get("knowledge_tags", []), ensure_ascii=False),
                order_index=nd.get("order_index", len(nodes) + 1),
                prerequisites=json.dumps(nd.get("prerequisites", []), ensure_ascii=False),
                resource_types=json.dumps(nd.get("resource_types", ["document"]), ensure_ascii=False),
                quiz_config=json.dumps(nd.get("quiz_config", {"count": 3, "threshold": 0.7}), ensure_ascii=False),
            )
            nodes.append({
                "node_id": node.id,
                "topic": node.topic,
                "order_index": node.order_index,
                "knowledge_tags": json.loads(node.knowledge_tags) if node.knowledge_tags else [],
                "prerequisites": json.loads(node.prerequisites) if node.prerequisites else [],
                "resource_types": json.loads(node.resource_types) if node.resource_types else [],
                "quiz_config": json.loads(node.quiz_config) if node.quiz_config else {},
            })

        return {
            "path_id": path.id,
            "subject": path.subject,
            "difficulty": path.difficulty,
            "node_count": path.node_count,
            "nodes": nodes,
        }

    @staticmethod
    async def list_paths(user_id: int | None = None) -> list[dict]:
        """列出所有公开路径"""
        from tortoise.expressions import Q

        qs = LearningPath.filter(Q(is_public=True))
        if user_id:
            qs = qs | LearningPath.filter(user_id=user_id, is_public=False)
        paths = await qs.order_by("-created_at").prefetch_related("nodes").all()

        result = []
        for p in paths:
            nodes = p.nodes or []
            result.append({
                "path_id": p.id,
                "subject": p.subject,
                "difficulty": p.difficulty,
                "node_count": p.node_count,
                "cover_tags": json.loads(p.cover_tags) if p.cover_tags else [],
                "created_at": str(p.created_at),
                "first_node_id": nodes[0].id if nodes else None,
            })
        return result

    @staticmethod
    async def get_path(path_id: int) -> dict | None:
        """获取路径详情含节点列表"""
        path = await LearningPath.filter(id=path_id).prefetch_related("nodes").first()
        if not path:
            return None

        nodes = path.nodes or []
        return {
            "path_id": path.id,
            "subject": path.subject,
            "difficulty": path.difficulty,
            "node_count": path.node_count,
            "nodes": sorted([
                {
                    "node_id": n.id,
                    "topic": n.topic,
                    "order_index": n.order_index,
                    "knowledge_tags": json.loads(n.knowledge_tags) if n.knowledge_tags else [],
                    "prerequisites": json.loads(n.prerequisites) if n.prerequisites else [],
                    "resource_types": json.loads(n.resource_types) if n.resource_types else [],
                    "quiz_config": json.loads(n.quiz_config) if n.quiz_config else {},
                }
                for n in nodes
            ], key=lambda x: x["order_index"]),
        }

    @staticmethod
    async def enroll_path(path_id: int, user_id: int) -> dict:
        """加入路径 → 初始化 UserPathProgress，解锁首节点并自动生成资源"""
        path = await LearningPath.filter(id=path_id).prefetch_related("nodes").first()
        if not path:
            raise ValueError("路径不存在")

        nodes = path.nodes or []
        if not nodes:
            raise ValueError("路径无节点")

        nodes_sorted = sorted(nodes, key=lambda n: n.order_index)

        existing = await UserPathProgress.filter(user_id=user_id, path_id=path_id).count()
        if existing:
            return {"message": "已加入该路径", "path_id": path_id}

        created = []
        first_node = None
        for i, node in enumerate(nodes_sorted):
            has_prereqs = node.prerequisites and json.loads(node.prerequisites)
            status = "unlocked" if (i == 0 and not has_prereqs) else "locked"
            await UserPathProgress.create(
                user_id=user_id,
                path=path,
                node=node,
                node_status=status,
            )
            if status == "unlocked" and not first_node:
                first_node = node
            created.append({"node_id": node.id, "topic": node.topic, "status": status})

        # 自动为首个节点生成资源
        resources = []
        if first_node:
            try:
                res_result = await PathService.generate_node_resources(path_id, first_node.id, user_id)
                resources = res_result.get("resource_ids", [])
            except Exception:
                pass

        return {"path_id": path_id, "progress": created, "first_node_resources": resources}

    @staticmethod
    async def get_progress(path_id: int, user_id: int) -> dict:
        """获取用户在路径上的整体进度"""
        records = await UserPathProgress.filter(user_id=user_id, path_id=path_id).prefetch_related("node").all()
        if not records:
            return {"path_id": path_id, "status": "not_enrolled"}

        total = len(records)
        completed = sum(1 for r in records if r.node_status == "completed")
        in_progress = sum(1 for r in records if r.node_status == "in_progress")
        unlocked = sum(1 for r in records if r.node_status == "unlocked")

        current_node = None
        for r in records:
            if r.node_status in ("unlocked", "in_progress"):
                current_node = r.node.id if r.node else None
                break

        return {
            "path_id": path_id,
            "total_nodes": total,
            "completed": completed,
            "in_progress": in_progress,
            "locked": total - completed - in_progress - unlocked,
            "percentage": round(completed / total * 100, 1) if total else 0,
            "current_node_id": current_node,
            "nodes": [
                {
                    "node_id": r.node.id if r.node else None,
                    "topic": r.node.topic if r.node else "",
                    "order_index": r.node.order_index if r.node else 0,
                    "status": r.node_status,
                    "quiz_passed": r.quiz_passed,
                }
                for r in sorted(records, key=lambda x: x.node.order_index if x.node else 0)
            ],
        }

    @staticmethod
    async def get_node(path_id: int, node_id: int, user_id: int) -> dict | None:
        """获取节点详情（含资源和测验状态）"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            return None

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()

        resource_ids = json.loads(progress.resource_ids) if progress and progress.resource_ids else []
        resources = []
        if resource_ids:
            from backend.src.models.resource_model import GeneratedResource
            res_records = await GeneratedResource.filter(id__in=resource_ids).all()
            resources = [
                {"resource_id": r.id, "topic": r.topic, "resource_type": r.resource_type}
                for r in res_records
            ]

        return {
            "node_id": node.id,
            "topic": node.topic,
            "order_index": node.order_index,
            "knowledge_tags": json.loads(node.knowledge_tags) if node.knowledge_tags else [],
            "prerequisites": json.loads(node.prerequisites) if node.prerequisites else [],
            "resource_types": json.loads(node.resource_types) if node.resource_types else [],
            "quiz_config": json.loads(node.quiz_config) if node.quiz_config else {},
            "progress": {
                "status": progress.node_status if progress else "not_enrolled",
                "quiz_passed": progress.quiz_passed if progress else False,
                "resources": resources,
            },
        }

    @staticmethod
    async def generate_node_resources(path_id: int, node_id: int, user_id: int) -> dict:
        """为节点生成学习资源"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            raise ValueError("节点不存在")

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()
        if not progress:
            raise ValueError("未加入该路径")

        resource_types = json.loads(node.resource_types) if node.resource_types else ["document"]
        try:
            saved = await ResourceService.generate_and_save(
                topic=node.topic,
                user_id=user_id,
                resource_types=resource_types,
            )
        except Exception:
            return {"node_id": node_id, "resource_ids": [], "generated_count": 0}

        generated_ids = [r.get("resource_id") or r.get("id") for r in saved if r]
        existing = json.loads(progress.resource_ids) if progress.resource_ids else []
        existing.extend(generated_ids)
        progress.resource_ids = json.dumps(existing, ensure_ascii=False)
        if progress.node_status == "unlocked":
            progress.node_status = "in_progress"
            progress.started_at = datetime.now()
        await progress.save()

        return {
            "node_id": node_id,
            "resource_ids": generated_ids,
            "generated_count": len(generated_ids),
        }

    @staticmethod
    async def generate_node_quiz(path_id: int, node_id: int, user_id: int) -> dict:
        """为节点生成测验题目"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            raise ValueError("节点不存在")

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()
        if not progress:
            raise ValueError("未加入该路径")

        quiz_config = json.loads(node.quiz_config) if node.quiz_config else {"count": 3, "threshold": 0.7}
        count = quiz_config.get("count", 3)
        difficulty = "medium"

        result = await ExamService.generate_and_save(
            topic=node.topic,
            user_id=user_id,
            question_types=["single_choice", "multi_choice", "true_false"],
            count=count,
            difficulty=difficulty,
        )

        return {
            "node_id": node_id,
            "session_id": result.get("session_id"),
            "questions": result.get("questions", []),
            "quiz_config": quiz_config,
        }

    @staticmethod
    async def submit_node_quiz(path_id: int, node_id: int, user_id: int, session_id: str) -> dict:
        """提交节点测验结果 → 评分 → 门禁 → 解锁下一节点 → 更新画像"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            raise ValueError("节点不存在")

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()
        if not progress:
            raise ValueError("未加入该路径")

        # 从 session 汇总成绩
        records = await ExamRecord.filter(session_id=session_id, user_id=user_id).all()
        judged = [r for r in records if r.is_correct is not None]
        if not judged:
            return {"error": "该会话无已判分的答题记录"}

        correct = sum(1 for r in judged if r.is_correct)
        score = round(correct / len(judged) * 100, 1)
        quiz_config = json.loads(node.quiz_config) if node.quiz_config else {"count": 3, "threshold": 0.7}
        threshold = quiz_config.get("threshold", 0.7)
        passed = (correct / len(judged)) >= threshold

        progress.quiz_passed = passed

        if passed:
            progress.node_status = "completed"
            progress.completed_at = datetime.now()
            await progress.save()

            # 解锁下一节点并自动生成资源
            await PathService._unlock_next_node(path_id, node.order_index, user_id)
        else:
            progress.node_status = "in_progress"
            await progress.save()

        # 更新画像 traits
        await PathService._update_portrait_from_mastery(user_id)

        return {
            "node_id": node_id,
            "total_questions": len(judged),
            "correct_count": correct,
            "score": score,
            "threshold": threshold,
            "passed": passed,
            "node_status": progress.node_status,
        }

    @staticmethod
    async def regenerate_path(path_id: int, user_id: int) -> dict:
        """基于最新画像重建未完成节点（已完成的保留）"""
        path = await LearningPath.filter(id=path_id).first()
        if not path:
            raise ValueError("路径不存在")

        progresses = await UserPathProgress.filter(user_id=user_id, path_id=path_id).prefetch_related("node").all()
        completed_topics = []
        for r in progresses:
            if r.node_status == "completed" and r.node:
                completed_topics.append(r.node.topic)

        # 用最新画像重新生成
        result = await PathService.generate_path(path.subject, user_id, path.difficulty, path.node_count)
        if "error" in result:
            return result

        new_path_id = result["path_id"]

        # 把新路径中对应已完成 topic 的节点直接标记为 completed
        for nd in result["nodes"]:
            if nd["topic"] in completed_topics:
                await UserPathProgress.filter(
                    user_id=user_id, path_id=new_path_id, node_id=nd["node_id"]
                ).update(node_status="completed", quiz_passed=True)

        return {
            "path_id": new_path_id,
            "regenerated": True,
            "nodes": result["nodes"],
        }

    # ── 内部辅助 ──

    @staticmethod
    async def _unlock_next_node(path_id: int, current_order: int, user_id: int):
        """解锁下一顺序节点并自动生成资源"""
        next_node = await PathNode.filter(path_id=path_id, order_index=current_order + 1).first()
        if not next_node:
            return

        await UserPathProgress.filter(
            user_id=user_id, path_id=path_id, node_id=next_node.id
        ).update(node_status="unlocked")

        # 自动为新节点生成学习资源
        try:
            await PathService.generate_node_resources(path_id, next_node.id, user_id)
        except Exception:
            pass

    @staticmethod
    async def _update_portrait_from_mastery(user_id: int):
        """汇总知识掌握度 → 更新画像 traits"""
        from backend.src.models.exam_model import KnowledgeMastery

        records = await KnowledgeMastery.filter(user_id=user_id).all()
        if not records:
            return

        mastery_data = [
            {"tag": r.knowledge_tag, "level": r.mastery_level, "accuracy": round(r.correct_count / max(r.total_attempts, 1), 2)}
            for r in records
        ]

        from backend.src.models.portraitmodel import User_picture

        user = await User.filter(id=user_id).prefetch_related("picture").first()
        if not user:
            return
        picture = await user.picture
        if not picture:
            picture = await User_picture.create()
            user.picture = picture
            await user.save()

        existing = {}
        if picture.traits:
            try:
                existing = json.loads(picture.traits)
            except Exception:
                existing = {}

        existing["knowledge_mastery"] = mastery_data
        existing["updated_at"] = str(datetime.now())
        picture.traits = json.dumps(existing, ensure_ascii=False)
        await picture.save()
