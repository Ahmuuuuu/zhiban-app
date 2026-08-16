from tortoise import Model, fields


class MemoryMessage(Model):
    """语义原文索引：对重要聊天原文建向量，支持'你上次说过…'式检索"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="memory_messages", on_delete=fields.CASCADE
    )
    chat_group_id = fields.IntField(null=True)
    source_history_id = fields.IntField(null=True, description="对应 chat_history.id")
    role = fields.CharField(max_length=8, default="user", description="user/assistant/pair")
    content = fields.TextField(description="被索引的原文（req+res 或单条 req）")
    embedding = fields.TextField(description="向量（JSON 数组字符串）")
    subjects = fields.JSONField(null=True)
    importance = fields.FloatField(default=0.5)
    created_at = fields.DatetimeField(auto_now_add=True, null=True)

    class Meta:
        table = "memory_message_vector"
        indexes = (
            ("user_id", "chat_group_id"),
            ("user_id", "created_at"),
        )
