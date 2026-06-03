"""APScheduler 定时任务调度器（AsyncIO 模式）"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


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

    from backend.src.service.notification_service import (
        generate_weekly_report_and_ai_tip,
    )

    # 每周一 9:00 生成周报 + AI 建议
    sched.add_job(
        generate_weekly_report_and_ai_tip,
        trigger="cron",
        day_of_week="mon",
        hour=9,
        minute=7,  # 避免整点高峰
        id="weekly_report_and_ai_tip",
        name="周报与AI建议",
        replace_existing=True,
    )

    sched.start()
    logger.info("定时任务已启动：每周一 09:07 生成周报+AI建议")


def stop():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("定时任务已停止")
