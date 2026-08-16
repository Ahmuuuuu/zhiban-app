"""自习室相关模型 — 会话、检测帧、提醒记录"""

from tortoise import Model, fields


class StudyRoomSession(Model):
    """一次自习室会话。"""

    id = fields.IntField(pk=True)
    session_key = fields.CharField(max_length=64, unique=True, description="对外暴露的会话 ID")
    goal = fields.CharField(max_length=128, description="本次自习目标")
    planned_minutes = fields.IntField(default=45, description="计划自习分钟数")
    state = fields.CharField(max_length=16, default="running", description="running/paused/finished/cancelled")
    vlog_enabled = fields.BooleanField(default=False, description="是否开启学习 Vlog")
    timelapse_interval = fields.IntField(default=5, description="延时摄影抽帧间隔秒数")
    timelapse_target = fields.IntField(null=True, description="期望成片秒数")
    timelapse_status = fields.CharField(max_length=16, default="disabled", description="disabled/capturing/generating/ready/failed")
    timelapse_url = fields.CharField(max_length=512, null=True, description="延时摄影成片 URL")
    frame_count = fields.IntField(default=0, description="保存的 Vlog 抽帧数量")

    elapsed_seconds = fields.IntField(default=0)
    focus_seconds = fields.IntField(default=0)
    away_seconds = fields.IntField(default=0)
    focus_rate = fields.IntField(default=100)
    away_count = fields.IntField(default=0)
    alert_count = fields.IntField(default=0)
    phone_alert_count = fields.IntField(default=0)
    multiple_people_alert_count = fields.IntField(default=0)

    started_at = fields.DatetimeField()
    ended_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    user = fields.ForeignKeyField("models.User", related_name="study_room_sessions", on_delete=fields.CASCADE)

    class Meta:
        table = "study_room_sessions"


class StudyRoomFrameLog(Model):
    """每次上传帧的检测结果。"""

    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.StudyRoomSession", related_name="frame_logs", on_delete=fields.CASCADE)
    captured_at = fields.DatetimeField(auto_now_add=True)
    client_elapsed_seconds = fields.IntField(default=0)
    state = fields.CharField(max_length=32, default="unknown")
    confidence = fields.FloatField(default=0)
    person_count = fields.IntField(default=0)
    phone_detected = fields.BooleanField(default=False)
    away = fields.BooleanField(default=False)
    multiple_people = fields.BooleanField(default=False)
    saved_for_vlog = fields.BooleanField(default=False)
    frame_path = fields.CharField(max_length=512, null=True)
    raw_result = fields.TextField(null=True)

    class Meta:
        table = "study_room_frame_logs"


class StudyRoomAlert(Model):
    """自习室提醒记录。"""

    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.StudyRoomSession", related_name="alerts", on_delete=fields.CASCADE)
    alert_type = fields.CharField(max_length=32)
    level = fields.CharField(max_length=16, default="warning")
    message = fields.CharField(max_length=255)
    triggered_at = fields.DatetimeField(auto_now_add=True)
    client_elapsed_seconds = fields.IntField(default=0)

    class Meta:
        table = "study_room_alerts"
