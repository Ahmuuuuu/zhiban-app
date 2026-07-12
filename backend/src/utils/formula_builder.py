"""Deterministic formula templates for learning-resource generation.

The LLM should not have to hand-write common LaTeX blocks.  This module builds
small, valid formula sheets from topic keywords, then the prompt can ask the LLM
to reuse those blocks verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class FormulaSnippet:
    title: str
    latex: str
    keywords: tuple[str, ...]
    note: str = ""


def display(latex: str) -> str:
    """Wrap a LaTeX expression in a reviewer-friendly display block."""
    return "$$\n" + latex.strip() + "\n$$"


def matrix(
    name: str,
    entries: list[list[str]],
    *,
    env: str = "bmatrix",
) -> str:
    """Build a named matrix block with balanced begin/end tags."""
    rows = [r" & ".join(str(cell) for cell in row) for row in entries]
    body = r" \\ ".join(rows)
    return display(
        rf"{name}=\begin{{{env}}}"
        "\n"
        rf"{body}"
        "\n"
        rf"\end{{{env}}}"
    )


def determinant_matrix(
    name: str,
    entries: list[list[str]],
) -> str:
    rows = [r" & ".join(str(cell) for cell in row) for row in entries]
    body = r" \\ ".join(rows)
    return display(
        rf"\det({name})=\begin{{vmatrix}}"
        "\n"
        rf"{body}"
        "\n"
        rf"\end{{vmatrix}}"
    )


def _snippet(title: str, latex: str, keywords: Iterable[str], note: str = "") -> FormulaSnippet:
    return FormulaSnippet(title=title, latex=display(latex), keywords=tuple(keywords), note=note)


def _matrix_snippet(title: str, latex_block: str, keywords: Iterable[str], note: str = "") -> FormulaSnippet:
    return FormulaSnippet(title=title, latex=latex_block, keywords=tuple(keywords), note=note)


FORMULAS: tuple[FormulaSnippet, ...] = (
    # Linear algebra
    _matrix_snippet(
        "2x2 matrix template",
        matrix("A", [["a", "b"], ["c", "d"]]),
        ("matrix", "linear algebra", "linear", "矩阵", "线性代数"),
    ),
    _snippet(
        "Matrix multiplication component",
        r"(AB)_{ij}=\sum_{k=1}^{n}a_{ik}b_{kj}",
        ("matrix multiplication", "matrix", "linear algebra", "矩阵乘法", "矩阵", "线性代数"),
    ),
    _snippet(
        "2x2 determinant",
        r"\det(A)=\begin{vmatrix}a & b \\ c & d\end{vmatrix}=ad-bc",
        ("determinant", "matrix", "linear algebra", "行列式", "矩阵", "线性代数"),
    ),
    _snippet(
        "3x3 determinant expansion",
        r"\det(A)=a_{11}(a_{22}a_{33}-a_{23}a_{32})-a_{12}(a_{21}a_{33}-a_{23}a_{31})+a_{13}(a_{21}a_{32}-a_{22}a_{31})",
        ("determinant", "cofactor", "matrix", "行列式", "余子式", "代数余子式"),
    ),
    _snippet(
        "2x2 inverse matrix",
        r"A^{-1}=\frac{1}{ad-bc}\begin{bmatrix}d & -b \\ -c & a\end{bmatrix},\quad ad-bc\ne 0",
        ("inverse", "matrix", "linear algebra", "逆矩阵", "矩阵", "线性代数"),
    ),
    _snippet(
        "Linear system",
        r"A\mathbf{x}=\mathbf{b}",
        ("linear system", "matrix", "linear algebra", "线性方程组", "矩阵", "线性代数"),
    ),
    _snippet(
        "Cramer's rule",
        r"x_i=\frac{\det(A_i)}{\det(A)},\quad \det(A)\ne 0",
        ("cramer", "determinant", "linear system", "克拉默", "行列式", "线性方程组"),
    ),
    _snippet(
        "Rank-nullity theorem",
        r"\operatorname{rank}(A)+\operatorname{nullity}(A)=n",
        ("rank", "nullity", "matrix", "秩", "零空间", "矩阵"),
    ),
    _snippet(
        "Characteristic polynomial",
        r"p_A(\lambda)=\det(\lambda I-A)",
        ("eigenvalue", "eigenvector", "characteristic", "matrix", "特征值", "特征向量", "特征多项式"),
    ),
    _snippet(
        "Eigen equation",
        r"A\mathbf{v}=\lambda\mathbf{v},\quad \mathbf{v}\ne \mathbf{0}",
        ("eigenvalue", "eigenvector", "matrix", "特征值", "特征向量"),
    ),
    _snippet(
        "Diagonalization",
        r"A=PDP^{-1}",
        ("diagonalization", "eigenvalue", "matrix", "对角化", "特征值", "矩阵"),
    ),
    _snippet(
        "Orthogonal projection",
        r"\operatorname{proj}_{\mathbf{u}}\mathbf{v}=\frac{\mathbf{v}\cdot\mathbf{u}}{\mathbf{u}\cdot\mathbf{u}}\mathbf{u}",
        ("projection", "vector", "orthogonal", "投影", "向量", "正交"),
    ),
    _snippet(
        "Least squares normal equation",
        r"A^{T}A\hat{\mathbf{x}}=A^{T}\mathbf{b}",
        ("least squares", "normal equation", "matrix", "最小二乘", "正规方程", "矩阵"),
    ),
    _snippet(
        "Gram-Schmidt step",
        r"\mathbf{u}_k=\mathbf{v}_k-\sum_{j=1}^{k-1}\frac{\mathbf{v}_k\cdot\mathbf{u}_j}{\mathbf{u}_j\cdot\mathbf{u}_j}\mathbf{u}_j",
        ("gram", "orthogonal", "vector", "施密特", "正交化", "向量"),
    ),
    # Calculus and analysis
    _snippet(
        "Derivative definition",
        r"f'(x)=\lim_{h\to 0}\frac{f(x+h)-f(x)}{h}",
        ("derivative", "calculus", "微分", "导数", "极限", "微积分"),
    ),
    _snippet(
        "Chain rule",
        r"\frac{d}{dx}f(g(x))=f'(g(x))g'(x)",
        ("chain rule", "derivative", "calculus", "链式法则", "导数", "微积分"),
    ),
    _snippet(
        "Integration by parts",
        r"\int u\,dv=uv-\int v\,du",
        ("integral", "calculus", "integration by parts", "积分", "分部积分", "微积分"),
    ),
    _snippet(
        "Taylor expansion",
        r"f(x)=\sum_{k=0}^{n}\frac{f^{(k)}(a)}{k!}(x-a)^k+R_n(x)",
        ("taylor", "series", "calculus", "泰勒", "级数", "微积分"),
    ),
    _snippet(
        "Gradient",
        r"\nabla f=\begin{bmatrix}\frac{\partial f}{\partial x_1} & \frac{\partial f}{\partial x_2} & \cdots & \frac{\partial f}{\partial x_n}\end{bmatrix}^{T}",
        ("gradient", "multivariable", "calculus", "梯度", "多元函数", "微积分"),
    ),
    _snippet(
        "Hessian matrix",
        r"H_f=\begin{bmatrix}\frac{\partial^2 f}{\partial x_1^2} & \cdots & \frac{\partial^2 f}{\partial x_1\partial x_n} \\ \vdots & \ddots & \vdots \\ \frac{\partial^2 f}{\partial x_n\partial x_1} & \cdots & \frac{\partial^2 f}{\partial x_n^2}\end{bmatrix}",
        ("hessian", "multivariable", "calculus", "海森矩阵", "二阶导", "多元函数"),
    ),
    _snippet(
        "Lagrange multiplier condition",
        r"\nabla f(\mathbf{x})=\lambda\nabla g(\mathbf{x})",
        ("lagrange", "optimization", "calculus", "拉格朗日", "优化", "约束极值"),
    ),
    _snippet(
        "Newton iteration",
        r"x_{k+1}=x_k-\frac{f(x_k)}{f'(x_k)}",
        ("newton", "numerical", "root", "牛顿法", "数值分析", "求根"),
    ),
    # Probability and statistics
    _snippet(
        "Conditional probability",
        r"P(A\mid B)=\frac{P(A\cap B)}{P(B)},\quad P(B)>0",
        ("probability", "conditional", "概率", "条件概率"),
    ),
    _snippet(
        "Bayes theorem",
        r"P(A\mid B)=\frac{P(B\mid A)P(A)}{P(B)}",
        ("bayes", "probability", "贝叶斯", "概率"),
    ),
    _snippet(
        "Expectation",
        r"E[X]=\sum_x xP(X=x)",
        ("expectation", "probability", "statistics", "期望", "概率", "统计"),
    ),
    _snippet(
        "Variance",
        r"\operatorname{Var}(X)=E[X^2]-\bigl(E[X]\bigr)^2",
        ("variance", "probability", "statistics", "方差", "概率", "统计"),
    ),
    _snippet(
        "Covariance",
        r"\operatorname{Cov}(X,Y)=E[XY]-E[X]E[Y]",
        ("covariance", "correlation", "statistics", "协方差", "相关", "统计"),
    ),
    _snippet(
        "Binomial distribution",
        r"P(X=k)=\binom{n}{k}p^k(1-p)^{n-k}",
        ("binomial", "probability", "statistics", "二项分布", "概率", "统计"),
    ),
    _snippet(
        "Normal distribution density",
        r"f(x)=\frac{1}{\sqrt{2\pi}\sigma}\exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right)",
        ("normal distribution", "gaussian", "statistics", "正态分布", "高斯", "统计"),
    ),
    _snippet(
        "Central limit theorem standardization",
        r"Z=\frac{\bar{X}-\mu}{\sigma/\sqrt{n}}",
        ("central limit", "statistics", "probability", "中心极限定理", "统计", "概率"),
    ),
    # Discrete math and graph theory
    _snippet(
        "Combination number",
        r"\binom{n}{k}=\frac{n!}{k!(n-k)!}",
        ("combination", "combinatorics", "discrete", "组合", "排列组合", "离散数学"),
    ),
    _snippet(
        "Permutation number",
        r"P(n,k)=\frac{n!}{(n-k)!}",
        ("permutation", "combinatorics", "discrete", "排列", "排列组合", "离散数学"),
    ),
    _snippet(
        "Inclusion-exclusion principle",
        r"\left|\bigcup_{i=1}^{n}A_i\right|=\sum_i|A_i|-\sum_{i<j}|A_i\cap A_j|+\cdots+(-1)^{n+1}\left|\bigcap_{i=1}^{n}A_i\right|",
        ("inclusion exclusion", "set", "discrete", "容斥", "集合", "离散数学"),
    ),
    _snippet(
        "Graph handshaking lemma",
        r"\sum_{v\in V}\deg(v)=2|E|",
        ("graph", "degree", "discrete", "图论", "度数", "离散数学"),
    ),
    _snippet(
        "Euler formula for planar graphs",
        r"|V|-|E|+|F|=2",
        ("graph", "planar", "euler", "图论", "欧拉公式", "平面图"),
    ),
    # Signals, transforms, and complex numbers
    _snippet(
        "Euler formula",
        r"e^{i\theta}=\cos\theta+i\sin\theta",
        ("complex", "euler", "signal", "复数", "欧拉公式", "信号"),
    ),
    _snippet(
        "Fourier transform",
        r"X(\omega)=\int_{-\infty}^{\infty}x(t)e^{-i\omega t}\,dt",
        ("fourier", "signal", "transform", "傅里叶", "信号", "变换"),
    ),
    _snippet(
        "Convolution",
        r"(f*g)(t)=\int_{-\infty}^{\infty}f(\tau)g(t-\tau)\,d\tau",
        ("convolution", "signal", "transform", "卷积", "信号"),
    ),
    _snippet(
        "Discrete Fourier transform",
        r"X_k=\sum_{n=0}^{N-1}x_n e^{-i2\pi kn/N}",
        ("dft", "fourier", "signal", "离散傅里叶", "信号"),
    ),
    _snippet(
        "Laplace transform",
        r"F(s)=\int_{0}^{\infty}f(t)e^{-st}\,dt",
        ("laplace", "transform", "signal", "拉普拉斯", "变换"),
    ),
    # Physics and engineering basics
    _snippet(
        "Newton second law",
        r"\sum \mathbf{F}=m\mathbf{a}",
        ("physics", "mechanics", "newton", "物理", "力学", "牛顿"),
    ),
    _snippet(
        "Kinetic energy",
        r"E_k=\frac{1}{2}mv^2",
        ("physics", "mechanics", "energy", "物理", "力学", "动能"),
    ),
    _snippet(
        "Ohm law",
        r"U=IR",
        ("circuit", "physics", "electric", "电路", "欧姆", "物理"),
    ),
    _snippet(
        "Capacitor equation",
        r"i(t)=C\frac{du(t)}{dt}",
        ("circuit", "capacitor", "electric", "电路", "电容"),
    ),
    # Machine learning and optimization
    _snippet(
        "Gradient descent",
        r"\theta_{t+1}=\theta_t-\eta\nabla_\theta J(\theta_t)",
        ("gradient descent", "machine learning", "optimization", "梯度下降", "机器学习", "优化"),
    ),
    _snippet(
        "Softmax",
        r"\operatorname{softmax}(z_i)=\frac{e^{z_i}}{\sum_{j=1}^{K}e^{z_j}}",
        ("softmax", "machine learning", "classification", "机器学习", "分类"),
    ),
    _snippet(
        "Cross entropy",
        r"L=-\sum_{i=1}^{K}y_i\log(\hat{y}_i)",
        ("cross entropy", "machine learning", "classification", "交叉熵", "机器学习"),
    ),
)


DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "linear_algebra": (
        "linear algebra", "matrix", "determinant", "eigen", "rank", "inverse",
        "vector", "least squares", "线性代数", "矩阵", "行列式", "特征值", "特征向量",
        "秩", "逆矩阵", "向量", "最小二乘",
    ),
    "calculus": (
        "calculus", "derivative", "integral", "taylor", "gradient", "hessian",
        "微积分", "导数", "积分", "泰勒", "梯度", "海森", "极限", "多元函数",
    ),
    "probability": (
        "probability", "statistics", "bayes", "variance", "distribution",
        "概率", "统计", "贝叶斯", "方差", "分布", "期望", "协方差",
    ),
    "discrete": (
        "discrete", "graph", "combinatorics", "set", "离散", "图论", "组合", "排列",
        "集合", "容斥",
    ),
    "signals": (
        "fourier", "signal", "convolution", "laplace", "transform", "complex",
        "傅里叶", "信号", "卷积", "拉普拉斯", "复数", "变换",
    ),
    "physics": (
        "physics", "mechanics", "circuit", "electric", "物理", "力学", "电路", "电容",
        "欧姆",
    ),
    "machine_learning": (
        "machine learning", "classification", "softmax", "gradient descent",
        "机器学习", "分类", "梯度下降", "交叉熵",
    ),
}


def normalize_topic(topic: str) -> str:
    return re.sub(r"\s+", " ", str(topic or "").strip().lower())


def topic_matches(topic: str, keywords: Iterable[str]) -> bool:
    text = normalize_topic(topic)
    return any(str(keyword).lower() in text for keyword in keywords if keyword)


def matched_domains(topic: str) -> set[str]:
    return {
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if topic_matches(topic, keywords)
    }


def build_formula_sheet(topic: str, *, max_items: int = 18) -> str:
    """Return a compact formula sheet for the topic, or an empty string.

    The returned text is intentionally prompt-ready.  It tells the LLM to quote
    formulas verbatim and to add explanations outside math blocks.
    """
    topic_text = normalize_topic(topic)
    if not topic_text:
        return ""

    domains = matched_domains(topic_text)
    if not domains:
        return ""

    picked: list[FormulaSnippet] = []
    seen_titles: set[str] = set()

    for formula in FORMULAS:
        if len(picked) >= max_items:
            break
        if formula.title in seen_titles:
            continue
        if topic_matches(topic_text, formula.keywords):
            picked.append(formula)
            seen_titles.add(formula.title)

    if len(picked) < min(max_items, 8):
        for formula in FORMULAS:
            if len(picked) >= max_items:
                break
            if formula.title in seen_titles:
                continue
            if any(topic_matches(" ".join(formula.keywords), DOMAIN_KEYWORDS[d]) for d in domains):
                picked.append(formula)
                seen_titles.add(formula.title)

    if not picked:
        return ""

    lines = [
        "Stable formula templates. Reuse these LaTeX blocks verbatim; put Chinese explanations outside $$...$$.",
    ]
    for formula in picked:
        lines.append(f"- {formula.title}:")
        lines.append(formula.latex)
        if formula.note:
            lines.append(f"  Note: {formula.note}")
    return "\n".join(lines)


def validate_formula_sheet(sheet: str) -> list[str]:
    """Lightweight structural validation for generated template sheets."""
    errors: list[str] = []
    if sheet.count("$$") % 2 != 0:
        errors.append("display math delimiters are not balanced")

    begins = re.findall(r"\\begin\{([^}]+)\}", sheet)
    ends = re.findall(r"\\end\{([^}]+)\}", sheet)
    if begins != ends:
        errors.append("LaTeX begin/end environments are not balanced")

    for env in ("bmatrix", "pmatrix", "vmatrix", "matrix"):
        if sheet.count(rf"\begin{{{env}}}") != sheet.count(rf"\end{{{env}}}"):
            errors.append(f"{env} environment is not balanced")
    return errors
