"""用户自建智能体模型"""

from tortoise import Model, fields


class UserAgent(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="agents", on_delete=fields.CASCADE)

    name = fields.CharField(max_length=64, description="智能体名称")
    avatar = fields.CharField(max_length=512, default="", description="头像URL")
    persona = fields.TextField(default="", description="角色设定(system prompt)")
    tools = fields.TextField(default="[]", description="已选工具名称列表(JSON)")
    memory = fields.TextField(default="[]", description="对话记忆摘要(JSON)")
    schedule = fields.TextField(null=True, description="定时任务配置(JSON)")

    is_public = fields.BooleanField(default=False, description="是否公开到市场")
    enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_agents"
