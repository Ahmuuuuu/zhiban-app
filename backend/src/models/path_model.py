"""学习路径相关模型"""

from tortoise import Model, fields


class LearningPath(Model):
    """学科路径模板"""
    id = fields.IntField(pk=True, description="路径ID")
    subject = fields.CharField(max_length=128, description="学科主题")
    difficulty = fields.CharField(max_length=16, default="medium", description="难度: easy/medium/hard")
    node_count = fields.IntField(default=5, description="节点数量")
    cover_tags = fields.TextField(null=True, description="标签 JSON 数组")
    is_public = fields.BooleanField(default=True, description="是否全员可见")
    created_at = fields.DatetimeField(auto_now_add=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="learning_paths",
        null=True,
        on_delete=fields.SET_NULL,
    )

    class Meta:
        table = "learning_paths"


class PathNode(Model):
    """路径节点"""
    id = fields.IntField(pk=True, description="节点ID")
    topic = fields.CharField(max_length=256, description="节点主题")
    knowledge_tags = fields.TextField(null=True, description="知识点标签 JSON 数组")
    order_index = fields.IntField(description="节点顺序")
    prerequisites = fields.TextField(null=True, description="前置节点 ID JSON 数组")
    resource_types = fields.TextField(default="[]", description="资源类型 JSON 数组")
    quiz_config = fields.TextField(null=True, description="测验配置 JSON，含 threshold 等")

    path = fields.ForeignKeyField(
        "models.LearningPath",
        related_name="nodes",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "path_nodes"
        ordering = ["order_index"]


class UserPathProgress(Model):
    """用户进度"""
    id = fields.IntField(pk=True, description="进度记录ID")
    node_status = fields.CharField(max_length=16, default="locked", description="状态: locked/unlocked/in_progress/completed")
    resource_ids = fields.TextField(null=True, description="已生成资源 ID JSON")
    quiz_session_id = fields.CharField(max_length=64, null=True, description="预生成测验的 session_id")
    quiz_passed = fields.BooleanField(default=False, description="是否通过测验门禁")
    started_at = fields.DatetimeField(null=True, description="开始学习时间")
    completed_at = fields.DatetimeField(null=True, description="完成时间")

    user = fields.ForeignKeyField(
        "models.User",
        related_name="path_progresses",
        on_delete=fields.CASCADE,
    )
    path = fields.ForeignKeyField(
        "models.LearningPath",
        related_name="user_progresses",
        on_delete=fields.CASCADE,
    )
    node = fields.ForeignKeyField(
        "models.PathNode",
        related_name="user_progresses",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "user_path_progress"
        unique_together = [("user_id", "path_id", "node_id")]
