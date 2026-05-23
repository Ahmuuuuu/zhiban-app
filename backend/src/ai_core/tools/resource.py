"""学习资源生成工具"""

from langchain_core.tools import tool
from backend.src.service.resource_service import ResourceService


@tool
async def generate_learning_resource(topic: str, user_id: str, resource_types: str = "document"):
    """生成学习资源。当用户说"帮我生成学习资料""做个PPT""出几道练习题""帮我整理成文档"时调用此工具。
    参数：topic学习主题，user_id用户数字ID，resource_types资源类型(逗号分隔，可选: document/ppt/mindmap/exercise/case/reading，默认document)"""
    uid = int(user_id.strip())
    types = [t.strip() for t in resource_types.split(",") if t.strip()]
    if not types:
        types = ["document"]
    results = await ResourceService.generate_and_save(topic, uid, types)
    if not results:
        return "生成失败，请稍后重试。"
    lines = [f"- {r['resource_type']}: {len(r['content'])}字" for r in results]
    return f"已为您生成 {len(results)} 份学习资料：\n" + "\n".join(lines)
