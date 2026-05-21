"""AI 图片生成工具 (讯飞 HiDream)"""

from langchain_core.tools import tool


ENHANCE_PROMPT = """你是一个专业的 AI 绘画提示词工程师。将用户的描述精炼成一段高质量的图片生成提示词。

规则：
1. 输出仅包含提示词本身，不要加任何解释、引号或前缀
2. 补充视觉细节：光线、构图、风格、色彩、材质
3. 如果是具象场景，补充"照片级真实感，高细节"
4. 如果是绘画风格，指定具体风格如"吉卜力风格/水墨画/油画/赛博朋克"
5. 输出 40-120 字的中文提示词
6. 不要包含"生成""制作""帮我画"等指令性文字，只输出画面描述

用户描述：{user_prompt}

提示词："""


@tool
async def generate_image(prompt: str, user_id: str, aspect_ratio: str = "1:1", img_count: int = 1):
    """AI 图片生成（讯飞 HiDream）。当用户说"画一个""帮我生成图片""画张图"等时调用。
    参数：prompt图片描述，user_id用户数字ID，aspect_ratio宽高比(1:1/16:9/9:16等)，img_count生成数量(1-4)"""
    from backend.src.service.image_service import ImageService
    from backend.src.ai_core.llm_config import llm

    try:
        # 用 LLM 精炼 prompt，提升出图质量
        enhance_input = ENHANCE_PROMPT.format(user_prompt=prompt)
        refined = await llm.ainvoke(enhance_input)
        refined_prompt = refined.content.strip() or prompt

        records = await ImageService.generate(refined_prompt, user_id, aspect_ratio, img_count)
        lines = [f"![{r['filename']}]({r['url']})" for r in records]
        return f"已为您生成 {len(records)} 张图片：\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"图片生成异常: {e}"
