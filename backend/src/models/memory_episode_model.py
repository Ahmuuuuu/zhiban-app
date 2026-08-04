from tortoise import Model, fields


class MemoryEpisode(Model):
    """长期情景记忆：每个会话组的滚动摘要，携带向量用于跨组语义检索"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="memory_episodes", on_delete=fields.CASCADE
    )
    chat_group_id = fields.IntField(null=True, description="所属会话组")
    agent_id = fields.IntField(null=True)
    summary = fields.TextField(default="", description="该会话的滚动摘要")
    subjects = fields.JSONField(null=True, description="学科标签列表")
    embedding = fields.TextField(null=True, description="summary 向量（JSON 数组字符串）")
    start_time = fields.DatetimeField(null=True)
    end_time = fields.DatetimeField(null=True)
    turn_count = fields.IntField(default=0)
    importance = fields.FloatField(default=0.5, description="抽取时 LLM 判定，用于遗忘/降权")
    access_count = fields.IntField(default=0)
    last_access_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "memory_episode"
        indexes = (
            ("user_id", "chat_group_id"),
            ("user_id", "updated_at"),
        )
