from tortoise import Model, fields


class AgentSkill(Model):
    """
    用户自定义 skill，分两类:
    - generation: 资源生成风格定制（原有功能），绑定 resource_type
    - action: 可执行的动作工具（新增），通过 HTTP 调用外部 API 等
    """
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=64, description="技能名称")
    skill_type = fields.CharField(max_length=16, default="generation", description="generation 或 action")
    resource_type = fields.CharField(max_length=64, default="", description="generation: 资源类型; action: action:{name}")
    system_prompt = fields.TextField(null=True, description="generation skill 的定制 prompt")
    action_type = fields.CharField(max_length=16, null=True, description="action skill: http")
    action_config = fields.TextField(null=True, description="action skill: JSON 配置 (url/method/params)")
    tool_description = fields.TextField(null=True, description="action skill: 工具描述，告诉 LLM 何时及如何调用")
    enabled = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="agent_skills",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "agent_skills"
        unique_together = [("user_id", "resource_type")]
