"""管理员身份校验 —— 仅 role='admin' 的用户可执行系统操作"""
from backend.src.models.usermodel import User


async def is_admin(user_id: int) -> bool:
    user = await User.filter(id=user_id).first()
    return user is not None and user.role == "admin"
