"""SMTP 邮件发送工具"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.qq.com"),
        "port": int(os.getenv("SMTP_PORT", "465")),
        "user": os.getenv("SMTP_USER", ""),
        "pass": os.getenv("SMTP_PASS", ""),
    }


def send_email(to_email: str, subject: str, body: str) -> bool:
    """同步发送邮件，返回是否成功"""
    cfg = _get_smtp_config()
    if not cfg["user"] or not cfg["pass"]:
        logger.error("SMTP 未配置，请在 .env 中设置 SMTP_USER 和 SMTP_PASS")
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = cfg["user"]
    msg["To"] = to_email
    msg["Subject"] = Header(subject, "utf-8")

    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10) as server:
                server.login(cfg["user"], cfg["pass"])
                server.sendmail(cfg["user"], [to_email], msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as server:
                server.starttls()
                server.login(cfg["user"], cfg["pass"])
                server.sendmail(cfg["user"], [to_email], msg.as_string())
        logger.info("邮件发送成功 to=%s", to_email)
        return True
    except Exception:
        logger.exception("邮件发送失败 to=%s", to_email)
        return False
