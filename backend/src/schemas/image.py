from pydantic import BaseModel, Field


class GenerateImageRequest(BaseModel):
    prompt: str = Field(description="图片描述，中英文均可")
    aspect_ratio: str = Field(default="1:1", description="宽高比 1:1 / 16:9 / 9:16")
    img_count: int = Field(default=1, ge=1, le=4, description="生成数量 1-4")
    chat_group_id: int = Field(default=0, description="对话分组ID")
