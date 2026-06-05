"""图片生成服务 (讯飞 HiDream)"""

import os
import json
import base64
import hmac
import hashlib
import uuid
import asyncio
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
from pathlib import Path
from urllib.parse import urlencode
from dotenv import load_dotenv
import httpx

from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User
from backend.src.models.image_model import GeneratedImage
from backend.src.models.notification_model import Notification


HOST = "cn-huadong-1.xf-yun.com"
CREATE_PATH = "/v1/private/s3fd61810/create"
QUERY_PATH = "/v1/private/s3fd61810/query"

import logging
_logger = logging.getLogger("image_service")

_task_status: dict[str, dict] = {}


def _load_env():
    env_file = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_file)
    app_id = os.getenv("XF_APP_ID", "")
    api_key = os.getenv("XF_API_KEY", "")
    api_secret = os.getenv("XF_API_SECRET", "")
    if not all([app_id, api_key, api_secret]):
        raise RuntimeError("图片生成服务未配置，请在 .env 中设置 XF_APP_ID、XF_API_KEY、XF_API_SECRET")
    return app_id, api_key, api_secret


def _make_auth_url(path: str, api_key: str, api_secret: str) -> str:
    cur_time = datetime.now()
    date = format_date_time(mktime(cur_time.timetuple()))
    signature_origin = f"host: {HOST}\ndate: {date}\nPOST {path} HTTP/1.1"
    signature_sha = hmac.new(api_secret.encode(), signature_origin.encode(), digestmod=hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature_sha).decode()
    authorization_origin = f"api_key=\"{api_key}\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"{signature_b64}\""
    authorization = base64.b64encode(authorization_origin.encode()).decode()
    return f"https://{HOST}{path}?" + urlencode({
        "host": HOST, "date": date, "authorization": authorization,
    })


SAVE_DIR = Path(__file__).parent.parent.parent / "static" / "images"


async def _next_chat_group_id(user_id: int) -> int:
    latest = await ChatHistory.filter(user_id=user_id).order_by("-chat_group_id").first()
    if not latest or not latest.chat_group_id:
        return 1
    return latest.chat_group_id + 1


async def _ensure_chat_group_id(user_id: int, chat_group_id: int = 0) -> int:
    return chat_group_id if chat_group_id and chat_group_id > 0 else await _next_chat_group_id(user_id)


async def _save_image_history(info: dict, images: list[dict]) -> None:
    if info.get("history_saved"):
        return

    user = await User.filter(id=info.get("user_id")).first()
    if not user:
        return

    lines = ["已生成图片："]
    for image in images:
        label = image.get("filename") or "生成图片"
        url = image.get("url") or ""
        lines.append(f"- [{label}]({url})" if url else f"- {label}")

    await ChatHistory.create(
        user=user,
        chat_group_id=info.get("chat_group_id"),
        req=info.get("prompt", ""),
        res="\n".join(lines),
    )
    await Notification.create(
        type="resource",
        title="图片生成完成",
        content=f"「{info.get('prompt', '图片')}」已生成，共 {len(images)} 张",
        target_url=f"/chat?chat_group_id={info.get('chat_group_id')}",
        target_user_id=info.get("user_id"),
    )
    info["history_saved"] = True


