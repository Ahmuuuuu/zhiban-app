"""用户画像六维雷达模型 — 每用户一条记录，定时/手动刷新"""

from tortoise import Model, fields


class PortraitRadar(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="radar", unique=True)

    memory = fields.IntField(default=0, description="记忆 — easy 难度正确率(0-100)")
    understanding = fields.IntField(default=0, description="理解 — medium 难度正确率(0-100)")
    application = fields.IntField(default=0, description="应用 — hard 难度正确率(0-100)")
    analysis = fields.IntField(default=0, description="分析 — multi_choice 题型正确率(0-100)")
    breadth = fields.IntField(default=0, description="广度 — 已覆盖知识标签种类(归一化,0-100)")
    persistence = fields.IntField(default=0, description="坚持 — 近30天活跃天数占比(0-100)")

    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "portrait_radar"
