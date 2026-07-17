"""思维导图缩进文本 → JSON 树转换"""

import re


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
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:text|txt|markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    lines = []
    for raw in cleaned.split("\n"):
        if not raw.strip():
            continue
        leading_spaces = len(raw) - len(raw.lstrip(" "))
        body = raw.strip()
        body = re.sub(r"^(?:[-*+]\s+|\d+[.)、]\s+|#{1,6}\s+)", "", body).strip()
        if not body:
            continue
        lines.append(" " * leading_spaces + body)
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
            if not stack:
                # 模型偶尔会把多个一级节点顶格输出。此时把它们挂到首行根节点下，
                # 避免解析失败或前端只能看到残缺结构。
                stack = [(0, root)]
            stack[-1][1]["children"].append(node)
            stack.append((depth, node))

    return root or {"topic": "", "children": []}
