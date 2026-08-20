import hashlib
import logging

from fastapi import APIRouter, HTTPException, Depends, Body, UploadFile, File, Request
from backend.src.service.user import service as user_service
from backend.src.utils.jwt import create_access_token, get_user_id_from_token
from backend.src.utils.redis_client import check_rate_limit_key
from backend.src.schemas.user import Create_User, Login_User, Update_User_Password, Update_User_Information, Delete_User, SendEmailCode, RegisterByEmail, LoginByEmail

router = APIRouter(prefix = "/user", tags = ["用户"])
logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    """读取反向代理后的真实 IP；仅信任来自本机 Nginx 的转发头。"""
    peer = request.client.host if request.client else "unknown"
    if peer in {"127.0.0.1", "::1"}:
        forwarded = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return peer


def _identity(value: str) -> str:
    return hashlib.sha256(str(value or "unknown").strip().lower().encode("utf-8")).hexdigest()[:32]


async def _guard_anonymous(request: Request, scope: str, limit: int, window: int, label: str = "请求"):
    identity = _client_ip(request)
    if not await check_rate_limit_key(scope, f"ip:{_identity(identity)}", limit, window):
        logger.warning("匿名接口触发限流 scope=%s ip=%s", scope, identity)
        raise HTTPException(status_code=429, detail=f"{label}过于频繁，请稍后再试")


async def _guard_value(value: str, scope: str, limit: int, window: int, label: str = "请求"):
    if not await check_rate_limit_key(scope, f"value:{_identity(value)}", limit, window):
        raise HTTPException(status_code=429, detail=f"{label}过于频繁，请稍后再试")

@router.post("/create_user")
async def create(data : Create_User, request: Request):
    # 兼容旧注册接口，但限制匿名批量创建；新前端使用邮箱验证码注册。
    await _guard_anonymous(request, "auth:legacy-register", 5, 600, "注册")
    try :
        user, msg = await user_service.create_user(data)
        if user is not None:
            return {
                "code" : 200,
                "msg" : "success",
                "data" : {
                    "id" : create_access_token(user.id, user.role or "user"),
                    "username" : user.username
                }
            }
        else :
            return {
                "code" : 409,
                "msg" : msg
            }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")
    
@router.post("/login_user")
async def login(data : Login_User, request: Request):
    await _guard_anonymous(request, "auth:password-login", 30, 600, "登录")
    await _guard_value(data.username or data.email or "", "auth:password-login-account", 12, 600, "登录")
    try : 
        user, msg = await user_service.login_user(data)
        if user is None:
            return {
                "code" : 404,
                "msg" : msg,
            }
        else :
            return {
                "code" : 200,
                "msg" : msg,
                "data" : {
                    "id" : user.id,
                    "token" : create_access_token(user.id, user.role or "user"),
                    "username" : user.username,
                    "role" : user.role or "user",
                }
            }
    except HTTPException:
        raise HTTPException(500, "服务器错误")


@router.post("/send_email_code")
async def send_email_code(request: Request, data: SendEmailCode = Body(...)):
    await _guard_anonymous(request, "auth:email-code-ip", 10, 600, "验证码发送")
    await _guard_value(data.email, "auth:email-code-email", 5, 600, "验证码发送")
    try:
        _, msg = await user_service.send_email_code(data.email, data.purpose)
        if msg != "success":
            return {"code": 400, "msg": msg}
        return {"code": 200, "msg": "验证码已发送"}
    except HTTPException:
        raise HTTPException(500, "服务器错误")


@router.post("/register_by_email")
async def register_by_email(request: Request, data: RegisterByEmail = Body(...)):
    await _guard_anonymous(request, "auth:email-register-ip", 6, 600, "注册")
    await _guard_value(data.email, "auth:email-register-email", 3, 3600, "注册")
    try:
        user, msg = await user_service.register_by_email(data.email, data.code, data.password, data.username)
        if user is None:
            return {"code": 400, "msg": msg}
        return {
            "code": 200,
            "msg": msg,
            "data": {"id": create_access_token(user.id, user.role or "user"), "username": user.username},
        }
    except HTTPException:
        raise HTTPException(500, "服务器错误")


