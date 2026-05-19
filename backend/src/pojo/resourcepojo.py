from pydantic import BaseModel, Field


class GenerateResourceRequest(BaseModel):
    topic: str = Field(default="", description="学习主题，为空则从 chat_group_id 提取")
    resource_types: list[str] = Field(
        default=["document"],
        description="资源类型列表: document / ppt / mindmap / exercise / case / reading"
    )
    chat_group_id: int = Field(default=0, description="对话分组ID，传此值可自动提取主题")
