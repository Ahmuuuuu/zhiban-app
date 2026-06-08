from pydantic import BaseModel, Field


class CreateAnnotationRequest(BaseModel):
    """创建笔记"""
    source_type: str = Field(default="generated", description="资源来源: generated/knowledge")
    source_id: int = Field(description="来源记录的主键ID")
    selected_text: str = Field(description="用户选中的原文")
    note_text: str = Field(description="用户的笔记内容")
    position: dict | None = Field(default=None, description="定位信息(JSON)")


class UpdateAnnotationRequest(BaseModel):
    """更新笔记"""
    note_text: str = Field(description="新的笔记内容")
