"""资源生成任务 — 持久化任务跟踪"""

from tortoise import Model, fields


class GenerationTask(Model):
    """资源生成任务"""
    id = fields.IntField(pk=True)
    task_id = fields.CharField(max_length=36, unique=True, description="UUID")
    user = fields.ForeignKeyField("models.User", related_name="generation_tasks", on_delete=fields.CASCADE)
    topic = fields.CharField(max_length=255, default="", description="学习主题")
    resource_types = fields.CharField(max_length=255, default="[]", description="资源类型 JSON 数组")
    chat_group_id = fields.IntField(null=True, description="关联的对话组ID")
    status = fields.CharField(max_length=16, default="pending", description="pending/running/success/failed")
    progress = fields.IntField(default=0, description="进度 0-100")
    progress_msg = fields.CharField(max_length=255, default="", description="进度描述")
    result = fields.TextField(null=True, description="生成结果 JSON: [{resource_id, file_type, topic, download_url}]")
    error = fields.TextField(null=True, description="错误信息")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "generation_tasks"
