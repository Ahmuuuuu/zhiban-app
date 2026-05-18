from tortoise import Model, fields

class ChatHistory(Model):
    id = fields.IntField(pk = True, description = "聊天记录ID")
    chat_group_id = fields.IntField(null = True, description = "聊天所属组")
    req = fields.TextField(null = True, description = "用户问题")
    res = fields.TextField(null = True, description = "AI回答")
    created_at = fields.DatetimeField(auto_now_add = True, null =True)
    updated_at = fields.DatetimeField(auto_now = True, null = True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name = "chat_history",
        on_delete = fields.CASCADE
    )

    class Meta:
        table = "chat_history"