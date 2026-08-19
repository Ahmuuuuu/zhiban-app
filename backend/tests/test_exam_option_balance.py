from backend.src.service.exam.service import _prepare_questions_for_storage


def test_choice_answers_are_rebalanced_without_changing_correct_content():
    questions = [
        {
            "question_type": "single_choice",
            "content": f"第 {index + 1} 题",
            "options": ["A. 正确内容", "B. 干扰项一", "C. 干扰项二", "D. 干扰项三"],
            "answer": "A",
        }
        for index in range(5)
    ]

    prepared = _prepare_questions_for_storage(questions)

    assert [item["answer"] for item in prepared] == ["A", "B", "C", "D", "A"]
    for item in prepared:
        correct = next(option for option in item["options"] if option.startswith(f"{item['answer']}."))
        assert correct.endswith("正确内容")


def test_multiple_choice_answer_is_mapped_with_options():
    question = {
        "question_type": "multi_choice",
        "options": ["A. 正确一", "B. 干扰项", "C. 正确二", "D. 干扰项"],
        "answer": ["A", "C"],
    }

    leading_choice = {
        "question_type": "single_choice",
        "options": ["A. 正确", "B. 干扰一", "C. 干扰二", "D. 干扰三"],
        "answer": "A",
    }
    prepared = _prepare_questions_for_storage([leading_choice, question])[1]

    assert prepared["answer"] == ["B", "D"]
    selected = [option for option in prepared["options"] if option[0] in prepared["answer"]]
    assert {option[3:] for option in selected} == {"正确一", "正确二"}
