"""响应自动包装中间件

所有 JSON 响应自动包装为 {"code": 200, "msg": "success", "data": ...}
已有 code 字段的响应、StreamingResponse / FileResponse 则原样返回
"""

import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse


class ResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 非 JSON 响应不处理（StreamingResponse、FileResponse 等）
        if isinstance(response, (StreamingResponse, FileResponse)):
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # 读取响应体
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # 非 JSON 内容原样返回
            return JSONResponse(content=body, status_code=response.status_code)

        # 已有统一格式的直接透传
        if isinstance(data, dict) and "code" in data:
            return JSONResponse(content=data, status_code=response.status_code)

        # 自动包装
        wrapped = {"code": 200, "msg": "success", "data": data}
        return JSONResponse(content=wrapped, status_code=200)
