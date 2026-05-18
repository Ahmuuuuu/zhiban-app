from tortoise import Model, fields

class User(Model):
    id = fields.IntField(pk = True, description = "用户ID")
    username = fields.CharField(max_length = 32, unique = True, description = "用户账号")
    password = fields.CharField(max_length = 256, description = "用户密码")
    university = fields.CharField(max_length=100, null=True, description="大学名称")
    grade = fields.CharField(max_length=20, null=True, description="年级")
    major = fields.TextField(null = True, description = "用户专业")
    email = fields.TextField(null = True, description = "用户邮箱")
    phonenum = fields.CharField(max_length=20, null=True, description="用户手机号")
    profile = fields.CharField(null = True, max_length = 200, description = "用户简介")
    role = fields.CharField(max_length=20, default="user", description="用户角色：user/admin")
    created_at = fields.DatetimeField(auto_now_add = True, null =True)
    updated_at = fields.DatetimeField(auto_now = True, null = True)

    picture = fields.OneToOneField(
        "models.User_picture",
        related_name = "user",
        null = True,
        on_delete = fields.SET_NULL
    )


    class Meta:
        table = "sys_user"

