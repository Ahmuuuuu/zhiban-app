from tortoise import Model, fields


class GeneratedImage(Model):
    id = fields.IntField(pk=True, description="图片ID")
    prompt = fields.TextField(description="生成时的提示词")
    filename = fields.CharField(max_length=255, description="文件名（不含路径）")
    aspect_ratio = fields.CharField(max_length=16, default="1:1", description="宽高比")
    visibility = fields.CharField(max_length=10, default="private", description="public=全员可见, private=仅创建者可见")
    created_at = fields.DatetimeField(auto_now_add=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="generated_images",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "generated_images"
