import logging
import os
import uuid
from pathlib import Path

from tortoise.exceptions import IntegrityError

from backend.src.models.usermodel import User

logger = logging.getLogger(__name__)
from backend.src.models.portraitmodel import User_picture
from backend.src.schemas.user import Create_User, Login_User, Update_User_Password, Update_User_Information, Delete_User, SendEmailCode, RegisterByEmail, LoginByEmail
from backend.src.utils.pwintohash import get_password_hash, verify_password


async def _on_profile_changed(user_id: int, major: str, grade: str):
    """专业/年级变更时后台执行：同步课程体系 → 生成学习路径 → 发通知"""
    try:
        # 0. 时间窗口防抖：1 小时内不重复执行
        from datetime import datetime, timedelta
        from backend.src.models.path_model import LearningPath
        recent = await LearningPath.filter(
            user_id=user_id,
            created_at__gte=datetime.now() - timedelta(hours=1),
        ).first()
        if recent:
            logger.info("_on_profile_changed 跳过（1小时内已生成过路径） user=%s", user_id)
            return

        # 1. 同步课程到画像
        from backend.src.service.curriculum_service import sync_to_portrait
        courses = await sync_to_portrait(user_id, major, grade)

        if not courses:
            return

        # 2. 为所有课程并行生成学习路径（generate_path 内部去重，cached=True 表示已存在）
        from backend.src.service.path_service import PathService
        from backend.src.models.notification_model import Notification
        import asyncio

        results = await asyncio.gather(
            *[PathService.generate_path(course, user_id, "medium", 0) for course in courses],
            return_exceptions=True,
        )

        new_paths = []
        cached_count = 0
        for course, result in zip(courses, results):
            if isinstance(result, Exception):
                logger.exception("自动生成路径失败 user=%s course=%s", user_id, course)
                continue
            if "error" in result:
                continue
            if result.get("cached"):
                cached_count += 1
            else:
                new_paths.append(result)

        # 3. 发通知（仅当有新路径时）
        if new_paths:
            course_names = "、".join(p.get("subject", "") for p in new_paths)
            grade_text = f"{grade}" if grade else ""
            suffix = f"（另外 {cached_count} 门已存在，已跳过）" if cached_count else ""
            await Notification.create(
                type="system",
                title="学习路径已生成",
                content=f"检测到你的专业/年级更新为{grade_text}{major}，已自动为你生成 {len(new_paths)} 条学习路径（{course_names}）。{suffix}",
                target_url="/learning-path",
                target_user_id=user_id,
            )
            logger.info("专业/年级变更 → 自动生成路径 user=%s major=%s grade=%s new=%d cached=%d",
                        user_id, major, grade, len(new_paths), cached_count)
    except Exception:
        logger.exception("_on_profile_changed 失败 user=%s", user_id)


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
        except IntegrityError:
            return None, "用户名重复"
        except Exception as e:
            logger.exception("用户注册失败 username=%s", data.username)
            return None, "注册失败，请稍后重试"

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
            major_changed = data.major is not None and data.major != user.major
            grade_changed = data.grade is not None and data.grade != user.grade

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

            # 清除画像上下文缓存，让下次对话立即看到最新信息
            from backend.src.service.chat_service import invalidate_portrait_cache
            invalidate_portrait_cache(user_id)

            # 专业或年级变更时，后台异步：同步课程体系 + 生成学习路径 + 通知
            if major_changed or grade_changed:
                import asyncio
                asyncio.ensure_future(_on_profile_changed(user_id, user.major or "", user.grade or ""))

            return user, "信息修改成功"
        
    @staticmethod
    async def upload_avatar(user_id: int, file_content: bytes, filename: str) -> tuple:
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "用户不存在"

        # 删除旧头像文件
        if user.avatar:
            old_path = Path(__file__).parent.parent.parent / user.avatar.lstrip("/")
            if old_path.exists():
                old_path.unlink()

        # 保存新头像
        ext = os.path.splitext(filename)[1] or ".png"
        avatar_dir = Path(__file__).parent.parent.parent / "static" / "avatars"
        avatar_dir.mkdir(parents=True, exist_ok=True)

        save_name = f"{user_id}_{uuid.uuid4().hex}{ext}"
        save_path = avatar_dir / save_name
        save_path.write_bytes(file_content)

        url_path = f"/static/avatars/{save_name}"
        user.avatar = url_path
        await user.save()
        return user, "头像上传成功"

    @staticmethod
    async def delete_avatar(user_id: int) -> tuple:
        user = await User.filter(id=user_id).first()
        if not user:
            return None, "用户不存在"
        if not user.avatar:
            return None, "没有头像"

        file_path = Path(__file__).parent.parent.parent / user.avatar.lstrip("/")
        if file_path.exists():
            file_path.unlink()

        user.avatar = None
        await user.save()
        return user, "头像删除成功"

    @staticmethod
    async def send_email_code(email: str, purpose: str = "login"):
        """发送邮箱验证码"""
        from datetime import datetime, timedelta
        import random
        from backend.src.models.email_code_model import EmailVerificationCode
        from backend.src.utils.email_sender import send_email

        # 1 分钟内不能重复发
        recent = await EmailVerificationCode.filter(
            email=email, purpose=purpose, used=False,
            created_at__gte=datetime.now() - timedelta(minutes=1),
        ).order_by("-created_at").first()
        if recent:
            return None, "请 1 分钟后再试"

        code = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now() + timedelta(minutes=10)

        await EmailVerificationCode.create(
            email=email, code=code, purpose=purpose, expires_at=expires_at
        )

        ok = send_email(
            to_email=email,
            subject="智伴 - 邮箱验证码",
            body=f"您的验证码是：{code}，有效期 10 分钟。如非本人操作，请忽略。",
        )
        if not ok:
            return None, "邮件发送失败，请检查邮箱地址或稍后重试"
        return {"msg": "验证码已发送"}, "success"

    @staticmethod
    async def register_by_email(email: str, code: str, password: str, username: str):
        """邮箱注册 — 验证码校验后创建用户"""
        from datetime import datetime
        from backend.src.models.email_code_model import EmailVerificationCode
        from tortoise.exceptions import IntegrityError

        # 校验验证码
        record = await EmailVerificationCode.filter(
            email=email, code=code, purpose="register", used=False,
            expires_at__gte=datetime.now(),
        ).order_by("-created_at").first()
        if not record:
            return None, "验证码无效或已过期"

        # 检查用户名
        exists = await User.filter(username=username).first()
        if exists:
            return None, "用户名已被占用"

        try:
            user = await User.create(
                username=username,
                password=get_password_hash(password),
                email=email,
            )
            # 创建画像记录
            from backend.src.models.portraitmodel import User_picture
            picture = await User_picture.create()
            user.picture = picture
            await user.save()

            # 标记验证码已用
            record.used = True
            await record.save()

            return user, "注册成功"
        except IntegrityError:
            return None, "注册失败，请稍后重试"

    @staticmethod
    async def login_by_email(email: str, code: str):
        """邮箱验证码登录 — 校验验证码后直接登录"""
        from datetime import datetime
        from backend.src.models.email_code_model import EmailVerificationCode

        record = await EmailVerificationCode.filter(
            email=email, code=code, purpose="login", used=False,
            expires_at__gte=datetime.now(),
        ).order_by("-created_at").first()
        if not record:
            return None, "验证码无效或已过期"

        user = await User.filter(email=email).first()
        if not user:
            return None, "该邮箱未注册"

        record.used = True
        await record.save()
        return user, "登录成功"

    @staticmethod
    async def delete_user(user_id : int, data : Delete_User) : 
        user = await User.filter(id = user_id).first()
        if not user:
            return None, "未查找到用户"
        else :
            if not verify_password(data.password, user.password):
                return None, "密码错误"
            await user.delete()
            return user, "删除成功"
