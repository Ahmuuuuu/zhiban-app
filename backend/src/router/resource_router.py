import asyncio
import json
import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Depends, Body, Query, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.src.service.resource_service import ResourceService, _subscribe_task_sse, _unsubscribe_task_sse
from backend.src.service.skill_service import SkillService
from backend.src.schemas.resource import GenerateResourceRequest
from backend.src.schemas.skill import UpsertSkillRequest
from backend.src.utils.jwt import get_user_id_from_token, JWT_KEY, ALGORITHM
from jose import jwt, JWTError

router = APIRouter(prefix = "/resource", tags = ["学习资源生成"])


class ExportPptxRequest(BaseModel):
    title: str = Field(default="")
    slides: list[dict] = Field(default_factory=list)


def _clean_bullet_text(value: str) -> str:
    return re.sub(r"^[-*•\s]+", "", str(value or "").strip())


def _slides_to_markdown(title: str, slides: list[dict]) -> str:
    try:
        from backend.src.utils.slide_schema import slides_to_markdown
        return slides_to_markdown(title, slides)
    except Exception:
        pass

    blocks: list[str] = []
    for index, slide in enumerate(slides or []):
        slide_title = str(slide.get("title") or title or f"第 {index + 1} 页").strip()
        text = str(slide.get("text") or slide.get("content") or "").strip()
        notes = str(slide.get("notes") or slide.get("speaker_notes") or "").strip()
        lines = [f"# {slide_title}"]

        for raw_line in re.split(r"\r?\n|[;；]", text):
            line = _clean_bullet_text(raw_line)
            if line:
                lines.append(f"- {line}")

        if notes:
            for note_line in notes.splitlines():
                note_line = note_line.strip()
                if note_line:
                    lines.append(f"> {note_line}")

        blocks.append("\n".join(lines))

    return "\n---\n".join(blocks)


async def get_user_id_from_download(
    token : str | None = Header(None),
    t : str | None = Query(None, alias = "token"),
) -> int:
    """优先从 Header 取 token，下载链接可从 query 参数取"""
    actual = token or t
    if not actual:
        raise HTTPException(401, "未携带Token")
    try:
        payload = jwt.decode(actual, JWT_KEY, [ALGORITHM])
        uid = payload.get("sub")
        if uid is None:
            raise ValueError
        return int(uid)
    except (ValueError, JWTError, TypeError):
        raise HTTPException(401, "token无效或已过期")


# ═══════════════════════════════════════
#  生成
# ═══════════════════════════════════════

@router.post("/generate")
async def generate_resource(
    user_id : int = Depends(get_user_id_from_token),
    data : GenerateResourceRequest = Body(...)
):
    try :
        result = await ResourceService.generate_and_save(data.topic, user_id, data.resource_types, data.chat_group_id, bind_chat_history=data.bind_chat_history)
        return {"code" : 200, "msg" : "success", "data" : result}
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")


