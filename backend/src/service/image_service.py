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


HOST = "cn-huadong-1.xf-yun.com"
CREATE_PATH = "/v1/private/s3fd61810/create"
QUERY_PATH = "/v1/private/s3fd61810/query"


def _load_env():
    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(env_file)
    app_id = os.getenv("XF_APP_ID", "")
    api_key = os.getenv("XF_API_KEY", "")
    api_secret = os.getenv("XF_API_SECRET", "")
    proxy = os.getenv("HTTP_PROXY", None)
    if not all([app_id, api_key, api_secret]):
        raise RuntimeError("图片生成服务未配置，请在 .env 中设置 XF_APP_ID、XF_API_KEY、XF_API_SECRET")
    return app_id, api_key, api_secret, proxy


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


class ImageService:

    @staticmethod
    async def generate(prompt: str, user_id: str, aspect_ratio: str = "1:1", img_count: int = 1) -> list[dict]:
        """生成图片，保存至 static/images/，创建 DB 记录，返回记录列表"""
        from backend.src.models.usermodel import User
        from backend.src.models.image_model import GeneratedImage

        app_id, api_key, api_secret, proxy = _load_env()

        user = await User.filter(id=int(user_id)).first()
        if not user:
            raise RuntimeError("用户不存在")

        # 确保保存目录存在
        save_dir = Path(__file__).parent.parent.parent / "static" / "images"
        save_dir.mkdir(parents=True, exist_ok=True)

        prompt_json = json.dumps({
            "image": [],
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "img_count": img_count,
            "resolution": "2k",
        })
        text_base64 = base64.b64encode(prompt_json.encode()).decode()

        client_kwargs = {"timeout": httpx.Timeout(120.0)}
        if proxy:
            client_kwargs["proxy"] = proxy

        async with httpx.AsyncClient(**client_kwargs) as client:
            # 创建任务
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

            # 轮询
            for _ in range(30):
                await asyncio.sleep(2)
                query_body = {"header": {"app_id": app_id, "task_id": task_id}}
                resp = await client.post(
                    _make_auth_url(QUERY_PATH, api_key, api_secret),
                    json=query_body,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code != 200:
                    continue
                qdata = resp.json()
                qheader = qdata.get("header", {})
                if qheader.get("code") != 0:
                    raise RuntimeError(f"查询任务失败: {qheader.get('message')}")
                if qheader.get("task_status") != "4":
                    continue

                payload = qdata.get("payload", {})
                oig = payload.get("oig", {})
                result = oig.get("result", {})
                result_text = result.get("text", "")
                if not result_text:
                    continue
                items = json.loads(base64.b64decode(result_text).decode())
                saved = []
                for item in items:
                    img_url = item.get("image_wm") or item.get("image")
                    if not img_url:
                        continue
                    img_resp = await client.get(img_url)
                    if img_resp.status_code != 200:
                        continue
                    filename = f"{uuid.uuid4().hex}.jpg"
                    filepath = save_dir / filename
                    filepath.write_bytes(img_resp.content)

                    record = await GeneratedImage.create(
                        prompt=prompt,
                        filename=filename,
                        aspect_ratio=aspect_ratio,
                        user=user,
                    )
                    saved.append({
                        "image_id": record.id,
                        "prompt": record.prompt,
                        "filename": record.filename,
                        "url": f"/static/images/{record.filename}",
                        "aspect_ratio": record.aspect_ratio,
                        "created_at": str(record.created_at),
                    })
                return saved

            raise TimeoutError("图片生成超时")
