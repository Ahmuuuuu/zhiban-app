const katex = require('katex');

// 当前 renderMath.js 的实现
function fixDollarSigns(text) {
  return text.replace(/(^|[^$\\{}^_])([A-Za-z0-9])\$(?=[\s，。、；：,.;:()（）、一-鿿])/g, '$1$$$2$$');
}

const render = (formula, displayMode) => {
  try {
    return katex.renderToString(formula.trim(), { displayMode, throwOnError: false, trust: true });
  } catch { return formula; }
};

function renderMath(text) {
  if (!text || typeof text !== 'string') return text;
  const fixed = fixDollarSigns(text);
  return fixed
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, f) => render(f, true))
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, f) => render(f, true))
    .replace(/\$([^\s\$][\s\S]*?[^\s\\])\$/g, (_, f) => render(f, false))
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, f) => render(f, false));
}

// 测试用例
const tests = [
  // 用户报告的矩阵公式
  '$A = \\begin{bmatrix}1 & 0 \\\\ 0 & 0\\end{bmatrix}$',
  // 带下标
  '$c_{ij} = \\sum_{k=1}^{n} a_{ik} b_{kj}$',
  // 混合文本
  '$A$ 的列数等于 $B$ 的行数',
  // $放反了的情况
  '矩阵 C$ 的第 $i 行第 j$ 列',
  // $A 没闭合 + i$放反
  '$A 的第 i$ 行',
  // 分数
  '$\\frac{1}{2} + \\frac{3}{4}$',
  // 多行公式用 $$
  '$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$',
  // 行内矩阵
  '矩阵 $\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$ 的行列式',
  // 正确公式不应被破坏
  '已知 $x^2 + y^2 = 1$，求 $z = x + y$ 的最大值。',
];

console.log('=== KaTeX 渲染测试 ===\n');

let pass = 0;
let fail = 0;

for (const input of tests) {
  const result = renderMath(input);
  // 检查结果中是否还有裸露的 $ 符号（说明没被正确替换）
  const bareDollar = (result.match(/\$/g) || []).length;
  // 检查结果是否包含 katex-html（说明渲染成功）
  const hasKatex = result.includes('katex-html');
  // 检查是否包含原始 LaTeX 命令（说明渲染失败退回了原文）
  const hasRawLaTeX = /\\begin|\\sum|\\frac|\\end/.test(result) && !hasKatex;

  const ok = hasKatex || (!hasRawLaTeX && bareDollar === 0);
  if (ok) pass++; else fail++;

  console.log(`${ok ? '✓' : '✗'} [bare$=${bareDollar} katex=${hasKatex} raw=${hasRawLaTeX}]`);
  console.log(`  IN : ${input.substring(0, 120)}`);
  console.log(`  OUT: ${result.substring(0, 200)}`);
  console.log('');
}

console.log(`=== ${pass}/${pass+fail} 通过 ===`);
