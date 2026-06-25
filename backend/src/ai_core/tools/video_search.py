"""外部视频搜索工具 (B站) — 搜索后自动保存为资源供前端嵌入播放"""
from langchain_core.tools import tool


@tool
async def search_online_video(topic: str, user_id: str, max_results: int = 3, chat_group_id: str = "0"):
    """搜索在线教学视频（B站）。当用户说"找视频""搜视频教程""找个教学视频""搜索视频资料"时调用。
    参数：topic搜索关键词，user_id用户数字ID，max_results返回视频数量(1-5，默认3)，chat_group_id聊天组ID"""
    from backend.src.service.video_service import ExternalVideoService

    gid = int(chat_group_id) if str(chat_group_id).isdigit() else 0
    try:
        saved = await ExternalVideoService.search_and_save(
            topic, int(user_id), max_results, chat_group_id=gid,
        )
        if not saved:
            return f"未找到「{topic}」相关的教学视频，可以试试换个关键词。"

        lines = [f"📺 已找到 {len(saved)} 个相关教学视频："]
        for i, v in enumerate(saved, 1):
            title = v.get("title", "")
            source = v.get("source", "")
            author = v.get("author", "")
            duration = v.get("duration_text", "")
            views = v.get("view_count_text", "")

            meta_parts = []
            if source:
                meta_parts.append(f"来源：{source}")
            if author:
                meta_parts.append(f"UP主：{author}")
            if duration:
                meta_parts.append(f"时长：{duration}")
            if views:
                meta_parts.append(f"播放：{views}")

            meta_str = "  ".join(meta_parts)
            lines.append(f"\n{i}. {title}")
            if meta_str:
                lines.append(f"   {meta_str}")
            lines.append(f"   资源ID: {v['resource_id']}（点击或在聊天中发送「查看资源 {v['resource_id']}」即可播放）")

        lines.append(f"\n💡 你也可以说「帮我生成 {topic} 的学习资料」来获取配套的文档和PPT。")
        return "\n".join(lines)

    except Exception as e:
        return f"视频搜索异常: {e}"
