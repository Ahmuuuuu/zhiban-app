"""邮箱验证码"""

from tortoise import Model, fields


class EmailVerificationCode(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=128, description="邮箱地址")
    code = fields.CharField(max_length=6, description="验证码")
    purpose = fields.CharField(max_length=16, default="login", description="login/register/bind")
    used = fields.BooleanField(default=False, description="是否已使用")
    expires_at = fields.DatetimeField(description="过期时间")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "email_verification_codes"
