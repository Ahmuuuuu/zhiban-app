from tortoise import Model, fields


class User_picture(Model):
    id = fields.IntField(pk=True, description="人物画像ID")

    # ── 弹窗标签获取 ──
    cognition = fields.CharField(max_length=50, null=True, description="认知风格：视觉型/听觉型/读写型/实践型")
    learning_goal = fields.CharField(max_length=50, null=True, description="学习目标：考试/竞赛/考证/兴趣/求职")
    personality_tags = fields.TextField(null=True, description="性格标签，JSON 数组字符串")

    # ── AI 对话中逐步构建的动态画像 (JSON) ──
    traits = fields.TextField(null=True, description="AI动态画像数据，JSON 格式")

    # ── AI 定期生成的画像自然语言总结 ──
    profile_summary = fields.TextField(null=True, description="画像自然语言总结（AI 生成）")

    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "user_picture"
