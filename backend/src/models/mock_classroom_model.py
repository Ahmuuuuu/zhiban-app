"""Mock classroom session, media frame, and report models."""

from tortoise import Model, fields


class MockClassroomSession(Model):
    """A single mock teaching session."""

    id = fields.IntField(pk=True)
    session_key = fields.CharField(max_length=64, unique=True, description="Public session id")
    topic = fields.CharField(max_length=128, description="Teaching topic")
    reference_text = fields.TextField(null=True, description="Knowledge-base reference text used for scoring")
    planned_minutes = fields.IntField(default=5, description="Planned teaching duration")
    state = fields.CharField(max_length=16, default="running", description="running/finished/cancelled")
    report_status = fields.CharField(max_length=16, default="pending", description="pending/generating/ready/failed")
    audio_url = fields.CharField(max_length=512, null=True, description="Uploaded lecture audio URL")
    transcript = fields.TextField(null=True, description="ASR transcript")
    elapsed_seconds = fields.IntField(default=0)
    frame_count = fields.IntField(default=0)
    audio_duration_seconds = fields.IntField(default=0)
    overall_score = fields.IntField(default=0)
    knowledge_score = fields.IntField(default=0)
    fluency_score = fields.IntField(default=0)
    presentation_score = fields.IntField(default=0)
    started_at = fields.DatetimeField()
    ended_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    user = fields.ForeignKeyField("models.User", related_name="mock_classroom_sessions", on_delete=fields.CASCADE)

    class Meta:
        table = "mock_classroom_sessions"


class MockClassroomFrameLog(Model):
    """Camera-frame analysis log for mock classroom."""

    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.MockClassroomSession", related_name="frame_logs", on_delete=fields.CASCADE)
    captured_at = fields.DatetimeField(auto_now_add=True)
    client_elapsed_seconds = fields.IntField(default=0)
    camera_state = fields.CharField(max_length=32, default="unknown")
    person_count = fields.IntField(default=0)
    face_visible = fields.BooleanField(default=False)
    away = fields.BooleanField(default=False)
    multiple_people = fields.BooleanField(default=False)
    frame_path = fields.CharField(max_length=512, null=True)
    raw_result = fields.TextField(null=True)

    class Meta:
        table = "mock_classroom_frame_logs"


class MockClassroomReport(Model):
    """Final scoring report for a mock teaching session."""

    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.MockClassroomSession", related_name="reports", on_delete=fields.CASCADE)
    overall_score = fields.IntField(default=0)
    knowledge_score = fields.IntField(default=0)
    fluency_score = fields.IntField(default=0)
    presentation_score = fields.IntField(default=0)
    strengths = fields.TextField(default="[]")
    gaps = fields.TextField(default="[]")
    suggestions = fields.TextField(default="[]")
    rubric_json = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "mock_classroom_reports"
