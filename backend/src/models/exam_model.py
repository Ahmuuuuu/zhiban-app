"""题库相关模型"""

from tortoise import Model, fields


class ExamQuestion(Model):
    """题库表"""
    id = fields.IntField(pk=True, description="题目ID")
    question_type = fields.CharField(max_length=32, description="题型: single_choice/multi_choice/true_false/fill_blank/short_answer")
    content = fields.TextField(description="题目正文")
    options = fields.TextField(null=True, description="选项 JSON 数组，非选择题为 null")
    answer = fields.TextField(description="正确答案")
    analysis = fields.TextField(null=True, description="解析")
    difficulty = fields.CharField(max_length=16, default="medium", description="难度: easy/medium/hard")
    knowledge_tags = fields.TextField(null=True, description="知识点标签 JSON 数组")
    point_value = fields.IntField(null=True, description="题目分值(null则按难度自动计算)")
    is_public = fields.BooleanField(default=True, description="是否全员可见")
    created_at = fields.DatetimeField(auto_now_add=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="exam_questions",
        null=True,
        on_delete=fields.SET_NULL,
    )

    class Meta:
        table = "exam_questions"


class ExamRecord(Model):
    """答题记录表"""
    id = fields.IntField(pk=True, description="记录ID")
    user_answer = fields.TextField(null=True, description="用户提交的答案")
    is_correct = fields.BooleanField(null=True, description="是否正确（简答题可为 null）")
    score = fields.FloatField(null=True, description="得分(0-100)，简答题为 null")
    time_spent = fields.IntField(null=True, description="作答耗时（秒）")
    session_id = fields.CharField(max_length=64, description="一次练习的统一标识")
    created_at = fields.DatetimeField(auto_now_add=True)

    question = fields.ForeignKeyField(
        "models.ExamQuestion",
        related_name="records",
        on_delete=fields.CASCADE,
    )
    user = fields.ForeignKeyField(
        "models.User",
        related_name="exam_records",
        on_delete=fields.CASCADE,
    )
    node = fields.ForeignKeyField(
        "models.PathNode",
        related_name="exam_records",
        null=True,
        on_delete=fields.SET_NULL,
        description="所属学习路径节点（非路径题目为 null）",
    )

    class Meta:
        table = "exam_records"


class KnowledgeMastery(Model):
    """知识点掌握度表"""
    id = fields.IntField(pk=True, description="记录ID")
    knowledge_tag = fields.CharField(max_length=128, description="知识点标签")
    total_attempts = fields.IntField(default=0, description="总答题数")
    correct_count = fields.IntField(default=0, description="答对数")
    mastery_level = fields.CharField(max_length=16, default="beginner", description="掌握等级: beginner/learning/proficient/mastered")
    last_practiced_at = fields.DatetimeField(null=True, description="上次练习时间")

    user = fields.ForeignKeyField(
        "models.User",
        related_name="knowledge_masteries",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "knowledge_mastery"
        unique_together = [("user_id", "knowledge_tag")]
