from tortoise import Model, fields


class Video(Model):
    id = fields.IntField(pk=True, description="视频ID")
    topic = fields.CharField(max_length=255, description="学习主题")
    status = fields.CharField(max_length=16, default="generating", description="generating / ready / failed")
    file_url = fields.CharField(max_length=512, null=True, description="HTML 文件路径")
    chapters_json = fields.TextField(null=True, description="章节 JSON 数组（逐章更新）")
    total_duration_ms = fields.IntField(default=0, description="总时长（毫秒）")
    error_message = fields.TextField(null=True, description="失败原因")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="presentations",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "presentations"
