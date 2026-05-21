from pydantic import BaseModel, Field


class GenerateExamRequest(BaseModel):
    """AI 生成题目"""
    topic: str = Field(description="学习主题")
    user_id: int = Field(description="用户 ID")
    count: int = Field(default=5, description="生成数量")
    difficulty: str = Field(default="medium", description="难度: easy/medium/hard")
    question_types: str = Field(default="single_choice", description="题型（逗号分隔）: single_choice/multi_choice/true_false/fill_blank/short_answer")


class SubmitAnswerRequest(BaseModel):
    """提交答案"""
    question_id: int = Field(description="题目 ID")
    user_id: int = Field(description="用户 ID")
    answer: str = Field(description="用户答案")
    time_spent: int | None = Field(default=None, description="作答耗时（秒）")