@router.post("/generate/stream")
async def generate_resource_stream(
    user_id : int = Depends(get_user_id_from_token),
    data : GenerateResourceRequest = Body(...)
):
    return StreamingResponse(
        ResourceService.generate_stream(data.topic, user_id, data.resource_types, data.chat_group_id, bind_chat_history=data.bind_chat_history),
        media_type = "text/event-stream",
        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ═══════════════════════════════════════════
#  任务系统
# ═══════════════════════════════════════════

@router.post("/generate/task")
async def create_generation_task(
    user_id: int = Depends(get_user_id_from_token),
    data: GenerateResourceRequest = Body(...),
):
    try:
        result = await ResourceService.create_task(data.topic, user_id, data.resource_types, data.chat_group_id, data.answers, bind_chat_history=data.bind_chat_history)
        return {"code": 200, "msg": "success", "data": result}
    except Exception:
        raise HTTPException(500, "创建任务失败")


@router.get("/generate/task/{task_id}")
async def get_generation_task(
    task_id: str,
    user_id: int = Depends(get_user_id_from_token),
):
    try:
        result = await ResourceService.get_task(task_id, user_id)
        if result is None:
            return {"code": 404, "msg": "任务不存在"}
        return {"code": 200, "msg": "success", "data": result}
    except Exception:
        raise HTTPException(500, "查询任务失败")


@router.get("/generate/tasks")
async def list_generation_tasks(
    user_id: int = Depends(get_user_id_from_token),
):
    try:
        result = await ResourceService.list_tasks(user_id)
        return {"code": 200, "msg": "success", "data": result}
    except Exception:
        raise HTTPException(500, "查询任务列表失败")


@router.get("/generate/task/{task_id}/stream")
async def stream_generation_task(
    task_id: str,
    request: Request,
    user_id: int = Depends(get_user_id_from_token),
):
    """SSE 订阅任务进度"""

    async def event_stream():
        q = _subscribe_task_sse(task_id)
        try:
            # 先推送当前状态
            task_data = await ResourceService.get_task(task_id, user_id)
            if task_data:
                if task_data["status"] in ("success", "failed"):
                    yield f"data: {json.dumps({'type': 'done', **task_data}, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                yield f"data: {json.dumps({'type': 'status', **task_data}, ensure_ascii=False)}\n\n"

            # 持续监听队列
            while True:
                if await request.is_disconnected():
                    break
                if q:
                    data = q.pop(0)
                    if data.get("type") == "__close__":
                        yield "data: [DONE]\n\n"
                        return
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                else:
                    await asyncio.sleep(0.3)
        finally:
            _unsubscribe_task_sse(task_id, q)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/list")
async def list_resources(user_id : int = Depends(get_user_id_from_token)):
    try :
        records = await ResourceService.list_resources(user_id)
        return {"code" : 200, "msg" : "success", "data" : records}
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")


# ═══════════════════════════════════════
#  Skill 管理
# ═══════════════════════════════════════

@router.post("/skill/upsert")
async def upsert_skill(
    user_id : int = Depends(get_user_id_from_token),
    data : UpsertSkillRequest = Body(...)
):
    try :
        result = await SkillService.upsert(user_id, data.resource_type, data.name, data.system_prompt)
        return {"code" : 200, "msg" : "success", "data" : result}
    except ValueError as e :
        return {"code" : 400, "msg" : str(e)}
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")


@router.get("/skill/list")
async def list_skills(user_id : int = Depends(get_user_id_from_token)):
    try :
        records = await SkillService.list_all(user_id)
        return {"code" : 200, "msg" : "success", "data" : records}
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")


@router.get("/skill/{resource_type}")
async def get_skill(
    resource_type : str,
    user_id : int = Depends(get_user_id_from_token)
):
    try :
        record = await SkillService.get(user_id, resource_type)
        if record is None :
            return {"code" : 404, "msg" : f"资源类型 '{resource_type}' 暂无定制 skill"}
        return {"code" : 200, "msg" : "success", "data" : record}
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")


@router.delete("/skill/{resource_type}")
async def delete_skill(
    resource_type : str,
    user_id : int = Depends(get_user_id_from_token)
):
    try :
        msg = await SkillService.delete(user_id, resource_type)
        if "不存在" in msg :
            return {"code" : 404, "msg" : msg}
        return {"code" : 200, "msg" : msg}
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")


# ═══════════════════════════════════════
#  资源 CRUD
# ═══════════════════════════════════════

@router.get("/{resource_id}")
async def get_resource(
    resource_id : int,
    user_id : int = Depends(get_user_id_from_token)
):
    try :
        record = await ResourceService.get_resource(resource_id, user_id)
        if record is None :
            return {"code" : 404, "msg" : "资源不存在"}
        return {"code" : 200, "msg" : "success", "data" : record}
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id : int,
    user_id : int = Depends(get_user_id_from_download)
):
    try :
        result = await ResourceService.download_resource(resource_id, user_id)
        if result is None :
            return {"code" : 404, "msg" : "资源不存在"}
        content, filename, media_type = result
        ascii_name = quote(filename, safe="")
        return StreamingResponse(
            iter([content]),
            media_type = media_type,
            headers = {"Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{ascii_name}"},
        )
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")


@router.post("/{resource_id}/export-pptx")
async def export_edited_pptx(
    resource_id: int,
    data: ExportPptxRequest = Body(...),
    user_id: int = Depends(get_user_id_from_download),
):
    try:
        resource = await ResourceService.get_resource(resource_id, user_id)
        if resource is None:
            return {"code": 404, "msg": "资源不存在"}

        markdown = _slides_to_markdown(data.title or resource.get("topic") or resource.get("title") or "", data.slides)
        if not markdown.strip():
            raise HTTPException(400, "没有可导出的幻灯片内容")

        try:
            from backend.src.utils.pptx_generator import markdown_to_pptx
        except ImportError:
            raise HTTPException(500, "PPT 导出需要安装 python-pptx 依赖")

        content = markdown_to_pptx(markdown)
        if not content:
            raise HTTPException(400, "PPT 内容为空，无法导出")

        filename_base = data.title or resource.get("topic") or resource.get("title") or "edited-presentation"
        filename = re.sub(r'[\\/:*?"<>|]+', "_", str(filename_base)).strip() or "edited-presentation"
        if not filename.lower().endswith(".pptx"):
            filename = f"{filename}.pptx"
        ascii_name = quote(filename, safe="")

        return StreamingResponse(
            iter([content]),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{ascii_name}"},
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "PPT 导出失败")


@router.post("/{resource_id}/like")
async def toggle_like(
    resource_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    try:
        result = await ResourceService.toggle_like(resource_id, user_id)
        return {"code": 200, "msg": "success", "data": result}
    except ValueError as e:
        return {"code": 404, "msg": str(e)}
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.post("/{resource_id}/favorite")
async def toggle_favorite(
    resource_id: int,
    user_id: int = Depends(get_user_id_from_token),
):
    try:
        result = await ResourceService.toggle_favorite(resource_id, user_id)
        return {"code": 200, "msg": "success", "data": result}
    except ValueError as e:
        return {"code": 404, "msg": str(e)}
    except Exception:
        raise HTTPException(500, "服务器错误")


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id : int,
    user_id : int = Depends(get_user_id_from_token)
):
    try :
        ok = await ResourceService.delete_resource(resource_id, user_id)
        if not ok :
            return {"code" : 404, "msg" : "资源不存在"}
        return {"code" : 200, "msg" : "删除成功"}
    except HTTPException :
        raise
    except Exception :
        raise HTTPException(500, "服务器错误")
