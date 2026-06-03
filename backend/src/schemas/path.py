"""学习路径请求/响应模型"""

from pydantic import BaseModel, Field


class GeneratePathRequest(BaseModel):
    """生成学习路径（user_id 从 token 提取）"""
    subject: str = Field(description="学科主题")
    difficulty: str = Field(default="medium", description="难度: easy/medium/hard")
    node_count: int = Field(default=5, description="节点数量")


class EnrollPathRequest(BaseModel):
    """加入路径学习"""
    path_id: int = Field(description="路径 ID")


class SubmitNodeQuizRequest(BaseModel):
    """提交节点测验"""
    session_id: str = Field(description="答题会话 session_id")


class RegeneratePathRequest(BaseModel):
    """基于最新画像重建路径"""
    path_id: int = Field(description="路径 ID")


class GenerateFromProfileRequest(BaseModel):
    """根据用户专业年级自动生成学习路径"""
    course_limit: int = Field(default=3, description="最多为几门课程生成路径")
    difficulty: str = Field(default="medium", description="难度: easy/medium/hard")
    node_count: int = Field(default=0, description="节点数，0=自动")
