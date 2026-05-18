from pydantic import BaseModel, model_validator, Field


class Create_User(BaseModel):
    """注册新用户"""
    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class Login_User(BaseModel):
    """用户登录，用户名和邮箱二选一"""
    username: str | None = Field(default=None, description="用户名")
    email: str | None = Field(default=None, description="邮箱")
    password: str = Field(description="密码")

    @model_validator(mode="after")
    def must_have_one(self):
        if not self.username and not self.email:
            raise ValueError("用户名或邮箱必须填写一个")
        return self


class Update_User_Password(BaseModel):
    """修改密码"""
    ori_password: str = Field(description="原密码")
    new_password: str = Field(description="新密码")


class Update_User_Information(BaseModel):
    """更新用户资料，未传字段不更新"""
    username: str | None = Field(default=None, description="用户名")
    university: str | None = Field(default=None, description="学校")
    grade: str | None = Field(default=None, description="年级")
    major: str | None = Field(default=None, description="专业")
    email: str | None = Field(default=None, description="邮箱")
    phonenum: str | None = Field(default=None, description="手机号")
    profile: str | None = Field(default=None, description="个人简介")


class Delete_User(BaseModel):
    """注销账户，需验证密码"""
    password: str = Field(description="密码")
