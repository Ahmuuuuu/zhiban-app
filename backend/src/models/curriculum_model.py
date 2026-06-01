"""课程体系模型 — 专业×年级 → 核心课程"""

from tortoise import Model, fields


class CurriculumCourse(Model):
    id = fields.IntField(pk=True)
    major = fields.CharField(max_length=100, description="专业名称")
    grade = fields.CharField(max_length=20, description="年级：大一/大二/大三/大四")
    courses = fields.TextField(description="核心课程列表，JSON 数组字符串")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "curriculum_courses"
        unique_together = [("major", "grade")]
