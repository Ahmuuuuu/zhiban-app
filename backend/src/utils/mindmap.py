"""思维导图缩进文本 → JSON 树转换"""


def parse_mindmap_text(text: str) -> dict:
    """将缩进文本树转为 JSON 树结构。

    输入示例:
      机器学习
        监督学习
          线性回归
          决策树

    输出:
      {"topic": "机器学习", "children": [{"topic": "监督学习", "children": [...]}]}
    """
    lines = [line for line in text.strip().split("\n") if line.strip()]
    if not lines:
        return {"topic": "", "children": []}

    root = None
    stack: list[tuple[int, dict]] = []

    for line in lines:
        stripped = line.strip()
        leading_spaces = len(line) - len(line.lstrip(" "))
        depth = leading_spaces // 2

        node = {"topic": stripped, "children": []}

        if root is None:
            root = node
            stack = [(depth, node)]
        else:
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack[-1][1]["children"].append(node)
            stack.append((depth, node))

    return root or {"topic": "", "children": []}
