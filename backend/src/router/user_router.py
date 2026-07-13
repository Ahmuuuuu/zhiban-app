from fastapi import APIRouter, HTTPException, Depends, Body, UploadFile, File
from backend.src.service.user import service as user_service
from backend.src.utils.jwt import create_access_token, get_user_id_from_token
from backend.src.schemas.user import Create_User, Login_User, Update_User_Password, Update_User_Information, Delete_User, SendEmailCode, RegisterByEmail, LoginByEmail

router = APIRouter(prefix = "/user", tags = ["用户"])

@router.post("/create_user")
async def create(data : Create_User):
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
async def login(data : Login_User):
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
async def send_email_code(data: SendEmailCode = Body(...)):
    try:
        _, msg = await user_service.send_email_code(data.email, data.purpose)
        if msg != "success":
            return {"code": 400, "msg": msg}
        return {"code": 200, "msg": "验证码已发送"}
    except HTTPException:
        raise HTTPException(500, "服务器错误")


@router.post("/register_by_email")
async def register_by_email(data: RegisterByEmail = Body(...)):
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
async def login_by_email(data: LoginByEmail = Body(...)):
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
                    "avatar" : user.avatar
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
