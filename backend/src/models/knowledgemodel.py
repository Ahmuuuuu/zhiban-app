from tortoise import Model, fields


class KnowledgeVector(Model):
    """知识库向量数据 — 关联用户，支持公开/私有"""
    doc_id = fields.CharField(max_length=64, pk=True, description="文档内容哈希 ID")
    title = fields.CharField(max_length=255, description="标题")
    content = fields.TextField(description="文本块内容")
    embedding = fields.TextField(description="向量嵌入，JSON 数组字符串")
    user_id = fields.IntField(null=True, description="上传用户 ID，null=系统公开")
    visibility = fields.CharField(max_length=10, default="private", description="public=全员可见, private=仅上传者")
    created_at = fields.DatetimeField(auto_now_add=True, null=True)

    class Meta:
        table = "knowledge_vectors"
