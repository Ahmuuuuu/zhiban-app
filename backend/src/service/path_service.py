"""学习路径服务 — 生成、资源、测验、进度追踪"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

import asyncio

from backend.src.ai_core.llm_config import llm


from backend.src.models.path_model import LearningPath, PathNode, UserPathProgress
from backend.src.models.exam_model import ExamRecord, KnowledgeMastery
from backend.src.service.notification_service import check_and_create_node_unlocked, check_and_create_quiz_failed
from backend.src.models.resource_model import GeneratedResource
from backend.src.models.portraitmodel import User_picture
from backend.src.models.usermodel import User
from backend.src.utils.database import init_db
from backend.src.utils.prompt_loader import load_prompt, fill_prompt
from backend.src.service.portrait_service import format_portrait, PortraitRadarService, build_learning_guidance
from backend.src.service.exam_service import ExamService, _normalize_db_answer, _parse_multi_ans
from backend.src.service.resource_service import ResourceService
from backend.src.utils.knowledge_base import search as kb_search
from backend.src.utils.json_parser import parse_llm_json


def _compute_node_count(subject: str, picture) -> int:
    """动态计算路径节点数 (8-30)，基于 knowbase 水平和学科广度"""
    traits = {}
    if picture and picture.traits:
        try:
            traits = json.loads(picture.traits)
        except (json.JSONDecodeError, TypeError):
            pass
    knowbase_data = traits.get("knowbase", {})
    if isinstance(knowbase_data, dict):
        kb_val = knowbase_data.get("value", "3")
    else:
        kb_val = str(knowbase_data or "3")
    try:
        kb_level = float(kb_val)
    except (ValueError, TypeError):
        kb_level = 3.0

    broad_keywords = ["学", "原理", "概论", "导论", "基础", "体系", "框架", "进阶", "实战", "应用"]
    narrow_keywords = ["定理", "公式", "法则", "方法", "工具", "技巧", "模型"]
    is_broad = any(kw in subject for kw in broad_keywords)
    is_narrow = any(kw in subject for kw in narrow_keywords)

    base = 10 if is_narrow else (20 if is_broad else 15)
    wc = len(subject)
    if wc <= 3:
        base = max(8, base - 2)
    elif wc >= 8:
        base = min(30, base + 3)

    level_adjust = int((kb_level - 3) * 2.0)
    return max(8, min(30, base + level_adjust))


class PathService:

    @staticmethod
    async def generate_path(subject: str, user_id: int, difficulty: str = "medium", node_count: int = 0) -> dict:
        """LLM 生成路径结构 → 存库（node_count=0 自动计算）。同用户同 subject 已存在则跳过。"""
        await init_db()

        existing = await LearningPath.filter(user_id=user_id, subject=subject).first()
        if existing:
            return {"path_id": existing.id, "subject": subject, "nodes": [], "cached": True}

        portrait_context = "暂无画像数据"
        mastery_context = "暂无掌握度数据"
        kb_context = "暂无相关知识库"
        learning_guidance = ""

        user = await User.filter(id=user_id).first()
        if user:
            picture = await user.picture
            if picture:
                try:
                    radar_data = await PortraitRadarService.get(user_id)
                except Exception:
                    radar_data = None
                portrait_context = "\n".join(format_portrait(picture, show_missing=False, radar_data=radar_data))
                if node_count <= 0:
                    node_count = _compute_node_count(subject, picture)
            else:
                if node_count <= 0:
                    node_count = 5

        try:
            learning_guidance = await build_learning_guidance(user_id) or ""
        except Exception:
            logger.exception("学习指导生成失败 user_id=%s", user_id)

        try:
            kb_result = await kb_search(subject, top_k=5, user_id=user_id)
            if kb_result and "暂无" not in kb_result:
                kb_context = kb_result
        except Exception:
            logger.exception("知识库搜索失败 subject=%s user_id=%s", subject, user_id)

        mastery_records = await KnowledgeMastery.filter(user_id=user_id).all()
        if mastery_records:
            lines = []
            for m in mastery_records:
                acc = round(m.correct_count / max(m.total_attempts, 1), 2)
                lines.append(f"- {m.knowledge_tag}: {m.mastery_level}（准确率 {acc}，练习 {m.total_attempts} 次）")
            mastery_context = "已掌握知识点：\n" + "\n".join(lines)

        template = load_prompt("path/path_generation")
        prompt_text = fill_prompt(
            template,
            subject=subject,
            difficulty=difficulty,
            node_count=str(node_count),
            portrait_context=portrait_context,
            mastery_context=mastery_context,
            kb_context=kb_context,
            learning_guidance=learning_guidance,
        )

        try:
            response = await llm.ainvoke(prompt_text)
            result = parse_llm_json(response.content)
            if not isinstance(result, dict):
                result = {}
        except Exception:
            logger.exception("LLM 路径生成调用失败 subject=%s", subject)
            return {"error": "路径生成失败"}

        nodes_data = result.get("nodes", [])
        if not nodes_data:
            return {"error": "LLM 未返回有效节点"}

        from tortoise.exceptions import IntegrityError
        try:
            path = await LearningPath.create(
                subject=subject,
                difficulty=difficulty,
                node_count=len(nodes_data),
                cover_tags=json.dumps([n.get("topic") for n in nodes_data], ensure_ascii=False),
                user=user,
            )
        except IntegrityError:
            existing = await LearningPath.filter(user_id=user_id, subject=subject).first()
            if existing:
                return {"path_id": existing.id, "subject": subject, "nodes": [], "cached": True}
            raise

        nodes = []
        created_nodes = []
        for nd in nodes_data:
            node = await PathNode.create(
                path=path,
                topic=nd.get("topic", ""),
                knowledge_tags=json.dumps(nd.get("knowledge_tags", []), ensure_ascii=False),
                order_index=nd.get("order_index", len(nodes) + 1),
                prerequisites=json.dumps(nd.get("prerequisites", []), ensure_ascii=False),
                resource_types=json.dumps(nd.get("resource_types", ["document", "ppt", "mindmap", "video"]), ensure_ascii=False),
                quiz_config=json.dumps(nd.get("quiz_config", {"count": 5, "threshold": 0.7}), ensure_ascii=False),
            )
            created_nodes.append(node)
            nodes.append({
                "node_id": node.id,
                "topic": node.topic,
                "order_index": node.order_index,
                "knowledge_tags": json.loads(node.knowledge_tags) if node.knowledge_tags else [],
                "prerequisites": json.loads(node.prerequisites) if node.prerequisites else [],
                "resource_types": json.loads(node.resource_types) if node.resource_types else [],
                "quiz_config": json.loads(node.quiz_config) if node.quiz_config else {},
            })

        # 自动 enroll 创建者：初始化进度 + 首节点解锁
        sorted_nodes = sorted(created_nodes, key=lambda n: n.order_index)
        progress_list = []
        first_node = None
        for i, node in enumerate(sorted_nodes):
            has_prereqs = node.prerequisites and json.loads(node.prerequisites)
            status = "unlocked" if (i == 0 or not has_prereqs) else "locked"
            await UserPathProgress.create(
                user_id=user_id,
                path=path,
                node=node,
                node_status=status,
            )
            progress_list.append({"node_id": node.id, "topic": node.topic, "status": status})
            if status == "unlocked":
                first_node = node

        # 通知：首节点已解锁
        if first_node:
            await check_and_create_node_unlocked(user_id, first_node.topic, path.id, first_node.id)

        # 只为首个解锁节点预生成资源 + 测验，其余按需懒加载
        node_results = {}
        if first_node:
            async def gen_resources():
                try:
                    r = await PathService.generate_node_resources(path.id, first_node.id, user_id)
                    return r.get("resource_ids", [])
                except Exception:
                    logger.exception(f"首节点 {first_node.id}({first_node.topic}) 资源生成失败")
                    return []

            async def gen_quiz():
                try:
                    q = await PathService.generate_node_quiz(path.id, first_node.id, user_id)
                    return q.get("session_id"), q.get("questions", [])
                except Exception:
                    logger.exception("首节点测验生成失败 node_id=%s topic=%s", first_node.id, first_node.topic)
                    return None, []

            res_ids, (session_id, questions) = await asyncio.gather(gen_resources(), gen_quiz())
            node_results[first_node.id] = {
                "node_id": first_node.id,
                "resource_ids": res_ids,
                "session_id": session_id,
                "quiz_count": len(questions),
            }

        return {
            "path_id": path.id,
            "subject": path.subject,
            "difficulty": path.difficulty,
            "node_count": path.node_count,
            "nodes": nodes,
            "progress": progress_list,
            "node_results": node_results,
        }

    @staticmethod
    async def list_paths(user_id: int) -> list[dict]:
        """列出当前用户的所有路径"""
        paths = await LearningPath.filter(user_id=user_id).order_by("-created_at").prefetch_related("nodes").all()

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
    async def get_path(path_id: int, user_id: int) -> dict | None:
        """获取路径详情含节点列表（仅返回本人创建或已加入的路径）"""
        path = await LearningPath.filter(id=path_id).prefetch_related("nodes").first()
        if not path:
            return None

        # 权限检查：仅创建者可查看
        if path.user_id != user_id:
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
            status = "unlocked" if (i == 0 or not has_prereqs) else "locked"
            await UserPathProgress.create(
                user_id=user_id,
                path=path,
                node=node,
                node_status=status,
            )
            if status == "unlocked" and not first_node:
                first_node = node
            created.append({"node_id": node.id, "topic": node.topic, "status": status})

        # 通知：首节点已解锁
        if first_node:
            await check_and_create_node_unlocked(user_id, first_node.topic, path_id, first_node.id)

        # 自动为首个节点生成资源
        resources = []
        if first_node:
            try:
                res_result = await PathService.generate_node_resources(path_id, first_node.id, user_id)
                resources = res_result.get("resource_ids", [])
            except Exception:
                logger.exception("自动生成首节点资源失败 path_id=%s node_id=%s", path_id, first_node.id)

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
            res_records = await GeneratedResource.filter(id__in=resource_ids).all()
            for r in res_records:
                item = {"resource_id": r.id, "topic": r.topic, "resource_type": r.resource_type}
                if r.file_url:
                    item["file_url"] = r.file_url
                    item["url"] = r.file_url
                    item["preview_url"] = r.file_url
                if r.resource_type == "html" and r.content:
                    try:
                        c = json.loads(r.content)
                        if c.get("presentation_id"):
                            item["presentation_id"] = c["presentation_id"]
                    except (json.JSONDecodeError, TypeError):
                        pass
                resources.append(item)

        return {
            "node_id": node.id,
            "topic": node.topic,
            "order_index": node.order_index,
            "knowledge_tags": json.loads(node.knowledge_tags) if node.knowledge_tags else [],
            "prerequisites": json.loads(node.prerequisites) if node.prerequisites else [],
            "resource_types": json.loads(node.resource_types) if node.resource_types else [],
            "quiz_config": json.loads(node.quiz_config) if node.quiz_config else {},
            "quiz_session_id": progress.quiz_session_id if progress else None,
            "progress": {
                "status": progress.node_status if progress else "not_enrolled",
                "quiz_passed": progress.quiz_passed if progress else False,
                "narration_status": progress.narration_status if progress else "",
                "resources": resources,
            },
        }

    # ── 内部工具方法（两条生成路径复用） ──

    @staticmethod
    async def _check_existing_resources(user_id: int, topic: str, resource_types: list[str] | None = None):
        """查已有资源 → (已有记录列表, 缺失类型列表)
        node 配置中的 "video" 映射到 DB 中的 "html" 资源类型。"""
        if resource_types is None:
            resource_types = ["document", "ppt", "mindmap", "video"]
        existing_records = []
        missing_types = []
        for rt in resource_types:
            db_type = "html" if rt == "video" else rt
            r = await GeneratedResource.filter(user_id=user_id, topic=topic, resource_type=db_type).first()
            if r:
                existing_records.append(r)
            else:
                missing_types.append(rt)
        return existing_records, missing_types

    @staticmethod
    async def _update_progress_resource_ids(progress, all_ids: list[int]):
        """写入 resource_ids 并推进节点状态"""
        update_fields = {"resource_ids": json.dumps(all_ids, ensure_ascii=False)}
        if progress.node_status == "unlocked":
            update_fields["node_status"] = "in_progress"
            update_fields["started_at"] = datetime.now()
        await UserPathProgress.filter(id=progress.id).update(**update_fields)

    # ── 资源生成 ──

    @staticmethod
    async def generate_node_resources_stream(path_id: int, node_id: int, user_id: int):
        """流式为节点生成学习资源（SSE）—— 生成好一个推送一个"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            yield f"data: {json.dumps({'type': 'error', 'detail': '节点不存在'}, ensure_ascii=False)}\n\n"
            return

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()
        if not progress:
            yield f"data: {json.dumps({'type': 'error', 'detail': '未加入该路径'}, ensure_ascii=False)}\n\n"
            return

        topic = node.topic
        node_resource_types = json.loads(node.resource_types) if node.resource_types else ["document", "ppt", "mindmap"]
        # 学习路径节点始终带 video（HTML 动态课件），LLM 生成时可能遗漏
        if "video" not in node_resource_types:
            node_resource_types = list(node_resource_types) + ["video"]
        existing_records, missing_types = await PathService._check_existing_resources(user_id, topic, node_resource_types)

        for r in existing_records:
            pres_id = 0
            if r.resource_type == "html" and r.content:
                try:
                    c = json.loads(r.content)
                    pres_id = c.get("presentation_id", 0)
                except (json.JSONDecodeError, TypeError):
                    pass
            yield _resource_sse(r, presentation_id=pres_id)

        if not missing_types:
            all_ids = [r.id for r in existing_records]
            await PathService._update_progress_resource_ids(progress, all_ids)
            yield _sse_done(all_ids)
            return

        # video/html 不由 LLM 生成；PPT 是 HTML 课件的基础，缺失就自动补
        gen_types = [t for t in missing_types if t != "video"]
        if "ppt" not in gen_types and "ppt" not in [r.resource_type for r in existing_records]:
            gen_types.insert(0, "ppt")

        if gen_types:
            yield f"data: {json.dumps({'type': 'status', 'msg': f'开始生成 {len(gen_types)} 种资源...'}, ensure_ascii=False)}\n\n"

        generated_ids = []
        ppt_id = None
        if gen_types:
            from backend.src.service.resource_service import ResourceService
            async for event_str in ResourceService.generate_stream(
                topic=topic, user_id=user_id, resource_types=gen_types, skip_review=True,
            ):
                yield event_str
                if event_str.startswith("data:") and "[DONE]" not in event_str:
                    try:
                        data = json.loads(event_str[5:].strip())
                        if data.get("done"):
                            for r in data.get("resources", []):
                                rid = r.get("resource_id")
                                if rid:
                                    generated_ids.append(rid)
                                    if r.get("file_type") == "ppt":
                                        ppt_id = rid
                    except (json.JSONDecodeError, KeyError):
                        pass

        all_ids = [r.id for r in existing_records] + generated_ids

        # PPT → 生成 HTML 动态课件（复用已有的 presentation_service.generate 逻辑：
        #   Presentation 记录 + 骨架 HTML + 后台补音频 + 前端轮询状态）
        # 优先用新生成的 ppt_id，否则从已有记录中找
        html_result = None
        target_ppt_id = ppt_id
        if not target_ppt_id:
            ppt_from_existing = next((r for r in existing_records if r.resource_type == "ppt"), None)
            if ppt_from_existing:
                target_ppt_id = ppt_from_existing.id

        if target_ppt_id:
            ppt_record = await GeneratedResource.filter(id=target_ppt_id).first()
            if ppt_record:
                try:
                    html_result = await _create_video_html(topic, user_id, ppt_record)
                except Exception:
                    logger.exception("动态课件生成失败 topic=%s ppt_id=%s", topic, target_ppt_id)
                if html_result:
                    all_ids.append(html_result["html_id"])
                    html_record = await GeneratedResource.filter(id=html_result["html_id"]).first()
                    if html_record:
                        yield _resource_sse(html_record, presentation_id=html_result["presentation_id"])

        await PathService._update_progress_resource_ids(progress, all_ids)
        yield _sse_done(all_ids)

    @staticmethod
    async def generate_node_resources(path_id: int, node_id: int, user_id: int) -> dict:
        """为节点获取学习资源 — 已有则复用，没有则生成"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            raise ValueError("节点不存在")

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()
        if not progress:
            raise ValueError("未加入该路径")

        topic = node.topic
        node_resource_types = json.loads(node.resource_types) if node.resource_types else ["document", "ppt", "mindmap"]
        # 学习路径节点始终带 video（HTML 动态课件）
        if "video" not in node_resource_types:
            node_resource_types = list(node_resource_types) + ["video"]
        existing_records, missing_types = await PathService._check_existing_resources(user_id, topic, node_resource_types)

        gen_types = [t for t in missing_types if t != "video"]
        if "ppt" not in gen_types and "ppt" not in [r.resource_type for r in existing_records]:
            gen_types.insert(0, "ppt")

        generated_ids = []
        if gen_types:
            try:
                saved = await ResourceService.generate_and_save(
                    topic=topic,
                    user_id=user_id,
                    resource_types=gen_types,
                )
                generated_ids = [r.get("resource_id") or r.get("id") for r in saved if r]
            except Exception:
                logger.exception("ResourceService.generate_and_save 失败 topic=%s types=%s", topic, gen_types)

        all_ids = [r.id for r in existing_records] + generated_ids

        # PPT → 生成 HTML 动态课件（复用已有的 presentation_service 逻辑）
        ppt_record = None
        html_result = None
        ppt_record = await GeneratedResource.filter(
            id__in=all_ids, user_id=user_id, resource_type="ppt"
        ).first()
        if ppt_record:
            try:
                html_result = await _create_video_html(topic, user_id, ppt_record)
            except Exception:
                logger.exception("动态课件生成失败 topic=%s ppt_id=%s", topic, ppt_record.id)
            if html_result:
                all_ids.append(html_result["html_id"])

        await PathService._update_progress_resource_ids(progress, all_ids)

        resources = []
        if all_ids:
            records = await GeneratedResource.filter(id__in=all_ids, user_id=user_id).all()
            record_map = {r.id: r for r in records}
            for rid in all_ids:
                r = record_map.get(rid)
                if not r:
                    continue
                item = {
                    "resource_id": r.id,
                    "topic": r.topic,
                    "resource_type": r.resource_type,
                    "content": r.content,
                    "review_passed": r.review_passed,
                    "download_url": f"/resource/{r.id}/download",
                    "cover_url": r.cover_url,
                    "view_count": r.view_count,
                    "download_count": r.download_count,
                }
                if r.file_url:
                    item["file_url"] = r.file_url
                    item["url"] = r.file_url
                    item["preview_url"] = r.file_url
                resources.append(item)

        return {
            "node_id": node_id,
            "resource_ids": all_ids,
            "resources": resources,
            "generated_count": len(generated_ids),
            "reused_count": len(existing_records),
        }

    @staticmethod
    async def _check_resource_viewed(node_id: int, user_id: int) -> tuple[bool, int]:
        """检查节点资源是否已查看，返回 (has_viewed, total_view_count)"""
        progress = await UserPathProgress.filter(user_id=user_id, node_id=node_id).first()
        if not progress or not progress.resource_ids:
            return False, 0
        rids = json.loads(progress.resource_ids) if progress.resource_ids else []
        if not rids:
            return False, 0
        resources = await GeneratedResource.filter(id__in=rids).all()
        total_views = sum(r.view_count or 0 for r in resources)
        return total_views > 0, total_views

    @staticmethod
    async def generate_node_quiz(path_id: int, node_id: int, user_id: int, pre_generate: bool = False) -> dict:
        """为节点获取测验题目 — 已有则复用，没有则生成

        Args:
            pre_generate: 预生成模式，跳过资源查看门禁，使用默认难度"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            raise ValueError("节点不存在")

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()
        if not progress:
            raise ValueError("未加入该路径")

        quiz_config = json.loads(node.quiz_config) if node.quiz_config else {"count": 5, "threshold": 0.7}

        # 已有预生成的 session → 直接复用
        if progress.quiz_session_id:
            existing = await ExamService.get_session(progress.quiz_session_id, user_id)
            if existing and existing.get("total_questions", 0) > 0:
                # 查该 session 的 difficulty（从第一题推测）
                first_record = await ExamRecord.filter(session_id=progress.quiz_session_id).prefetch_related("question").first()
                return {
                    "node_id": node_id,
                    "session_id": progress.quiz_session_id,
                    "questions": existing.get("records", []),
                    "quiz_config": quiz_config,
                    "reused": True,
                    "difficulty": first_record.question.difficulty if first_record and first_record.question else "medium",
                }

        # 没有则生成
        count = quiz_config.get("count", 10)

        if not pre_generate:
            # 检查资源是否已查看，根据查看次数决定难度
            has_viewed, total_views = await PathService._check_resource_viewed(node_id, user_id)
            if not has_viewed:
                return {"blocked": True, "reason": "请先学习当前节点的学习资料后再进行检测"}

            if total_views <= 1:
                difficulty = "easy"
            elif total_views <= 3:
                difficulty = "medium"
            else:
                difficulty = "hard"
        else:
            difficulty = "medium"

        # 收集节点关联资源上的用户笔记，注入出题上下文
        user_notes = ""
        try:
            resource_ids = json.loads(progress.resource_ids) if progress.resource_ids else []
            if resource_ids:
                from backend.src.service.annotation_service import AnnotationService
                user_notes = await AnnotationService.collect_notes_for_quiz(user_id, resource_ids)
        except Exception:
            logger.exception("收集笔记失败 path_id=%s node_id=%s user_id=%s", path_id, node_id, user_id)

        result = await ExamService.generate_and_save(
            topic=node.topic,
            user_id=user_id,
            question_types=["single_choice"] * 5 + ["multi_choice"] + ["true_false"] * 2 + ["fill_blank"] * 2,
            count=count,
            difficulty=difficulty,
            node_id=node_id,
            user_notes=user_notes,
        )

        sid = result.get("session_id")
        if sid:
            await UserPathProgress.filter(id=progress.id).update(quiz_session_id=sid)

        return {
            "node_id": node_id,
            "session_id": sid,
            "questions": result.get("questions", []),
            "quiz_config": quiz_config,
            "difficulty": difficulty,
            "reused": False,
        }

    @staticmethod
    async def generate_node_quiz_stream(path_id: int, node_id: int, user_id: int):
        """流式为节点生成测验题目 → SSE 推送进度"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            yield f"data: {json.dumps({'type': 'error', 'detail': '节点不存在'}, ensure_ascii=False)}\n\n"
            return

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()
        if not progress:
            yield f"data: {json.dumps({'type': 'error', 'detail': '未加入该路径'}, ensure_ascii=False)}\n\n"
            return

        quiz_config = json.loads(node.quiz_config) if node.quiz_config else {"count": 5, "threshold": 0.7}

        # 已有预生成的 session → 秒返
        if progress.quiz_session_id:
            existing = await ExamService.get_session(progress.quiz_session_id, user_id)
            if existing and existing.get("total_questions", 0) > 0:
                yield f"data: {json.dumps({'type': 'status', 'msg': '复用已有测验题目'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'session_id': progress.quiz_session_id, 'quiz_config': quiz_config, 'question_count': existing.get('total_questions', 0), 'reused': True}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return

        count = quiz_config.get("count", 10)
        difficulty = "medium"

        # 检查资源是否已查看，根据查看次数决定难度
        has_viewed, total_views = await PathService._check_resource_viewed(node_id, user_id)
        if not has_viewed:
            yield f"data: {json.dumps({'type': 'blocked', 'reason': '请先学习当前节点的学习资料后再进行检测'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        if total_views <= 1:
            difficulty = "easy"
        elif total_views <= 3:
            difficulty = "medium"
        else:
            difficulty = "hard"

        # 收集节点关联资源上的用户笔记，注入出题上下文
        user_notes = ""
        try:
            resource_ids = json.loads(progress.resource_ids) if progress.resource_ids else []
            if resource_ids:
                from backend.src.service.annotation_service import AnnotationService
                user_notes = await AnnotationService.collect_notes_for_quiz(user_id, resource_ids)
        except Exception:
            logger.exception("收集笔记失败 path_id=%s node_id=%s user_id=%s", path_id, node_id, user_id)

        # 流式生成并透传事件，截获 done 写 quiz_session_id
        async for event in ExamService.generate_and_save_stream(
            topic=node.topic,
            user_id=user_id,
            question_types=["single_choice"] * 5 + ["multi_choice"] + ["true_false"] * 2 + ["fill_blank"] * 2,
            count=count,
            difficulty=difficulty,
            node_id=node_id,
            user_notes=user_notes,
        ):
            if isinstance(event, str) and event.startswith("data:"):
                data_str = event[5:].strip()
                if data_str == "[DONE]":
                    yield event
                    continue
                try:
                    payload = json.loads(data_str)
                    if payload.get("type") == "done":
                        session_id = payload.get("session_id")
                        if session_id:
                            await UserPathProgress.filter(id=progress.id).update(quiz_session_id=session_id)
                        payload["quiz_config"] = quiz_config
                        payload["difficulty"] = difficulty
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        continue
                    yield event
                except json.JSONDecodeError:
                    yield event
            else:
                yield event

    @staticmethod
    async def submit_node_quiz(path_id: int, node_id: int, user_id: int, session_id: str, answers: dict[str, str] | None = None, correct_answers: dict[str, str] | None = None) -> dict:
        """提交节点测验结果 → 评分 → 门禁 → 解锁下一节点 → 更新画像

        answers: 可选，{question_id_str: user_answer}。传入则直接判分并写入 ExamRecord，
        绕过逐题 submitExamAnswer 调用不可靠的问题。
        """
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            raise ValueError("节点不存在")

        progress = await UserPathProgress.filter(user_id=user_id, path_id=path_id, node_id=node_id).first()
        if not progress:
            raise ValueError("未加入该路径")

        # 如果传入了 answers，直接在此判分写入
        direct_results = []  # 内存判分结果，兜底用
        if answers:
            logger.info("submit_node_quiz 收到 %d 个答案，直接判分 node_id=%s session_id=%r", len(answers), node_id, session_id)
            # 加载该 session 下已有的占位记录
            existing_records = await ExamRecord.filter(
                session_id=session_id, user_id=user_id
            ).prefetch_related("question").all()
            if not existing_records:
                existing_records = await ExamRecord.filter(
                    session_id=session_id, user_id=user_id, node_id=node_id
                ).prefetch_related("question").all()

            record_by_qid = {}
            for r in existing_records:
                record_by_qid[r.question_id] = r

            for question_id_str, user_answer in answers.items():
                try:
                    qid = int(question_id_str)
                except (ValueError, TypeError):
                    continue
                if not user_answer:
                    continue

                question = None
                existing = record_by_qid.get(qid)
                if existing and existing.question:
                    question = existing.question
                if not question:
                    question = await ExamQuestion.filter(id=qid).first()

                correct_answer = ""
                qt = ""
                if question:
                    correct_answer = _normalize_db_answer(question.answer)
                    qt = (question.question_type or "").lower()
                elif correct_answers:
                    # 兜底：题目不在 DB，用前端传来的正确答案直接比对
                    correct_answer = _normalize_db_answer(correct_answers.get(question_id_str, ""))
                if not correct_answer:
                    continue

                if qt == "multi_choice":
                    try:
                        user_set = _parse_multi_ans(user_answer)
                        correct_set = _parse_multi_ans(correct_answer)
                        is_correct = (user_set == correct_set)
                    except Exception:
                        is_correct = user_answer.strip().upper() == correct_answer
                else:
                    is_correct = user_answer.strip().upper() == correct_answer

                score = 1.0 if is_correct else 0.0

                logger.info("submit_node_quiz 判分 qid=%s type=%s correct_answer=%r user_answer=%r is_correct=%s",
                            qid, qt, correct_answer, user_answer, is_correct)

                # 记录内存判分结果（兜底用）
                direct_results.append({
                    "question_id": qid,
                    "is_correct": is_correct,
                    "correct_answer": correct_answer,
                    "user_answer": user_answer,
                    "score": score,
                })

                if existing:
                    existing.user_answer = user_answer
                    existing.is_correct = is_correct
                    existing.score = score
                    await existing.save()
                else:
                    await ExamRecord.create(
                        question=question,
                        user_id=user_id,
                        user_answer=user_answer,
                        is_correct=is_correct,
                        score=score,
                        session_id=session_id,
                        node_id=node_id,
                    )

        # 从 session 汇总成绩
        records = await ExamRecord.filter(session_id=session_id, user_id=user_id).order_by("id").prefetch_related("question").all()
        if not records:
            records = await ExamRecord.filter(session_id=session_id, user_id=user_id, node_id=node_id).order_by("id").prefetch_related("question").all()
        logger.info("submit_node_quiz node_id=%s user_id=%s session_id=%r found %d records", node_id, user_id, session_id, len(records))
        latest_by_question = {}
        for r in records:
            latest_by_question[r.question_id] = r
        records = list(latest_by_question.values())
        judged = [r for r in records if r.is_correct is not None]
        if not judged:
            # 兜底：如果传了 answers，直接用内存判分结果，不依赖 DB 记录
            if answers and direct_results:
                correct = sum(1 for r in direct_results if r["is_correct"])
                score = round(correct / len(direct_results) * 100, 1) if direct_results else 0.0
                judged_questions = direct_results
            else:
                return {"error": "该会话无已判分的答题记录"}
        else:
            correct = sum(1 for r in judged if r.is_correct)
            score = round(correct / len(judged) * 100, 1) if judged else 0.0
            judged_questions = [
                {
                    "question_id": r.question_id,
                    "is_correct": r.is_correct,
                    "correct_answer": _normalize_db_answer(r.question.answer) if r.question else "",
                    "user_answer": r.user_answer,
                    "score": float(r.score or 0),
                }
                for r in judged
            ]
        quiz_config = json.loads(node.quiz_config) if node.quiz_config else {"count": 5, "threshold": 0.7}
        threshold = quiz_config.get("threshold", 0.7)
        passed = score >= threshold * 100

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
            await check_and_create_quiz_failed(user_id, node.topic, path_id, node_id)

        # 更新画像 traits
        await PathService._update_portrait_from_mastery(user_id)

        return {
            "node_id": node_id,
            "total_questions": len(judged_questions),
            "correct_count": correct,
            "score": score,
            "threshold": threshold,
            "passed": passed,
            "node_status": progress.node_status,
            "judged_questions": judged_questions,
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

    @staticmethod
    async def update_node(path_id: int, node_id: int, user_id: int, **fields) -> dict:
        """更新节点属性：topic, knowledge_tags, resource_types, quiz_config, order_index 等"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            raise ValueError("节点不存在")

        allowed = {"topic", "knowledge_tags", "resource_types", "quiz_config", "order_index"}
        updates = {}
        for k, v in fields.items():
            if k in allowed and v is not None:
                updates[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v

        if updates:
            await PathNode.filter(id=node_id).update(**updates)
            await node.refresh_from_db()

        return {
            "node_id": node.id,
            "topic": node.topic,
            "knowledge_tags": json.loads(node.knowledge_tags) if node.knowledge_tags else [],
            "resource_types": json.loads(node.resource_types) if node.resource_types else [],
            "quiz_config": json.loads(node.quiz_config) if node.quiz_config else {},
            "order_index": node.order_index,
        }

    @staticmethod
    async def delete_node(path_id: int, node_id: int) -> bool:
        """删除节点（后续节点的 order_index 自动前移）"""
        node = await PathNode.filter(id=node_id, path_id=path_id).first()
        if not node:
            return False
        deleted_order = node.order_index
        await node.delete()

        # 后续节点前移
        later = await PathNode.filter(path_id=path_id, order_index__gt=deleted_order).all()
        for n in later:
            n.order_index -= 1
            await n.save()

        # 更新路径的 node_count
        count = await PathNode.filter(path_id=path_id).count()
        await LearningPath.filter(id=path_id).update(node_count=count)

        return True

    @staticmethod
    async def add_node(path_id: int, topic: str, user_id: int, **fields) -> dict:
        """在路径末尾追加一个新节点"""
        path = await LearningPath.filter(id=path_id).first()
        if not path:
            raise ValueError("路径不存在")

        max_order = await PathNode.filter(path_id=path_id).order_by("-order_index").first()
        next_order = (max_order.order_index + 1) if max_order else 1

        node = await PathNode.create(
            path=path,
            topic=topic,
            knowledge_tags=json.dumps(fields.get("knowledge_tags", []), ensure_ascii=False),
            order_index=fields.get("order_index", next_order),
            prerequisites=json.dumps(fields.get("prerequisites", []), ensure_ascii=False),
            resource_types=json.dumps(fields.get("resource_types", ["document", "ppt", "mindmap"]), ensure_ascii=False),
            quiz_config=json.dumps(fields.get("quiz_config", {"count": 5, "threshold": 0.7}), ensure_ascii=False),
        )

        await LearningPath.filter(id=path_id).update(node_count=await PathNode.filter(path_id=path_id).count())

        # 为新节点自动生成资源
        try:
            await PathService.generate_node_resources(path_id, node.id, user_id)
        except Exception:
            logger.exception("新节点资源生成失败 node_id=%s", node.id)

        return {
            "node_id": node.id,
            "topic": node.topic,
            "order_index": node.order_index,
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

        await check_and_create_node_unlocked(user_id, next_node.topic, path_id, next_node.id)

        # 自动为新节点生成学习资源 + 检测题
        try:
            await PathService.generate_node_resources(path_id, next_node.id, user_id)
        except Exception:
            logger.exception("自动生成下一节点资源失败 path_id=%s node_id=%s", path_id, next_node.id)
        try:
            await PathService.generate_node_quiz(path_id, next_node.id, user_id, pre_generate=True)
        except Exception:
            logger.exception("自动生成下一节点检测题失败 path_id=%s node_id=%s", path_id, next_node.id)

    @staticmethod
    async def _update_portrait_from_mastery(user_id: int):
        """汇总知识掌握度 → 同步更新画像 traits"""

        records = await KnowledgeMastery.filter(user_id=user_id).all()
        if not records:
            return

        mastery_data = [
            {"tag": r.knowledge_tag, "level": r.mastery_level, "accuracy": round(r.correct_count / max(r.total_attempts, 1), 2)}
            for r in records
        ]

        # 分化强项/弱项
        strengths = [m["tag"] for m in mastery_data if m["level"] in ("mastered", "proficient")]
        weaknesses = [m["tag"] for m in mastery_data if m["level"] == "beginner"]
        avg_accuracy = round(sum(m["accuracy"] for m in mastery_data) / len(mastery_data), 2)
        level_map = {"beginner": 1, "learning": 2, "proficient": 3, "mastered": 4}
        avg_level = sum(level_map.get(m["level"], 1) for m in mastery_data) / len(mastery_data)
        knowbase = round(min(avg_level, 5), 1)

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
            except (json.JSONDecodeError, TypeError):
                logger.warning("画像 traits JSON 解析失败 user_id=%s", user_id)
                existing = {}

        # 保留原始数据
        existing["knowledge_mastery"] = mastery_data
        existing["updated_at"] = str(datetime.now())

        # 同步核心画像维度
        existing["knowbase"] = {
            "value": str(knowbase),
            "confidence": min(0.95, 0.3 + avg_accuracy * 0.5),
            "source": "agent_inferred",
        }
        if strengths:
            existing["strengths"] = {
                "value": "、".join(strengths[:5]),
                "confidence": 0.85,
                "source": "agent_inferred",
            }
        if weaknesses:
            existing["weaknesses"] = {
                "value": "、".join(weaknesses[:5]),
                "confidence": 0.75,
                "source": "agent_inferred",
            }

        picture.traits = json.dumps(existing, ensure_ascii=False)
        await picture.save()

    # ── 轻量学习路径接口（供前端动态路径动画） ──

    @staticmethod
    async def get_current_path(user_id: int) -> dict | None:
        """返回用户当前活跃路径（含节点、进度、诊断）"""
        progress_record = await UserPathProgress.filter(user_id=user_id)\
            .order_by("-id").prefetch_related("path", "node").first()
        if not progress_record or not progress_record.path:
            return None

        path = progress_record.path
        path_id = path.id

        progresses = await UserPathProgress.filter(user_id=user_id, path_id=path_id)\
            .prefetch_related("node").all()
        progresses.sort(key=lambda p: p.node.order_index if p.node else 0)

        # 批量收集所有资源 ID → 一次查询
        all_resource_ids = []
        resource_ids_map = {}
        for p in progresses:
            if p.resource_ids:
                rids = json.loads(p.resource_ids)
                resource_ids_map[p.node_id] = rids
                all_resource_ids.extend(rids)

        resources_map = {}
        if all_resource_ids:
            res_records = await GeneratedResource.filter(id__in=all_resource_ids).all()
            for r in res_records:
                resources_map[r.id] = r

        nodes = []
        current_node_id = None
        for p in progresses:
            node = p.node
            if not node:
                continue
            status = p.node_status
            if status in ("unlocked", "in_progress") and not current_node_id:
                current_node_id = node.id

            # 组装 summary 文本
            knowledge_tags = json.loads(node.knowledge_tags) if node.knowledge_tags else []
            summary = f"学习{node.topic}" + (f"（{', '.join(knowledge_tags[:3])}）" if knowledge_tags else "")

            # 当前节点的学习资源列表
            node_resources = []
            for rid in resource_ids_map.get(node.id, []):
                r = resources_map.get(rid)
                if r:
                    ext = {"document": "md", "ppt": "pptx", "mindmap": "txt", "exercise": "md", "audio": "mp3", "html": "html", "video": "html"}.get(r.resource_type, "md")
                    item = {
                        "id": r.id,
                        "title": r.topic,
                        "resource_type": r.resource_type,
                        "file_type": ext,
                        "filename": f"{r.topic}_{r.resource_type}.{ext}",
                        "download_url": f"/resource/{r.id}/download",
                        "view_count": r.view_count or 0,
                    }
                    if r.file_url:
                        item["file_url"] = r.file_url
                        item["url"] = r.file_url
                        item["preview_url"] = r.file_url if r.resource_type == "html" else ""
                    if r.resource_type == "html" and r.content:
                        try:
                            c = json.loads(r.content)
                            if c.get("presentation_id"):
                                item["presentation_id"] = c["presentation_id"]
                        except (json.JSONDecodeError, TypeError):
                            pass
                    node_resources.append(item)

            # 计算该节点资源总查看次数
            node_total_views = sum(
                (resources_map.get(rid).view_count or 0) for rid in resource_ids_map.get(node.id, [])
                if resources_map.get(rid)
            )

            resource_types = json.loads(node.resource_types) if node.resource_types else ["document", "ppt", "mindmap"]
            nodes.append({
                "id": node.id,
                "title": node.topic,
                "type": "quiz" if node.quiz_config else "read",
                "status": status,
                "summary": summary,
                "knowledge_tags": knowledge_tags,
                "resource_types": resource_types,
                "resources": node_resources,
                "session_id": p.quiz_session_id,
                "narration_status": p.narration_status or "",
                "resources_viewed": node_total_views > 0,
                "total_views": node_total_views,
                "action_label": "开始测验" if node.quiz_config and status in ("unlocked", "in_progress") else "开始学习",
            })

        # 诊断
        mastery_records = await KnowledgeMastery.filter(user_id=user_id).all()
        weak_points = []
        latest_scores = []
        for m in mastery_records:
            acc = round(m.correct_count / max(m.total_attempts, 1), 2)
            if acc < 0.6:
                weak_points.append({"tag": m.knowledge_tag, "accuracy": acc, "level": m.mastery_level})
            if m.total_attempts > 0:
                latest_scores.append(acc)
        best_score = round(max(latest_scores) * 100) if latest_scores else 0
        latest_score = round(latest_scores[-1] * 100) if latest_scores else 0

        completed = sum(1 for p in progresses if p.node_status == "completed")
        total = len(progresses)

        diagnosis = {
            "weak_points": weak_points,
            "latest_score": latest_score,
            "best_score": best_score,
            "recommendation": "继续巩固薄弱知识点" if weak_points else "进度良好，继续保持",
        }

        # next_action
        next_action = None
        if current_node_id:
            cur_node = next((n for n in nodes if n["id"] == current_node_id), None)
            if cur_node:
                next_action = {
                    "label": cur_node["action_label"],
                    "type": cur_node["type"],
                    "target_id": cur_node["id"],
                }

        return {
            "path_id": path_id,
            "goal": path.subject,
            "stage": f"{completed}/{total}",
            "progress": round(completed / total * 100) if total else 0,
            "current_node_id": current_node_id,
            "nodes": nodes,
            "next_action": next_action,
            "diagnosis": diagnosis,
        }

    @staticmethod
    async def complete_node(node_id: int, user_id: int, session_id: str, answers: dict[str, str] | None = None, correct_answers: dict[str, str] | None = None) -> dict:
        """完成节点（提交测验）→ 返回更新后节点 + 新解锁节点

        answers: 前端传来的所有答案 {question_id_str: user_answer}，直接判分
        correct_answers: 前端传来的正确答案 {question_id_str: correct_answer}，DB 找不到题目时的兜底
        """
        node = await PathNode.filter(id=node_id).first()
        if not node:
            raise ValueError("节点不存在")

        progress = await UserPathProgress.filter(user_id=user_id, node_id=node_id)\
            .prefetch_related("path").first()
        if not progress:
            raise ValueError("未加入该路径")

        path_id = progress.path_id

        # 复用原有测验提交逻辑（传入 answers 直接判分）
        quiz_result = await PathService.submit_node_quiz(path_id, node_id, user_id, session_id, answers=answers, correct_answers=correct_answers)
        if "error" in quiz_result:
            raise ValueError(quiz_result["error"])

        # 当前节点更新后状态
        updated_progress = await UserPathProgress.filter(user_id=user_id, node_id=node_id)\
            .prefetch_related("node").first()
        updated_node = {
            "id": node_id,
            "title": node.topic,
            "status": updated_progress.node_status if updated_progress else "locked",
            "quiz_passed": quiz_result.get("passed", False),
            "score": quiz_result.get("score", 0),
        }

        # 新解锁的节点
        new_nodes = []
        next_node = await PathNode.filter(path_id=path_id, order_index=node.order_index + 1).first()
        if next_node:
            next_progress = await UserPathProgress.filter(
                user_id=user_id, path_id=path_id, node_id=next_node.id
            ).first()
            if next_progress and next_progress.node_status in ("unlocked", "in_progress"):
                # 确保下一节点的 quiz 已预生成
                quiz_session_id = None
                if next_node.quiz_config:
                    try:
                        quiz_result = await PathService.generate_node_quiz(path_id, next_node.id, user_id)
                        quiz_session_id = quiz_result.get("session_id")
                    except Exception:
                        logger.exception("下一节点测验预生成失败 path_id=%s node_id=%s", path_id, next_node.id)
                knowledge_tags = json.loads(next_node.knowledge_tags) if next_node.knowledge_tags else []
                new_nodes.append({
                    "id": next_node.id,
                    "title": next_node.topic,
                    "type": "quiz" if next_node.quiz_config else "read",
                    "status": "unlocked",
                    "summary": f"学习{next_node.topic}" + (f"（{', '.join(knowledge_tags[:3])}）" if knowledge_tags else ""),
                    "resource_ids": json.loads(next_progress.resource_ids) if next_progress and next_progress.resource_ids else [],
                    "session_id": quiz_session_id,
                    "action_label": "开始学习",
                })

        return {
            "node": updated_node,
            "new_nodes": new_nodes,
            "passed": quiz_result.get("passed", False),
            "score": quiz_result.get("score", 0),
        }


# ═══════════════════════════════════════
#  SSE 流式辅助函数
# ═══════════════════════════════════════

def _resource_sse(record, presentation_id: int = 0) -> str:
    """单个资源的 SSE 事件"""
    data = {
        "type": "resource",
        "resource_id": record.id,
        "resource_type": record.resource_type,
        "title": record.topic or "",
        "download_url": f"/resource/{record.id}/download",
    }
    if record.file_url:
        data["file_url"] = record.file_url
        data["url"] = record.file_url
        data["preview_url"] = record.file_url
    if presentation_id:
        data["presentation_id"] = presentation_id
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_done(all_ids: list[int]) -> str:
    """生成完成的 SSE 事件"""
    data = {"type": "done", "resource_ids": all_ids}
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _ppt_to_slides(content: str) -> list[dict]:
    """把 PPT markdown 解析为幻灯片列表"""
    import re
    raw_slides = re.split(r"\n---\n", (content or "").strip())
    slides = []
    for block in raw_slides:
        block = block.strip()
        if not block:
            continue
        title = ""
        bullets = []
        notes = []
        body_lines = []
        for line in block.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# ") or stripped.startswith("## "):
                title = stripped.lstrip("#").strip()
            elif stripped.startswith("> "):
                notes.append(stripped[2:].strip())
            elif stripped.startswith("- ") or stripped.startswith("* "):
                bullets.append(stripped[2:].strip())
            else:
                body_lines.append(stripped)
        if body_lines and not title:
            title = body_lines[0]
            body_lines = body_lines[1:]
        slides.append({
            "title": title,
            "bullets": bullets,
            "notes": "，".join(notes),
            "body": body_lines,
        })
    return slides


async def _create_video_html(topic: str, user_id: int, ppt_record) -> dict | None:
    """通过已有的 presentation_service 创建动态课件（含骨架→后台补音频→状态轮询）。
    返回 {"html_id": int, "presentation_id": int, "file_url": str} 或 None。"""
    from backend.src.service.presentation_service import generate as generate_presentation
    from backend.src.models.resource_model import GeneratedResource

    # 已有 HTML GeneratedResource 则复用
    existing_html = await GeneratedResource.filter(
        user_id=user_id, topic=topic, resource_type="html"
    ).first()
    if existing_html:
        try:
            content = json.loads(existing_html.content or "{}")
        except (json.JSONDecodeError, TypeError):
            content = {}
        pres_id = content.get("presentation_id", 0)
        return {"html_id": existing_html.id, "presentation_id": pres_id, "file_url": existing_html.file_url or ""}

    user = await User.filter(id=user_id).first()
    if not user:
        return None

    # 调用已有的 presentation 生成逻辑（骨架 + 后台补音频 + Presentation 记录）
    pres = await generate_presentation(topic, user_id)
    if not pres or "error" in pres:
        logger.error("课件生成失败 topic=%s error=%s", topic, pres.get("error") if pres else "unknown")
        return None

    html = await GeneratedResource.create(
        user=user, topic=topic, resource_type="html",
        content=json.dumps({
            "presentation_id": pres["id"],
            "slides": _ppt_to_slides(ppt_record.content or ""),
            "narration": [],
        }, ensure_ascii=False),
        file_url=pres["file_url"],
    )
    logger.info("动态课件已创建 html_id=%s presentation_id=%s", html.id, pres["id"])
    return {"html_id": html.id, "presentation_id": pres["id"], "file_url": pres["file_url"]}


def _safe_topic_filename(topic: str) -> str:
    return "".join(c for c in topic if c.isalnum() or c in " _-")[:30]
