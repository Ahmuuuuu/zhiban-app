from typing import Optional
from pydantic import BaseModel, Field


class CreateNewHistory(BaseModel):
    """新建对话"""
    user_req: str = Field(description="用户提问内容")
    agent_id: Optional[int] = Field(default=None, description="自建智能体ID")


class CreateMsgIntoHistory(BaseModel):
    """向已有对话追加消息"""
    chat_group_id: int = Field(description="对话组 ID")
    user_req: str = Field(description="用户提问内容")
    agent_id: Optional[int] = Field(default=None, description="自建智能体ID")


class StreamNewHistory(BaseModel):
    """流式新建对话"""
    user_req: str = Field(description="用户提问内容")
    agent_id: Optional[int] = Field(default=None, description="自建智能体ID")


class StreamMsgIntoHistory(BaseModel):
    """流式追加消息到已有对话"""
    chat_group_id: int = Field(description="对话组 ID")
    user_req: str = Field(description="用户提问内容")
    agent_id: Optional[int] = Field(default=None, description="自建智能体ID")
