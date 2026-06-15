from pydantic import BaseModel, Field


class GenerateResourceRequest(BaseModel):
    topic: str = Field(default="", description="瀛︿範涓婚锛屼负绌哄垯浠?chat_group_id 鎻愬彇")
    resource_types: list[str] = Field(
        default=[],
        description="璧勬簮绫诲瀷鍒楄〃锛屼负绌哄垯鐢?LeaderAgent 鑷姩鍐冲畾"
    )
    chat_group_id: int = Field(default=0, description="瀵硅瘽鍒嗙粍ID锛屼紶姝ゅ€煎彲鑷姩鎻愬彇涓婚")
    bind_chat_history: bool = Field(default=False, description="Bind generated resources to chat history when chat_group_id is missing")
    answers: dict | None = Field(default=None, description="瑙嗛妯″紡锛氱敤鎴疯拷闂綔绛?{focus, depth}锛屾敞鍏?prompt 鎸夐渶鐢熸垚")
    force_regenerate: bool = Field(default=False, description="寮哄埗閲嶆柊鐢熸垚锛屾棤瑙嗗凡缂撳瓨鐨勫悓涓婚璧勬簮")

