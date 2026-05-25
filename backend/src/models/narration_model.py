"""语音旁白记录表"""

from tortoise import Model, fields


class Narration(Model):
    id = fields.IntField(pk=True)
    resource = fields.ForeignKeyField(
        "models.GeneratedResource",
        related_name="narrations",
        on_delete=fields.CASCADE,
    )
    voice = fields.CharField(max_length=64, description="EdgeTTS 语音名称")
    slides_json = fields.JSONField(description="逐页旁白 [{index, title, text, audio_url, duration_ms}]")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "narrations"
