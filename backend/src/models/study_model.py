"""学习统计相关模型 — 学习时长、资源已读"""

from tortoise import Model, fields


class StudySession(Model):
    """每日学习时长表（心跳聚合）"""
    id = fields.IntField(pk=True)
    date = fields.DateField(description="日期")
    total_seconds = fields.IntField(default=0, description="当日累计学习秒数")
    last_heartbeat_at = fields.DatetimeField(null=True)

    user = fields.ForeignKeyField("models.User", related_name="study_sessions", on_delete=fields.CASCADE)

    class Meta:
        table = "study_sessions"
        unique_together = [("user_id", "date")]


class ResourceReadStatus(Model):
    """资源已读标记"""
    id = fields.IntField(pk=True)
    is_read = fields.BooleanField(default=False)
    read_at = fields.DatetimeField(null=True)

    user = fields.ForeignKeyField("models.User", related_name="resource_reads", on_delete=fields.CASCADE)
    resource = fields.ForeignKeyField("models.GeneratedResource", related_name="read_statuses", on_delete=fields.CASCADE)

    class Meta:
        table = "resource_read_status"
        unique_together = [("user_id", "resource_id")]


class ResourceCollection(Model):
    """资源收藏"""
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    user = fields.ForeignKeyField("models.User", related_name="resource_collections", on_delete=fields.CASCADE)
    resource = fields.ForeignKeyField("models.GeneratedResource", related_name="collections", on_delete=fields.CASCADE)

    class Meta:
        table = "resource_collections"
        unique_together = [("user_id", "resource_id")]


class ResourceLike(Model):
    """资源点赞"""
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    user = fields.ForeignKeyField("models.User", related_name="resource_likes", on_delete=fields.CASCADE)
    resource = fields.ForeignKeyField("models.GeneratedResource", related_name="likes", on_delete=fields.CASCADE)

    class Meta:
        table = "resource_likes"
        unique_together = [("user_id", "resource_id")]
