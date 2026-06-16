"""统一返回格式工具"""

from typing import Any, Optional


def success(data: Any = None, msg: str = "success") -> dict:
    """成功响应"""
    return {"code": 200, "msg": msg, "data": data}


def error(code: int = 400, msg: str = "错误", data: Any = None) -> dict:
    """业务错误响应"""
    result = {"code": code, "msg": msg}
    if data is not None:
        result["data"] = data
    return result
