from backend.src.models.usermodel import User
from backend.src.utils.knowledge_base import list_grouped
from backend.src.utils.pwintohash import get_password_hash


async def list_users() -> list[dict]:
    users = await User.all().prefetch_related("picture")
    return [
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "university": user.university,
            "grade": user.grade,
            "major": user.major,
            "email": user.email,
            "phonenum": user.phonenum,
            "profile": user.profile,
            "has_picture": user.picture_id is not None,
            "created_at": str(user.created_at),
        }
        for user in users
    ]


async def delete_user(user_id: int) -> str:
    user = await User.filter(id=user_id).first()
    if not user:
        return "用户不存在"
    if user.role == "admin":
        return "不能删除管理员"
    username = user.username
    await user.delete()
    return f"用户 '{username}' 已删除"


async def reset_password(user_id: int, new_password: str) -> str:
    user = await User.filter(id=user_id).first()
    if not user:
        return "用户不存在"
    user.password = get_password_hash(new_password)
    await user.save()
    return f"用户 '{user.username}' 密码已重置"


async def list_knowledge_base() -> list[dict]:
    return await list_grouped()