@router.post("/login_by_email")
async def login_by_email(request: Request, data: LoginByEmail = Body(...)):
    await _guard_anonymous(request, "auth:email-login-ip", 20, 600, "登录")
    await _guard_value(data.email, "auth:email-login-email", 12, 600, "登录")
    try:
        user, msg = await user_service.login_by_email(data.email, data.code)
        if user is None:
            return {"code": 400, "msg": msg}
        return {
            "code": 200,
            "msg": msg,
            "data": {
                "id": user.id,
                "token": create_access_token(user.id, user.role or "user"),
                "username": user.username,
                "role": user.role or "user",
            },
        }
    except HTTPException:
        raise HTTPException(500, "服务器错误")


@router.get("/read_user")
async def read(user_id : int = Depends(get_user_id_from_token)):
    try : 
        user, msg = await user_service.read_user(user_id)
        if user is None:
            return {
                "code" : 404,
                "msg" : msg
            }
        else : 
            return {
                "code" : 200,
                "msg" : msg,
                "data" : {
                    "id" : user.id,
                    "username" : user.username,
                    "university" : user.university,
                    "grade" : user.grade,
                    "major" : user.major,
                    "email" : user.email,
                    "phonenum" : user.phonenum,
                    "profile" : user.profile,
                    "avatar" : user.avatar,
                    "role" : user.role or "user",
                }
            }
    except HTTPException:
        raise HTTPException(500, "服务器错误")
    
@router.post("/update_user/information")
async def update_information(user_id : int = Depends(get_user_id_from_token), data : Update_User_Information = Body(...)):
    try : 
        user, msg = await user_service.update_user_information(user_id, data)
        if user is None:
            return {
                "code" : 404,
                "msg" : msg
            }
        else :
            return {
                "code" : 200,
                "msg" : msg,
                "data" : {
                    "id" : create_access_token(user.id, user.role or "user")
                }
            }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")
    
@router.post("/update_user/password")
async def update_password(user_id : int = Depends(get_user_id_from_token), data : Update_User_Password = Body(...)):
    try : 
        user, msg = await user_service.update_user_password(user_id, data)
        if user is None:
            return {
                "code" : 404,
                "msg" : msg
            }
        else :
            return {
                "code" : 200,
                "msg" : msg,
                "data" : {
                    "id" : create_access_token(user.id, user.role or "user")
                }
            }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")
    
@router.post("/avatar")
async def upload_avatar(user_id: int = Depends(get_user_id_from_token), file: UploadFile = File(...)):
    try:
        if not file.filename:
            return {"code": 400, "msg": "未选择文件"}
        content = await file.read()
        user, msg = await user_service.upload_avatar(user_id, content, file.filename)
        if user is None:
            return {"code": 404, "msg": msg}
        return {
            "code": 200,
            "msg": msg,
            "data": {"avatar": user.avatar}
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")

@router.delete("/avatar")
async def delete_avatar(user_id: int = Depends(get_user_id_from_token)):
    try:
        user, msg = await user_service.delete_avatar(user_id)
        if user is None:
            return {"code": 404, "msg": msg}
        return {"code": 200, "msg": msg}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "服务器错误")

@router.delete("/delete_user")
async def delete(user_id : int = Depends(get_user_id_from_token), data : Delete_User = Body(...)):
    try :
        user, msg = await user_service.delete_user(user_id, data)
        if user is None :
            return {
                "code" : 404,
                "msg" : msg
            } 
        else :
            return {
                "code" : 200,
                "msg" : msg,
                "data" : {
                    "id" : create_access_token(user.id, user.role or "user")
                }
            }
    except HTTPException:
        raise HTTPException(500, "服务器错误")
