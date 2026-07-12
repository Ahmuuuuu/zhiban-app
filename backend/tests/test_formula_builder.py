from backend.src.utils.formula_builder import (
    build_formula_sheet,
    determinant_matrix,
    matrix,
    validate_formula_sheet,
)


def test_matrix_builder_balances_environment():
    block = matrix("A", [["1", "2"], ["3", "4"]])

    assert r"\begin{bmatrix}" in block
    assert r"\end{bmatrix}" in block
    assert block.count("$$") == 2
    assert validate_formula_sheet(block) == []


def test_determinant_builder_uses_vmatrix():
    block = determinant_matrix("A", [["a", "b"], ["c", "d"]])

    assert r"\det(A)" in block
    assert r"\begin{vmatrix}" in block
    assert r"\end{vmatrix}" in block
    assert validate_formula_sheet(block) == []


def test_linear_algebra_topic_has_core_formulas():
    sheet = build_formula_sheet("矩阵行列式与特征值分析")

    assert "2x2 determinant" in sheet
    assert "Eigen equation" in sheet
    assert r"\det(A)" in sheet
    assert validate_formula_sheet(sheet) == []


def test_probability_topic_has_probability_formulas_only():
    sheet = build_formula_sheet("概率统计中的条件概率和方差")

    assert "Conditional probability" in sheet
    assert "Variance" in sheet
    assert "2x2 determinant" not in sheet
    assert validate_formula_sheet(sheet) == []


def test_unknown_topic_returns_empty_sheet():
    assert build_formula_sheet("古诗词意象赏析") == ""
