# -*- coding: utf-8 -*-
"""APScheduler 定时任务调度器（AsyncIO 模式）"""

import asyncio
import json
import logging
import shutil
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.src.utils.constants import STATIC_DIR, CLEANUP_AGE_SECONDS

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_last_agent_fire: dict[int, float] = {}  # (user_id, agent_id) → 上次执行时间戳，防重复触发


def _cleanup_old_files():
    """删除 static 目录下超过 1 天的生成文件（音频缓存、视频、演示、PPT）"""
    now = time.time()
    dirs = [
        STATIC_DIR / "audio" / "_cache",
        STATIC_DIR / "videos",
        STATIC_DIR / "presentations",
        STATIC_DIR / "ppt",
    ]
    cleaned = 0
    for d in dirs:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            try:
                if f.is_file() and now - f.stat().st_mtime > CLEANUP_AGE_SECONDS:
                    f.unlink()
                    cleaned += 1
            except OSError:
                logger.debug("Suppressed exception at backend/src/utils/scheduler.py:33", exc_info=True)
        if d.name != "_cache" and d.parent.name == "audio":
            continue
    audio_dir = STATIC_DIR / "audio"
    if audio_dir.is_dir():
        for sub in audio_dir.iterdir():
            if sub.is_dir() and sub.name != "_cache":
                try:
                    if not any(sub.iterdir()):
                        sub.rmdir()
                except OSError:
                    logger.debug("Suppressed exception at backend/src/utils/scheduler.py:46", exc_info=True)
    if cleaned:
        logger.info("清理过期文件 %d 个", cleaned)


def _cron_matches(cron_expr: str, now_minute: int, now_hour: int,
                  now_dom: int, now_month: int, now_dow: int) -> bool:
    """简易 cron 五字段匹配（minute hour dom month dow），不支持 / 和 , 以外的特殊字符"""
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False

        def _match(field: str, current: int) -> bool:
            if field == "*":
                return True
            # 逗号分隔
            for chunk in field.split(","):
                chunk = chunk.strip()
                if "/" in chunk:
                    base, step = chunk.split("/", 1)
                    step = int(step)
                    if base == "*":
                        return current % step == 0
                    else:
                        val = int(base)
                        return current >= val and (current - val) % step == 0
                if "-" in chunk:
                    lo, hi = chunk.split("-", 1)
                    if int(lo) <= current <= int(hi):
                        return True
                elif chunk == str(current):
                    return True
            return False

        current_values = [now_minute, now_hour, now_dom, now_month, now_dow]
        return all(_match(parts[i], current_values[i]) for i in range(5))
    except (ValueError, IndexError):
        return False


async def _execute_scheduled_agents():
    """每分钟扫描 UserAgent 表，执行匹配当前时间的定时任务"""
    from datetime import datetime, timezone as tz
    now = datetime.now(tz.utc)
    now_shanghai = now.replace(tzinfo=None)  # APScheduler 用 Asia/Shanghai，无时区
    minute, hour, dom, month, dow = (
        now_shanghai.minute, now_shanghai.hour, now_shanghai.day,
        now_shanghai.month, (now_shanghai.weekday() + 1) % 7,  # 0=周日→6
    )

    try:
        from backend.src.models.user_agent_model import UserAgent
        from backend.src.ai_core.llm_config import llm

        agents = await UserAgent.filter(enabled=True).exclude(schedule__isnull=True).all()
        if not agents:
            return

        for agent in agents:
            try:
                sched = json.loads(agent.schedule or "{}")
            except (json.JSONDecodeError, TypeError):
                continue

            cron_expr = sched.get("cron", "").strip()
            prompt = sched.get("prompt", "").strip()
            if not cron_expr or not prompt:
                continue

            if not _cron_matches(cron_expr, minute, hour, dom, month, dow):
                continue

            # 防重复：同一智能体每分钟最多执行一次
            key = agent.id
            last_fire = _last_agent_fire.get(key, 0)
            if time.monotonic() - last_fire < 59:
                continue
            _last_agent_fire[key] = time.monotonic()

            logger.info("智能体定时触发 agent_id=%d name=%s user_id=%d cron=%s",
                        agent.id, agent.name, agent.user_id, cron_expr)

            # 构建 system prompt（用户自定义 persona 或默认）
            system = agent.persona or "你是小知，一个 AI 学习导师。"
            full_prompt = f"{system}\n\n当前时间：{now_shanghai.isoformat()}\n\n{prompt}"

            try:
                response = await asyncio.wait_for(llm.ainvoke(full_prompt), timeout=60)
                result_text = str(response.content)[:500]
            except asyncio.TimeoutError:
                result_text = "智能体定时任务执行超时"
            except Exception:
                logger.exception("智能体定时执行 LLM 失败 agent_id=%d", agent.id)
                continue

            # 写入通知记录，前端轮询或 SSE 推送时可见
            try:
                from backend.src.models.notification_model import Notification
                await Notification.create(
                    target_user_id=agent.user_id,
                    title=f"[{agent.name}] 定时推送",
                    content=result_text or f"定时任务「{prompt[:30]}...」已执行",
                    type="system",
                )
            except Exception:
                logger.debug("智能体通知写入失败 agent_id=%d", agent.id, exc_info=True)

    except Exception:
        logger.exception("智能体定时扫描异常")


def get_scheduler() -> AsyncIOScheduler:
    """获取全局调度器（懒初始化）"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone="Asia/Shanghai",
            job_defaults={"coalesce": True, "max_instances": 1},
        )
    return _scheduler


def start():
    sched = get_scheduler()

    from backend.src.service.notification.service import (
        generate_weekly_report_and_ai_tip,
    )

    # 每天凌晨 3 点清理超过 1 天的静态文件
    sched.add_job(
        _cleanup_old_files,
        trigger="cron",
        hour=3,
        minute=13,
        id="cleanup_old_files",
        name="清理过期静态文件",
        replace_existing=True,
    )

    # 每周一 9:00 生成周报 + AI 建议
    sched.add_job(
        generate_weekly_report_and_ai_tip,
        trigger="cron",
        day_of_week="mon",
        hour=9,
        minute=7,
        id="weekly_report_and_ai_tip",
        name="周报与AI建议",
        replace_existing=True,
    )

    # 每分钟扫描用户自建智能体的定时任务
    sched.add_job(
        _execute_scheduled_agents,
        trigger="cron",
        minute="*",
        id="user_agent_schedule",
        name="用户智能体定时触发",
        replace_existing=True,
    )

    sched.start()
    logger.info("定时任务已启动：清理过期文件（每日3:13）+ 周报（周一9:07）+ 智能体定时（每分钟）")


def stop():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("定时任务已停止")
