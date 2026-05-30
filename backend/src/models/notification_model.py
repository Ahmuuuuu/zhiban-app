"""站内消息推送 — 双表：通知 + 用户已读状态"""
from tortoise import Model, fields


class Notification(Model):
    """通知表 — target_user_id=NULL 表示全员广播"""
    id = fields.IntField(pk=True)
    type = fields.CharField(max_length=32, default="system", description="resource/reminder/system/weekly_report")
    title = fields.CharField(max_length=128)
    content = fields.TextField()
    target_url = fields.CharField(max_length=256, null=True, description="点击跳转，可空")
    target_user_id = fields.IntField(null=True, description="NULL=全员广播，否则定向推送")
    is_active = fields.BooleanField(default=True, description="软删除标记")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "notifications"


class UserNotification(Model):
    """用户已读状态表 — 记录谁读了哪条通知"""
    id = fields.IntField(pk=True)
    user_id = fields.IntField(description="用户ID")
    notification = fields.ForeignKeyField("models.Notification", related_name="user_reads", on_delete=fields.CASCADE)
    is_read = fields.BooleanField(default=False)
    read_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_notifications"
        unique_together = (("user_id", "notification_id"),)
