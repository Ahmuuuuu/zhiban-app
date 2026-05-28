"""讯飞智文 PPT 生成服务"""
import asyncio
import hashlib
import hmac
import base64
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_URL = "https://zwapi.xfyun.cn"
CREATE_PATH = "/api/aippt/create"
CREATE_BY_DOC_PATH = "/api/aippt/createByDoc"
PROGRESS_PATH = "/api/aippt/progress"
SAVE_DIR = Path(__file__).parent.parent.parent / "static" / "ppt"


def _load_env():
    env_file = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_file)
    app_id = os.getenv("XF_APP_ID", "")
    api_secret = os.getenv("XF_PPT_API_SECRET", "")
    return app_id, api_secret


def _sign(app_id: str, secret: str, timestamp: str) -> str:
    auth_str = app_id + timestamp
    auth_md5 = hashlib.md5(auth_str.encode()).hexdigest()
    sign = hmac.new(secret.encode(), auth_md5.encode(), hashlib.sha1).digest()
    return base64.b64encode(sign).decode()


def _headers(app_id: str, secret: str) -> dict[str, str]:
    timestamp = str(int(datetime.now().timestamp()))
    return {
        "appId": app_id,
        "timestamp": timestamp,
        "signature": _sign(app_id, secret, timestamp),
        "Content-Type": "application/json",
    }


class PptService:

    @staticmethod
    async def generate(topic: str, is_figure: bool = True, theme: str = "auto",
                       language: str = "cn") -> str:
        """生成 PPT，返回本地文件路径

        Args:
            topic: PPT 主题/要求。写越详细效果越好，
                  建议包含大纲结构（每章一条）和配图要求。
            is_figure: 是否自动配图
            theme: 主题模板 (auto/blue/purple 等)
            language: 语种 (cn/en)

        Returns:
            本地 PPTX 文件路径
        """
        app_id, api_secret = _load_env()
        if not app_id or not api_secret:
            raise RuntimeError("讯飞智文未配置，请在 .env 中设置 XF_APP_ID 和 XF_PPT_API_SECRET")

        sid = await PptService._create_task(app_id, api_secret, topic, is_figure, theme, language)
        download_url = await PptService._poll_progress(app_id, api_secret, sid)
        local_path = await PptService._download_file(download_url, topic)
        return local_path

    @staticmethod
    async def _create_task(app_id: str, api_secret: str, query: str,
                           is_figure: bool, theme: str, language: str) -> str:
        if len(query) > 8000:
            query = query[:8000]

        payload = {
            "query": query,
            "create_model": "auto",
            "theme": theme,
            "is_figure": is_figure,
            "language": language,
            "is_card_note": True,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                resp = await client.post(
                    f"{BASE_URL}{CREATE_PATH}",
                    headers=_headers(app_id, api_secret),
                    json=payload,
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"创建 PPT 任务失败 (HTTP {resp.status_code}): {resp.text[:300]}")
                data = resp.json()
                if data.get("code") != 0:
                    raise RuntimeError(f"创建 PPT 任务失败: {data.get('desc', '未知错误')}")
                sid = data.get("data", {}).get("sid", "")
                if not sid:
                    raise RuntimeError("创建 PPT 任务成功但未返回 sid")
                logger.info(f"PPT 任务已提交 sid={sid}")
                return sid
        except httpx.TimeoutException:
            raise RuntimeError("创建 PPT 任务超时")

    @staticmethod
    async def _poll_progress(app_id: str, api_secret: str, sid: str,
                             max_retries: int = 60, interval: float = 3.0) -> str:
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                    resp = await client.get(
                        f"{BASE_URL}{PROGRESS_PATH}",
                        params={"sid": sid},
                        headers=_headers(app_id, api_secret),
                    )
                    if resp.status_code != 200:
                        logger.warning(f"查询进度 HTTP {resp.status_code} (attempt {attempt})")
                        await asyncio.sleep(interval)
                        continue

                    data = resp.json()
                    if data.get("code") != 0:
                        logger.warning(f"查询进度失败: {data.get('desc')} (attempt {attempt})")
                        await asyncio.sleep(interval)
                        continue

                    progress = data.get("data", {})
                    process = progress.get("process", 0)
                    ppt_url = progress.get("pptUrl", "")

                    if process == 100 and ppt_url:
                        logger.info(f"PPT 生成完成 sid={sid}")
                        return ppt_url

                    logger.info(f"PPT 进度: {process}% (attempt {attempt})")
                    await asyncio.sleep(interval)

            except httpx.TimeoutException:
                logger.warning(f"查询进度超时 (attempt {attempt})")

        raise TimeoutError(f"PPT 生成超时 (sid={sid})")

    @staticmethod
    async def _download_file(download_url: str, topic: str) -> str:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)

        safe_name = "".join(c for c in topic if c.isalnum() or c in " _-")[:50]
        filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.pptx"
        local_path = SAVE_DIR / filename

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                resp = await client.get(download_url)
                if resp.status_code != 200:
                    raise RuntimeError(f"下载 PPTX 失败 (HTTP {resp.status_code})")
                local_path.write_bytes(resp.content)
                logger.info(f"PPTX 已下载: {local_path} ({len(resp.content)} bytes)")
                return str(local_path)
        except httpx.TimeoutException:
            raise RuntimeError("下载 PPTX 超时")
