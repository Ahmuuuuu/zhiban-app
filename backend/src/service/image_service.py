"""图片生成服务 (讯飞 HiDream)"""

import os
import json
import base64
import hmac
import hashlib
import uuid
import asyncio
import time as _time
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
from urllib.parse import urlencode
import httpx

from backend.src.models.chat_history_model import ChatHistory
from backend.src.models.usermodel import User
from backend.src.models.image_model import GeneratedImage

_REFINE_PROMPT = """你是一个专业的 AI 绘画提示词工程师。将用户描述精炼成高质量图片提示词。

精炼规则：
1. 补充光线来源与方向、构图方式、艺术风格、色彩调性、材质质感等视觉细节
2. 具象场景加"照片级真实感，高细节，8K"
3. 绘画风格指定具体风格如"吉卜力风格/水墨画/油画/赛博朋克/写实摄影/扁平插画"
4. 输出 80-150 字中文，必须包含：主体描述 + 环境背景 + 光线色彩 + 艺术风格 + 画质关键词
5. 只输出画面描述，不含"生成""制作""帮我画"等指令性文字

用户描述：{raw}"""

_MIN_PROMPT_LEN = 80

_BAD_PATTERNS = ["帮我", "生成一张", "画一张", "画个", "请生成", "请画", "生成图片", "配图"]


async def _ensure_prompt_quality(prompt: str) -> str:
    """确保图片提示词质量满足星火最低要求，所有路径统一入口"""
    prompt = prompt.strip()

    # 合格 → 直接放行
    if len(prompt) >= _MIN_PROMPT_LEN and not any(p in prompt for p in _BAD_PATTERNS):
        return prompt

    # 明显是 LLM 偷懒没精炼 → 直接用模板，不调 LLM，零延迟
    if len(prompt) < 30 or any(p in prompt for p in _BAD_PATTERNS):
        _logger.warning("图片 prompt 质量差(len=%d)，使用模板兜底: %s", len(prompt), prompt[:60])
        topic = prompt
        for pat in _BAD_PATTERNS:
            topic = topic.replace(pat, "")
        topic = topic.strip().lstrip("：:，,。. ").strip() or prompt
        return (
            f"教育科普插图，教学示意图风格，{topic}，高清晰度，"
            "色彩鲜明，构图清晰，适合学习使用，详细展示相关知识点和结构，"
            "学术配图，照片级真实感，高细节，8K分辨率，专业灯光，电影级构图"
        )

    # 偏短但无坏词 → LLM 精炼（罕见情况，值得花 1-2s）
    _logger.info("图片 prompt 偏短(len=%d)，LLM 精炼: %s", len(prompt), prompt[:60])
    try:
        from backend.src.ai_core.llm_config import llm
        resp = await llm.ainvoke(_REFINE_PROMPT.format(raw=prompt), pool="thread")
        refined = resp.content.strip()
        if refined and len(refined) >= _MIN_PROMPT_LEN:
            return refined
    except Exception:
        _logger.exception("图片 prompt 精炼异常")

    fallback = f"{prompt}，照片级真实感，高细节，8K分辨率，专业灯光，电影级构图"
    _logger.info("使用兜底 prompt: %s", fallback[:80])
    return fallback
from backend.src.models.notification_model import Notification
from backend.src.utils.chat_utils import allocate_chat_group_id


HOST = "cn-huadong-1.xf-yun.com"
CREATE_PATH = "/v1/private/s3fd61810/create"
QUERY_PATH = "/v1/private/s3fd61810/query"

import logging
_logger = logging.getLogger("image_service")

_task_status: dict[str, dict] = {}

# ─── 讯飞并发控制 ───
# 免费版仅 1 路并发，10006/10007/11203 都是并发超限
_xf_submit_lock = asyncio.Lock()
_xf_last_submit: float = 0.0
_RETRYABLE_CODES = {10006, 10007, 11203, 10008, 401}
_MAX_RETRIES = 3
_MIN_SUBMIT_INTERVAL = 1.5  # 两次提交最小间隔（秒）


def _load_env():
    app_id = os.getenv("XF_APP_ID", "")
    api_key = os.getenv("XF_API_KEY", "")
    api_secret = os.getenv("XF_API_SECRET", "")
    if not all([app_id, api_key, api_secret]):
        raise RuntimeError("图片生成服务未配置，请在 .env 中设置 XF_APP_ID、XF_API_KEY、XF_API_SECRET")
    return app_id, api_key, api_secret


def _make_auth_url(path: str, api_key: str, api_secret: str) -> str:
    """生成带鉴权的请求 URL（标准 讯飞 HMAC-SHA256 签名）"""
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


