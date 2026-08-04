from tortoise import Model, fields


class MemoryKV(Model):
    """长期语义记忆 KV：结构化客观事实（user 级全局 / group 级本组）"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="memory_kvs", on_delete=fields.CASCADE
    )
    key = fields.CharField(max_length=64, description="语义键，如 learning_goal / exam_date / weak_subject")
    value = fields.TextField(description="结构化事实值（简洁中文）")
    scope = fields.CharField(max_length=8, default="user", description="user=全局用户级；group=仅当前会话组可见")
    subjects = fields.JSONField(null=True, description="学科/主题标签列表")
    source_group_id = fields.IntField(null=True, description="来源会话组")
    source_agent_id = fields.IntField(null=True, description="来源智能体")
    source = fields.CharField(max_length=16, default="agent_inferred", description="user_stated / agent_inferred / auto")
    confidence = fields.FloatField(default=0.5, description="0~1")
    version = fields.IntField(default=1, description="冲突解决：每次覆盖 version+1")
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "memory_kv"
        unique_together = (("user_id", "key", "scope"),)   # 同一用户同一键同一作用域只有一条
        indexes = (
            ("user_id", "updated_at"),
            ("user_id", "scope"),
        )
