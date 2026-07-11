from pydantic import BaseModel, Field


class GenerateResourceRequest(BaseModel):
    topic: str = Field(default="", description="学习主题，为空则从 chat_group_id 提取")
    resource_types: list[str] = Field(
        default=[],
        description="资源类型列表，为空则由 LeaderAgent 自动决定"
    )
    chat_group_id: int = Field(default=0, description="对话分组ID，传此值可自动提取主题")
    bind_chat_history: bool = Field(default=False, description="Bind generated resources to chat history when chat_group_id is missing")
    answers: dict | None = Field(default=None, description="视频模式：用户追问作答 {focus, depth}，注入 prompt 按需生成")
    ppt_theme_id: str | None = Field(default=None, description="前端选择的 PPT 模板/主题 ID")
    force_regenerate: bool = Field(default=False, description="强制重新生成，无视已缓存的同主题资源")
    skip_review: bool = Field(default=False, description="跳过 AI 审核（视频模式等对质量要求不极端的场景）")

