from tortoise import Model, fields


class ResourceAnnotation(Model):
    id = fields.IntField(pk=True, description="笔记ID")
    selected_text = fields.TextField(description="用户选中的原文")
    note_text = fields.TextField(description="用户的笔记内容")
    position = fields.JSONField(null=True, description="定位信息(JSON)")

    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="annotations",
        on_delete=fields.CASCADE,
    )
    resource = fields.ForeignKeyField(
        "models.GeneratedResource",
        related_name="annotations",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "resource_annotations"
