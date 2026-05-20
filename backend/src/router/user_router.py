from fastapi import APIRouter, HTTPException, Depends, Body
from backend.src.service.userservice import UserService
from backend.src.utils.jwt import create_access_token, get_user_id_from_token
from backend.src.schemas.user import Create_User, Login_User, Update_User_Password, Update_User_Information, Delete_User

router = APIRouter(prefix = "/user", tags = ["用户"])

@router.post("/create_user")
async def create(data : Create_User):
    try :
        user, msg = await UserService.create_user(data)
        if user is not None:
            return {
                "code" : 200,
                "msg" : "success",
                "data" : {
                    "id" : create_access_token(user.id),
                    "username" : user.username
                }
            }
        else :
            return {
                "code" : 409,
                "msg" : msg
            }
    except HTTPException :
        raise HTTPException(500, "服务器错误")
    
@router.post("/login_user")
async def login(data : Login_User):
    try : 
        user, msg = await UserService.login_user(data)
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
                    "id" : create_access_token(user.id)
                }
            }
    except HTTPException:
        raise HTTPException(500, "服务器错误")
    
@router.get("/read_user")
async def read(user_id : int = Depends(get_user_id_from_token)):
    try : 
        user, msg = await UserService.read_user(user_id)
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
                    "id" : create_access_token(user.id),
                    "username" : user.username,
                    "university" : user.university,
                    "grade" : user.grade,
                    "major" : user.major,
                    "email" : user.email,
                    "phonenum" : user.phonenum,
                    "profile" : user.profile
                }
            }
    except HTTPException:
        raise HTTPException(500, "服务器错误")
    
@router.post("/update_user/information")
async def update_information(user_id : int = Depends(get_user_id_from_token), data : Update_User_Information = Body(...)):
    try : 
        user, msg = await UserService.update_user_information(user_id, data)
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
                    "id" : create_access_token(user.id)
                }
            }
    except HTTPException :
        raise HTTPException(500, "服务器错误")
    
@router.post("/update_user/password")
async def update_password(user_id : int = Depends(get_user_id_from_token), data : Update_User_Password = Body(...)):
    try : 
        user, msg = await UserService.update_user_password(user_id, data)
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
                    "id" : create_access_token(user.id)
                }
            }
    except HTTPException :
        raise HTTPException(500, "服务器错误")
    
@router.delete("/delete_user")
async def delete(user_id : int = Depends(get_user_id_from_token), data : Delete_User = Body(...)):
    try :
        user, msg = await UserService.delete_user(user_id, data)
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
                    "id" : create_access_token(user.id)
                }
            }
    except HTTPException:
        raise HTTPException(500, "服务器错误")