from backend.src.utils.constants import IMAGES_DIR

SAVE_DIR = IMAGES_DIR




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

    _logger.info("_save_image_history() user_id=%s chat_group_id=%s prompt=%s",
                  info.get("user_id"), info.get("chat_group_id"), info.get("prompt", "")[:60])
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
        """提交生成任务到讯飞，带并发控制 + 自动重试"""
        app_id, api_key, api_secret = _load_env()

        user = await User.filter(id=user_id).first()
        if not user:
            raise RuntimeError("用户不存在")

        chat_group_id = chat_group_id if chat_group_id and chat_group_id > 0 else await allocate_chat_group_id(user_id)
        _logger.info(f"submit user_id={user_id} chat_group_id={chat_group_id}")

        prompt_json = json.dumps({
            "image": [],
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "img_count": img_count,
            "resolution": "2k",
        })
        text_base64 = base64.b64encode(prompt_json.encode()).decode()

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

        # ═══ 串行化提交：全局锁 + 最小间隔 + 重试 ═══
        async with _xf_submit_lock:
            # 保证两次提交至少间隔 _MIN_SUBMIT_INTERVAL
            global _xf_last_submit
            now = _time.time()
            gap = _MIN_SUBMIT_INTERVAL - (now - _xf_last_submit)
            if gap > 0:
                await asyncio.sleep(gap)

            last_err = None
            for attempt in range(_MAX_RETRIES):
                try:
                    url = _make_auth_url(CREATE_PATH, api_key, api_secret)
                    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=60.0)) as client:
                        resp = await client.post(
                            url, json=create_body,
                            headers={"Content-Type": "application/json"},
                        )
                        if resp.status_code != 200:
                            raise RuntimeError(f"创建任务失败 (HTTP {resp.status_code}): {resp.text[:300]}")

                        data = resp.json()
                        header = data.get("header", {})
                        code = header.get("code", 0)
                        msg = header.get("message", "")

                        if code == 0:
                            task_id = header.get("task_id")
                            if not task_id:
                                raise RuntimeError("未获取到 task_id")

                            _xf_last_submit = _time.time()
                            _task_status[task_id] = {
                                "status": "processing", "prompt": prompt,
                                "user_id": user_id, "chat_group_id": chat_group_id,
                                "aspect_ratio": aspect_ratio, "img_count": img_count,
                                "created_at": str(datetime.now()),
                            }
                            _logger.info(f"图片任务已提交 task_id={task_id}")
                            return {"task_id": task_id, "status": "processing", "chat_group_id": chat_group_id}

                        # 可重试：并发超限 / 服务容量不足 / 鉴权失败
                        if code in _RETRYABLE_CODES and attempt < _MAX_RETRIES - 1:
                            wait = 2 ** attempt * 2  # 2s, 4s, 8s
                            _logger.warning(f"submit 可重试 code={code} msg={msg} attempt={attempt+1}/{_MAX_RETRIES} wait={wait}s")
                            await asyncio.sleep(wait)
                            last_err = f"{msg} (code={code})"
                            continue

                        # 不可重试
                        raise RuntimeError(f"创建任务失败: {msg} (code={code})")

                except httpx.TimeoutException as e:
                    if attempt < _MAX_RETRIES - 1:
                        wait = 2 ** attempt * 2
                        _logger.warning(f"submit 超时 attempt={attempt+1}/{_MAX_RETRIES} wait={wait}s")
                        await asyncio.sleep(wait)
                        last_err = str(e)
                        continue
                    raise RuntimeError(f"创建任务超时 (已重试{_MAX_RETRIES}次)")

            # 所有重试用尽
            raise RuntimeError(f"创建任务失败 (已重试{_MAX_RETRIES}次): {last_err}")

    @staticmethod
    async def poll_once(task_id: str, save_history: bool = True) -> dict | None:
        """查询讯飞一次，如果完成则下载存库并更新状态。返回当前任务状态。"""
        info = _task_status.get(task_id)
        if not info:
            return None
        if info["status"] in ("done", "failed"):
            return dict(info)

        app_id, api_key, api_secret = _load_env()

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
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
                _logger.info(f"task_id={task_id} 查询响应 code={qdata.get('header', {}).get('code')} task_status={qdata.get('header', {}).get('task_status')}")
                qheader = qdata.get("header", {})
                code = qheader.get("code", 0)
                if code != 0:
                    # 非 0 多为瞬时错误（限流/服务忙），不判死，下轮重试
                    _logger.warning(f"查询 task_id={task_id} 非零 code={code} msg={qheader.get('message')}（非致命，下轮重试）")
                    return dict(info)

                task_status_code = qheader.get("task_status", "")
                if task_status_code == "5":
                    _task_status[task_id] = {**info, "status": "failed",
                        "error": f"图片生成失败 (task_status=5): {qheader.get('message', '未知错误')}"}
                    _logger.error(f"task_id={task_id} 任务失败 task_status=5 msg={qheader.get('message')}")
                    return _task_status[task_id]
                if task_status_code != "4":
                    # 从查询响应中提取进度百分比
                    _progress = qheader.get("task_completion", 0) or 0
                    _logger.info(f"task_id={task_id} 生成中 task_status={task_status_code} progress={_progress}%")
                    return {**info, "status": "processing", "progress": int(_progress)}

                _logger.info(f"task_id={task_id} 任务完成，开始下载")
                payload = qdata.get("payload", {})
                oig = payload.get("oig", {})
                result = payload.get("result", {}) or oig.get("result", {})
                result_text = result.get("text", "")
                if not result_text:
                    # 偶尔 result_text 延迟到达，不判死
                    _logger.warning(f"task_id={task_id} result_text 为空，下轮重试")
                    return dict(info)

                # 下载图片并存库

                user = await User.filter(id=info.get("user_id")).first()
                if not user:
                    _task_status[task_id] = {**info, "status": "failed", "error": "用户不存在"}
                    return _task_status[task_id]

                SAVE_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    decoded_raw = base64.b64decode(result_text).decode()
                except Exception:
                    _logger.exception(f"task_id={task_id} base64 解码失败")
                    _task_status[task_id] = {**info, "status": "failed", "error": "图片结果解码失败"}
                    return _task_status[task_id]
                items = json.loads(decoded_raw)
                _logger.info(f"task_id={task_id} 解码得到 {len(items)} 个 item, 全部 raw={decoded_raw}")
                images = []
                all_empty = True
                for item in items:
                    img_url = item.get("image_wm") or item.get("image")
                    # 子任务 task_status: 3=成功, 1-2=排队/处理中, 0/4=失败
                    sub_status = item.get("task_status", -1)
                    sub_completion = item.get("task_completion", 0)
                    _logger.info(f"task_id={task_id} sub_task_id={item.get('sub_task_id')} "
                                 f"task_status={sub_status} task_completion={sub_completion} "
                                 f"image={item.get('image', '')[:80]} image_wm={item.get('image_wm', '')[:80]}")
                    if not img_url:
                        continue
                    all_empty = False
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
                    if save_history:
                        await _save_image_history(info, images)
                    _task_status[task_id] = {**info, "status": "done", "images": images}
                    _logger.info(f"task_id={task_id} 完成 {len(images)} 张图片")
                elif all_empty:
                    _task_status[task_id] = {**info, "status": "failed",
                        "error": "图片生成失败，请检查讯飞星火控制台：额度是否已用尽或内容是否被审核拦截"}
                    _logger.error(f"task_id={task_id} 图片 URL 为空（疑似额度用尽或审核拦截），全部响应已打印")
                return _task_status[task_id]

        except Exception as e:
            _task_status[task_id] = {**info, "status": "failed", "error": f"{type(e).__name__}: {e}"}
            _logger.error(f"task_id={task_id} 异常: {type(e).__name__}: {e}")
            return _task_status[task_id]

    @staticmethod
    async def generate(prompt: str, user_id: str, aspect_ratio: str = "1:1", img_count: int = 1, chat_group_id: int = 0, save_history: bool = True) -> list[dict]:
        """同步生成（供 tool 使用，阻塞等待结果）。
        save_history=False 时跳过聊天记录写入（资源整合流程已有统一记录）。

        最多等待 _MAX_POLL * _POLL_INTERVAL ≈ 300 秒（5 分钟），
        每次 poll 耗时超过间隔时会自动跳过本次睡眠。
        """
        prompt = await _ensure_prompt_quality(prompt)
        result = await ImageService.submit(prompt, int(user_id), aspect_ratio, img_count, chat_group_id=chat_group_id)
        task_id = result["task_id"]

        _POLL_INTERVAL = 2
        _MAX_POLL = 150

        for i in range(_MAX_POLL):
            _t_start = _time.monotonic()
            status = await ImageService.poll_once(task_id, save_history=save_history)
            if status["status"] == "done":
                return status.get("images", [])
            if status["status"] == "failed":
                raise RuntimeError(status.get("error", "图片生成失败"))

            elapsed = _time.monotonic() - _t_start
            wait = _POLL_INTERVAL - elapsed
            if wait > 0:
                await asyncio.sleep(wait)

        raise TimeoutError(f"图片生成超时（已等待 {_MAX_POLL * _POLL_INTERVAL} 秒，实际因 API 响应时间可能更长）")
