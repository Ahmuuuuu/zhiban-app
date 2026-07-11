import os
from jose import jwt, JWTError
from fastapi import HTTPException, Header, Depends, Request
from datetime import datetime, timedelta, timezone

JWT_KEY = os.getenv("JWT_KEY") or "zhiban-jwt-secret-key-change-in-production"
ALGORITHM = os.getenv("ALGORITHM") or "HS256"

if not JWT_KEY:
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


async def get_admin_user_id(user_id: int = Depends(get_user_id_from_token)) -> int:
    """管理员校验依赖：先通过 get_user_id_from_token 获取 user_id，再校验 role=admin"""
    from backend.src.models.usermodel import User
    user = await User.filter(id=user_id).first()
    if not user or getattr(user, 'role', '') != 'admin':
        raise HTTPException(403, "需要管理员权限")
    return user_id
