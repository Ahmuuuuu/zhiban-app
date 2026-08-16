from tortoise import Model, fields


class MemorySummary(Model):
    """工作记忆滚动摘要 + 抽取水位线（每个 user+group+agent 一条）"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="memory_summaries", on_delete=fields.CASCADE
    )
    chat_group_id = fields.IntField(null=True)
    agent_id = fields.IntField(null=True)
    summary = fields.TextField(default="", description="折叠后的工作记忆滚动摘要")
    last_processed_id = fields.IntField(null=True, description="已抽取的 chat_history 最大 id（水位线）")
    buffer_start_id = fields.IntField(null=True, description="尚未折入工作摘要的最小 chat_history id")
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "memory_summary"
        unique_together = (("user_id", "chat_group_id", "agent_id"),)
