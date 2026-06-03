import os
from pathlib import Path
from jose import jwt, JWTError
from fastapi import HTTPException, Header, Depends
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv(Path(__file__).parent.parent.parent / ".env")
JWT_KEY = os.getenv("JWT_KEY") or "zhiban-jwt-secret-key-change-in-production"
ALGORITHM = os.getenv("ALGORITHM") or "HS256"

if not os.getenv("JWT_KEY"):
    import warnings
    warnings.warn("JWT_KEY 未在 .env 中配置，使用了默认密钥，生产环境请务必更换！")

def create_access_token(user_id : int) -> str:
    payload = {
        "sub" : str(user_id),
        "exp" : datetime.now(timezone.utc) + timedelta(hours = 2)
    }
    token = jwt.encode(payload, JWT_KEY, ALGORITHM)
    return token

def get_user_id_from_token(token : str | None = Header(None) ) -> int :
    if not token :
        raise HTTPException(401, "未携带Token")
    try :
        payload = jwt.decode(token, JWT_KEY, [ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError
        return int(user_id)

    except (ValueError, JWTError, TypeError) :
        raise HTTPException(401, "token无效或已过期")
