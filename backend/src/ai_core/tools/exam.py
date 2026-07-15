"""题库生成工具"""

from langchain_core.tools import tool
from backend.src.service.exam.service import ExamService


@tool
async def generate_exam_questions(topic: str, user_id: str, count: str = "5", difficulty: str = "medium", question_types: str = "single_choice", chat_group_id: str = "0"):
    """根据学习主题自动生成练习题。当用户说"出几道题""帮我练习""测验一下""考试模拟""做几道题"时调用此工具。
    参数：topic学习主题，user_id用户数字ID，count题目数量(默认5)，difficulty难度(easy/medium/hard，默认medium)，question_types题型(逗号分隔，可选: single_choice/multi_choice/true_false/fill_blank/short_answer，默认single_choice)，chat_group_id聊天组ID"""

    uid = int(user_id.strip())
    gid = int(chat_group_id) if str(chat_group_id).isdigit() else 0
    types = [t.strip() for t in question_types.split(",") if t.strip()] if question_types else ["single_choice"]
    cnt = int(count) if str(count).isdigit() else 5

    result = await ExamService.generate_and_save(
        topic,
        uid,
        types,
        cnt,
        difficulty,
        chat_group_id=gid,
        include_request_in_history=False,
    )
    questions = result.get("questions", []) if isinstance(result, dict) else result
    if not questions:
        return "题目生成失败，请稍后重试。"

    lines = [f"已为您生成 {len(questions)} 道练习题："]
    for i, q in enumerate(questions, 1):
        lines.append(f"\n{i}. [{q['question_type']}] {q['content'][:80]}...")
    return "\n".join(lines)
