from backend.src.models.usermodel import User
from backend.src.models.portraitmodel import User_picture
from backend.src.pojo.userpojo import Create_User, Login_User, Update_User_Password, Update_User_Information, Delete_User
from backend.src.utils.pwintohash import get_password_hash, verify_password


class UserService():
    @staticmethod
    async def create_user(data: Create_User):
        try:
            user = await User.create(
                username=data.username,
                password=get_password_hash(data.password)
            )
            # 创建用户时同步创建一条空的画像记录
            picture = await User_picture.create()
            user.picture = picture
            await user.save()
            return user, "注册成功"
        except Exception:
            return None, "用户名重复"

    @staticmethod
    async def login_user(data : Login_User):
        if data.username :
            user = await User.filter(username = data.username).first()
        elif data.email : 
            user = await User.filter(email = data.email).first()
        else :
            return None, "请输入用户或者邮箱"
        if not user : 
            return None, "用户不存在"
        if not verify_password(data.password, user.password):
            return  None, "密码错误"
        return user, "登陆成功"
    
    @staticmethod
    async def read_user(user_id : int):
        user = await User.filter(id = user_id).first()
        if not user:
            return None, "未查找到用户"
        else :
            return user, "查找成功"
        
    @staticmethod
    async def update_user_password(user_id : int , data : Update_User_Password) :
        user = await User.filter(id = user_id).first()
        if not user : 
            return None, "未查找到该用户"
        else : 
            if not verify_password(data.ori_password, user.password):
                return None, "原密码密码错误"
            else : 
                user.password = get_password_hash(data.new_password)
                await user.save()
                return user, "密码修改成功"

    @staticmethod
    async def update_user_information(user_id : int, data : Update_User_Information) :
        user = await User.filter(id = user_id).first()
        if not user :
            return None, "未查找到用户"
        else :
            if data.username is not None:
                user.username = data.username
            if data.university is not None:
                user.university = data.university
            if data.grade is not None:
                user.grade = data.grade
            if data.major is not None:
                user.major = data.major
            if data.email is not None:
                user.email = data.email
            if data.phonenum is not None:
                user.phonenum = data.phonenum
            if data.profile is not None and len(data.profile) <= 200:
                user.profile = data.profile
            await user.save()
            return user, "信息修改成功"
        
    @staticmethod
    async def delete_user(user_id : int, data : Delete_User) : 
        user = await User.filter(id = user_id).first()
        if not user:
            return None, "未查找到用户"
        else :
            await user.delete()
            return user, "删除成功"
