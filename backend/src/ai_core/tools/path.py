"""学习路径管理工具 - Agent 可据此增删改查路径节点"""

from langchain_core.tools import tool


@tool
async def list_learning_paths(user_id: str):
    """列出所有可加入的学习路径。调用时机：用户想了解有哪些学习路径、想选课、想加入某个学科的学习时"""
    from backend.src.service.path.service import PathService

    paths = await PathService.list_paths(int(user_id))
    if not paths:
        return "暂无可用学习路径。可以帮你生成一条新的。"
    lines = ["可用的学习路径："]
    for path in paths:
        lines.append(
            f"- [ID:{path['path_id']}] {path['subject']}（{path['difficulty']}，{path['node_count']} 节点）"
        )
    return "\n".join(lines)


@tool
async def get_learning_path_detail(path_id: int, user_id: str):
    """查看某条学习路径的完整节点详情（含 topic、resource_types、quiz_config 等）。调用时机：用户想了解路径具体内容、查看节点安排时"""
    from backend.src.service.path.service import PathService

    path = await PathService.get_path(path_id, int(user_id))
    if not path:
        return "路径不存在。"
    nodes = path["nodes"]
    lines = [f"路径「{path['subject']}」（难度：{path['difficulty']}，共 {path['node_count']} 节点）："]
    for node in nodes:
        resource_types = ", ".join(node.get("resource_types", []))
        quiz = node.get("quiz_config", {})
        quiz_str = f"测验 {quiz.get('count', 3)}题/通过线{quiz.get('threshold', 0.7)}" if quiz else "无测验"
        lines.append(
            f"  {node['order_index']}. {node['topic']} - 资源：{resource_types or '文档'} - {quiz_str}"
        )
    return "\n".join(lines)


@tool
async def enroll_learning_path(path_id: int, user_id: str):
    """帮用户加入一条学习路径，自动解锁第一个节点并生成学习资源。调用时机：用户明确要加入某个路径、开始学习时"""
    from backend.src.service.path.service import PathService

    try:
        result = await PathService.enroll_path(path_id, int(user_id))
        if "message" in result and "已加入" in result["message"]:
            return result["message"]
        nodes = result.get("progress", [])
        first = next((node for node in nodes if node["status"] == "unlocked"), None)
        return f"已加入路径！首节点「{first['topic'] if first else '未知'}」已解锁，学习资源已生成。"
    except ValueError as exc:
        return str(exc)


@tool
async def regenerate_learning_path(path_id: int, user_id: str):
    """基于最新用户画像重建学习路径（已完成的节点保留）。调用时机：用户画像变化后、用户觉得路径不合适需要重新规划时"""
    from backend.src.service.path.service import PathService

    try:
        result = await PathService.regenerate_path(path_id, int(user_id))
        if "error" in result:
            return f"路径重建失败：{result['error']}"
        return f"路径已重建（新 ID：{result['path_id']}），共 {len(result['nodes'])} 个节点。"
    except ValueError as exc:
        return str(exc)


@tool
async def update_path_node(
    path_id: int,
    node_id: int,
    user_id: str,
    topic: str = "",
    knowledge_tags: str = "",
    resource_types: str = "",
    quiz_count: int = 0,
    quiz_threshold: float = 0.0,
):
    """更新学习路径中某个节点的内容。参数：topic 新主题、knowledge_tags 知识点标签(逗号分隔)、
    resource_types 资源类型(逗号分隔，可选 document/ppt/mindmap/exercise/case/reading)、
    quiz_count 测验题数、quiz_threshold 通过分数线(0-1)。
    调用时机：用户想调整某个节点的学习内容、难度、资源类型时"""
    from backend.src.service.path.service import PathService

    fields = {}
    if topic:
        fields["topic"] = topic
    if knowledge_tags:
        fields["knowledge_tags"] = [tag.strip() for tag in knowledge_tags.split(",") if tag.strip()]
    if resource_types:
        fields["resource_types"] = [item.strip() for item in resource_types.split(",") if item.strip()]
    quiz_config = {}
    if quiz_count > 0:
        quiz_config["count"] = quiz_count
    if quiz_threshold > 0:
        quiz_config["threshold"] = quiz_threshold
    if quiz_config:
        if "count" not in quiz_config:
            quiz_config["count"] = 3
        if "threshold" not in quiz_config:
            quiz_config["threshold"] = 0.7
        fields["quiz_config"] = quiz_config
    if not fields:
        return "未提供任何需要更新的字段。"
    try:
        result = await PathService.update_node(path_id, node_id, int(user_id), **fields)
        return f"节点已更新：{result['topic']}（资源：{', '.join(result['resource_types'])}，测验配置：{result['quiz_config']}）"
    except ValueError as exc:
        return str(exc)


@tool
async def add_path_node(
    path_id: int,
    topic: str,
    user_id: str,
    knowledge_tags: str = "",
    resource_types: str = "document",
):
    """在学习路径末尾添加一个新节点。参数：path_id 路径ID、topic 节点主题、
    knowledge_tags 知识点标签(逗号分隔)、resource_types 资源类型(逗号分隔)。
    调用时机：用户觉得路径不够完整、需要补充新的学习内容时"""
    from backend.src.service.path.service import PathService

    fields = {}
    if knowledge_tags:
        fields["knowledge_tags"] = [tag.strip() for tag in knowledge_tags.split(",") if tag.strip()]
    if resource_types:
        fields["resource_types"] = [item.strip() for item in resource_types.split(",") if item.strip()]
    try:
        result = await PathService.add_node(path_id, topic, int(user_id), **fields)
        return f"新节点「{result['topic']}」（ID：{result['node_id']}）已添加至路径末尾（第 {result['order_index']} 位），学习资源已自动生成。"
    except ValueError as exc:
        return str(exc)


@tool
async def delete_path_node(path_id: int, node_id: int, user_id: str):
    """删除学习路径中的某个节点。调用时机：用户觉得某个节点不需要、想跳过时。
    注意：删除不可逆，执行前应确认用户意图。"""
    from backend.src.service.path.service import PathService

    try:
        ok = await PathService.delete_node(path_id, node_id)
        return "节点已删除。" if ok else "节点不存在。"
    except ValueError as exc:
        return str(exc)
