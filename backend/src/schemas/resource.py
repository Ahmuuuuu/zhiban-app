from pydantic import BaseModel, Field


class GenerateResourceRequest(BaseModel):
    topic: str = Field(default="", description="学习主题，为空则从 chat_group_id 提取")
    resource_types: list[str] = Field(
        default=[],
        description="资源类型列表，为空则由 LeaderAgent 自动决定"
    )
    chat_group_id: int = Field(default=0, description="对话分组ID，传此值可自动提取主题")
    answers: dict | None = Field(default=None, description="视频模式：用户追问作答 {focus, depth}，注入 prompt 按需生成")
