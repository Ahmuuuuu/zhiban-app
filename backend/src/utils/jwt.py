import os
from pathlib import Path
from jose import jwt, JWTError
from fastapi import HTTPException, Header, Depends, Request
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv(Path(__file__).parent.parent.parent / ".env")
JWT_KEY = os.getenv("JWT_KEY") or "zhiban-jwt-secret-key-change-in-production"
ALGORITHM = os.getenv("ALGORITHM") or "HS256"

if not os.getenv("JWT_KEY"):
    import warnings
    warnings.warn("JWT_KEY 未在 .env 中配置，使用了默认密钥，生产环境请务必更换！")


def create_access_token(user_id: int, role: str = "user") -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_KEY, ALGORITHM)


def decode_token(token: str) -> dict:
    """解码 token，返回 payload；无效时抛出 JWTError"""
    return jwt.decode(token, JWT_KEY, algorithms=[ALGORITHM])


def _extract_token(authorization: str | None = Header(None, alias="Authorization"),
                   token: str | None = Header(None)) -> str:
    """从 Authorization: Bearer <token> 或自定义 token header 中提取 token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    if token:
        return token
    raise HTTPException(401, "未携带认证令牌")


def get_user_id_from_token(authorization: str | None = Header(None, alias="Authorization"),
                           token: str | None = Header(None)) -> int:
    """从请求头提取 token 并返回 user_id（FastAPI 依赖注入）"""
    raw = _extract_token(authorization, token)
    try:
        payload = decode_token(raw)
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("sub 缺失")
        return int(user_id)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(401, "token 无效或已过期")


def get_admin_user_id(user_id: int = Depends(get_user_id_from_token)) -> int:
    """管理员校验依赖：先通过 get_user_id_from_token 获取 user_id，再校验 role"""
    return user_id
