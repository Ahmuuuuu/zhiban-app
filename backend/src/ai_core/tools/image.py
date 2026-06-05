"""AI 图片生成工具 (讯飞 HiDream)"""

from langchain_core.tools import tool


@tool
async def generate_image(prompt: str, user_id: str, aspect_ratio: str = "1:1", img_count: int = 1, chat_group_id: str = "0"):
    """AI 图片生成（讯飞 HiDream）。当用户说"画一个""帮我生成图片""画张图"等时调用。
    参数：prompt图片描述（Agent 已精炼过的高质量提示词），user_id用户数字ID，aspect_ratio宽高比(1:1/16:9/9:16等)，img_count生成数量(1-4)，chat_group_id聊天组ID"""
    from backend.src.service.image_service import ImageService

    gid = int(chat_group_id) if str(chat_group_id).isdigit() else 0

    try:
        records = await ImageService.generate(prompt, user_id, aspect_ratio, img_count, chat_group_id=gid)
        lines = [f"![{r['filename']}]({r['url']})" for r in records]
        return f"已为您生成 {len(records)} 张图片：\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"图片生成异常: {e}"
