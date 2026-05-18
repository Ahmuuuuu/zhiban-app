from pydantic import BaseModel, Field


class Init_Portrait(BaseModel):
    """前端弹窗一次性提交的初始画像标签"""
    cognition: str | None = Field(default=None, description="认知风格：视觉型/听觉型/读写型/实践型")
    learning_goal: str | None = Field(default=None, description="学习目标：考试/竞赛/考证/兴趣/求职")
    personality_tags: str | list[str] | None = Field(default=None, description="性格标签（JSON 数组或列表）")
