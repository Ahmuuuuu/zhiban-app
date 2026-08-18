"""互动课堂持久化模型。"""

from tortoise import Model, fields


class ClassroomLesson(Model):
    """用户在某个路径节点上的最新课堂快照。"""

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="classroom_lessons", on_delete=fields.CASCADE)
    path = fields.ForeignKeyField("models.LearningPath", related_name="classroom_lessons", on_delete=fields.CASCADE)
    node = fields.ForeignKeyField("models.PathNode", related_name="classroom_lessons", on_delete=fields.CASCADE)
    lesson_json = fields.JSONField(description="完整课堂 JSON（四幕及总结）")
    resources_json = fields.JSONField(null=True, description="生成时使用的资源快照")
    quiz_session_id = fields.CharField(max_length=64, null=True, description="关联的节点练习会话")
    content_fingerprint = fields.CharField(max_length=64, description="节点输入内容指纹")
    schema_version = fields.CharField(max_length=24, default="exercise-v2", description="课堂协议版本")
    status = fields.CharField(max_length=16, default="ready", description="ready/failed")
    error_message = fields.CharField(max_length=500, null=True, description="最近一次生成错误")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "classroom_lessons"
        unique_together = [("user_id", "path_id", "node_id")]
