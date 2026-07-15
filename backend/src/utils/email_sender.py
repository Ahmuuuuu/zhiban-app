"""SMTP 邮件发送工具"""

import logging
import os
import smtplib
import ssl
from contextlib import suppress
from email.mime.text import MIMEText
from email.header import Header

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.qq.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "security": os.getenv("SMTP_SECURITY", "auto").strip().lower(),
        "user": os.getenv("SMTP_USER", ""),
        "pass": os.getenv("SMTP_PASS", ""),
    }


def _make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _security_for_port(port: int) -> str:
    return "ssl" if port == 465 else "starttls"


def _build_attempts(cfg: dict) -> list[tuple[int, str]]:
    security = cfg.get("security") or "auto"
    first = (cfg["port"], _security_for_port(cfg["port"]) if security == "auto" else security)
    attempts = [first]

    # 常见邮箱服务商都支持 465/SSL 或 587/STARTTLS。配置的通道握手异常时，
    # 换一条标准通道再试一次，避免因为网络/代理对某个端口不稳定导致验证码不可用。
    for item in [(587, "starttls"), (465, "ssl")]:
        if item not in attempts:
            attempts.append(item)
    return attempts


def _send_with_security(cfg: dict, msg: MIMEText, to_email: str, port: int, security: str) -> None:
    server = None
    try:
        if security == "ssl":
            server = smtplib.SMTP_SSL(
                cfg["host"],
                port,
                timeout=10,
                context=_make_ssl_context(),
            )
        else:
            server = smtplib.SMTP(cfg["host"], port, timeout=10)
            server.ehlo()
            if security != "none":
                server.starttls(context=_make_ssl_context())
                server.ehlo()

        server.login(cfg["user"], cfg["pass"])
        server.sendmail(cfg["user"], [to_email], msg.as_string())
    finally:
        if server is not None:
            with suppress(Exception):
                server.quit()


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

    last_error: Exception | None = None
    for port, security in _build_attempts(cfg):
        try:
            logger.info("尝试发送邮件 host=%s port=%s security=%s to=%s", cfg["host"], port, security, to_email)
            _send_with_security(cfg, msg, to_email, port, security)
            logger.info("邮件发送成功 host=%s port=%s security=%s to=%s", cfg["host"], port, security, to_email)
            return True
        except smtplib.SMTPAuthenticationError:
            logger.exception("SMTP 认证失败，请检查 SMTP_USER 和 SMTP_PASS/授权码")
            return False
        except Exception as exc:
            last_error = exc
            logger.warning(
                "邮件通道失败 host=%s port=%s security=%s to=%s error=%s",
                cfg["host"],
                port,
                security,
                to_email,
                exc,
            )

    if last_error:
        logger.exception("邮件发送失败 to=%s", to_email, exc_info=last_error)
    return False