class ImageService:

    @staticmethod
    async def submit(prompt: str, user_id: int, aspect_ratio: str = "1:1", img_count: int = 1, chat_group_id: int = 0) -> dict:
        """提交生成任务到讯飞，立即返回 task_id"""
        app_id, api_key, api_secret = _load_env()

        user = await User.filter(id=user_id).first()
        if not user:
            raise RuntimeError("用户不存在")

        chat_group_id = await _ensure_chat_group_id(user_id, chat_group_id)

        prompt_json = json.dumps({
            "image": [],
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "img_count": img_count,
            "resolution": "2k",
        })
        text_base64 = base64.b64encode(prompt_json.encode()).decode()

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=30.0)) as client:
            create_body = {
                "header": {
                    "app_id": app_id, "status": 3,
                    "channel": "default", "callback_url": "default",
                },
                "parameter": {
                    "oig": {"result": {"encoding": "utf8", "compress": "raw", "format": "json"}}
                },
                "payload": {
                    "oig": {
                        "encoding": "utf8", "compress": "raw", "format": "json",
                        "status": 3, "text": text_base64,
                    }
                },
            }
            resp = await client.post(
                _make_auth_url(CREATE_PATH, api_key, api_secret),
                json=create_body,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"创建任务失败 (HTTP {resp.status_code}): {resp.text[:300]}")
            data = resp.json()
            header = data.get("header", {})
            if header.get("code") != 0:
                raise RuntimeError(f"创建任务失败: {header.get('message')} (code={header.get('code')})")
            task_id = header.get("task_id")
            if not task_id:
                raise RuntimeError("未获取到 task_id")

        _task_status[task_id] = {
            "status": "processing",
            "prompt": prompt,
            "user_id": user_id,
            "chat_group_id": chat_group_id,
            "aspect_ratio": aspect_ratio,
            "img_count": img_count,
            "created_at": str(datetime.now()),
        }

        _logger.info(f"图片任务已提交 task_id={task_id}")
        return {"task_id": task_id, "status": "processing", "chat_group_id": chat_group_id}

    @staticmethod
    async def poll_once(task_id: str) -> dict | None:
        """查询讯飞一次，如果完成则下载存库并更新状态。返回当前任务状态。"""
        info = _task_status.get(task_id)
        if not info:
            return None
        if info["status"] in ("done", "failed"):
            return dict(info)

        app_id, api_key, api_secret = _load_env()

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                query_body = {"header": {"app_id": app_id, "task_id": task_id}}
                resp = await client.post(
                    _make_auth_url(QUERY_PATH, api_key, api_secret),
                    json=query_body,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code != 200:
                    _logger.warning(f"查询 task_id={task_id} HTTP {resp.status_code}: {resp.text[:200]}")
                    return dict(info)

                qdata = resp.json()
                qheader = qdata.get("header", {})
                code = qheader.get("code", 0)
                if code != 0:
                    _task_status[task_id] = {**info, "status": "failed", "error": f"查询失败: {qheader.get('message')}"}
                    _logger.error(f"task_id={task_id} 查询失败 code={code} msg={qheader.get('message')}")
                    return _task_status[task_id]

                task_status_code = qheader.get("task_status", "")
                if task_status_code != "4":
                    return dict(info)

                _logger.info(f"task_id={task_id} 任务完成，开始下载")
                payload = qdata.get("payload", {})
                oig = payload.get("oig", {})
                result = payload.get("result", {}) or oig.get("result", {})
                result_text = result.get("text", "")
                if not result_text:
                    _logger.warning(f"task_id={task_id} 任务完成但 result_text 为空")
                    return dict(info)

                # 下载图片并存库

                user = await User.filter(id=info.get("user_id")).first()
                if not user:
                    _task_status[task_id] = {**info, "status": "failed", "error": "用户不存在"}
                    return _task_status[task_id]

                SAVE_DIR.mkdir(parents=True, exist_ok=True)
                items = json.loads(base64.b64decode(result_text).decode())
                images = []
                for item in items:
                    img_url = item.get("image_wm") or item.get("image")
                    if not img_url:
                        continue
                    img_resp = await client.get(img_url)
                    if img_resp.status_code != 200:
                        _logger.warning(f"下载图片失败 HTTP {img_resp.status_code}: {img_url[:100]}")
                        continue
                    filename = f"{uuid.uuid4().hex}.jpg"
                    filepath = SAVE_DIR / filename
                    filepath.write_bytes(img_resp.content)

                    record = await GeneratedImage.create(
                        prompt=info.get("prompt", ""),
                        filename=filename,
                        aspect_ratio=info.get("aspect_ratio", "1:1"),
                        user=user,
                    )
                    images.append({
                        "image_id": record.id,
                        "prompt": record.prompt,
                        "filename": record.filename,
                        "url": f"/static/images/{record.filename}",
                        "aspect_ratio": record.aspect_ratio,
                        "created_at": str(record.created_at),
                    })

                if images:
                    await _save_image_history(info, images)
                    _task_status[task_id] = {**info, "status": "done", "images": images}
                    _logger.info(f"task_id={task_id} 完成 {len(images)} 张图片")
                else:
                    _task_status[task_id] = {**info, "status": "failed", "error": "图片下载失败，请重试"}
                    _logger.error(f"task_id={task_id} 所有图片下载均失败")
                return _task_status[task_id]

        except Exception as e:
            _task_status[task_id] = {**info, "status": "failed", "error": f"{type(e).__name__}: {e}"}
            _logger.error(f"task_id={task_id} 异常: {type(e).__name__}: {e}")
            return _task_status[task_id]

    @staticmethod
    async def generate(prompt: str, user_id: str, aspect_ratio: str = "1:1", img_count: int = 1, chat_group_id: int = 0) -> list[dict]:
        """同步生成（供 tool 使用，阻塞等待结果）"""
        result = await ImageService.submit(prompt, int(user_id), aspect_ratio, img_count, chat_group_id=chat_group_id)
        task_id = result["task_id"]

        for _ in range(30):
            await asyncio.sleep(2)
            status = await ImageService.poll_once(task_id)
            if status["status"] == "done":
                return status.get("images", [])
            if status["status"] == "failed":
                raise RuntimeError(status.get("error", "图片生成失败"))

        raise TimeoutError("图片生成超时")
