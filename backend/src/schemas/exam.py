from typing import Optional, Union, List
from pydantic import BaseModel, Field


class GenerateExamRequest(BaseModel):
    """AI 生成题目（user_id 从 token 提取）"""
    topic: str = Field(description="学习主题")
    count: int = Field(default=5, description="生成数量")
    difficulty: str = Field(default="medium", description="难度: easy/medium/hard")
    question_types: str = Field(default="single_choice", description="题型（逗号分隔）: single_choice/multi_choice/true_false/fill_blank/short_answer")


class SubmitAnswerRequest(BaseModel):
    """提交答案"""
    question_id: int = Field(description="题目 ID")
    answer: Union[str, List[str]] = Field(description="用户答案（单选/判断为字符串，多选为数组）")
    time_spent: Optional[int] = Field(default=None, description="作答耗时（秒）")
    session_id: Optional[str] = Field(default=None, description="练习会话 ID，不传则自动生成")
