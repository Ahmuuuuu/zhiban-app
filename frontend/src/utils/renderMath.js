import katex from 'katex'

const render = (formula, displayMode) => {
  try {
    return katex.renderToString(formula.trim(), {
      displayMode,
      throwOnError: false,
      trust: true,
    })
  } catch {
    return formula
  }
}

/**
 * 修复 LLM 常见公式问题：
 * 1. 裸 \begin{...}...\end{...} 没包 $ → 补 $$...$$
 * 2. $ 放反：A$ → $A$
 */
function fixBrokenLatex(text) {
  // 1. 裸 \begin{env}...\end{env} 补 $$ 包裹
  text = text.replace(
    /(?<!\$)(\\begin\{([a-zA-Z*]+)\}[\s\S]*?\\end\{\2\})(?!\$)/g,
    '$$$1$$',
  )
  // 2. $ 放反：数学表达式后紧跟 $ 但前面无 $ 配对 → 补开头的 $
  //    匹配多字符变量（AB、m×n）而非仅单个字母
  return text.replace(
    /(^|[^$\\{}^_])([A-Za-z0-9×÷±≤≥≠≈·∑∏∫√∞∂∇+\-*=<>]+)\$(?=[\s，。、；：,.;:()（）、一-鿿])/g,
    '$1$$$2$$',
  )
}

/** CJK 及中文标点 — 这些字符不应出现在纯数学公式中 */
const NON_MATH_RE = /[一-鿿㐀-䶿豈-﫿　-〿＀-￯]/

/**
 * 将文本中的 LaTeX 公式渲染为 HTML。
 * 支持：$$...$$ / \[...\] （块级），$...$ / \(...\) （行内）
 */
export function renderMath(text) {
  if (!text || typeof text !== 'string') return text

  const fixed = fixBrokenLatex(text)

  // 按顺序处理：块级优先，避免 $ 干扰 $$
  return fixed
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, f) => render(f, true))
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, f) => render(f, true))
    .replace(/\$([^\s\$][^\$]*)\$/g, (_, f) => {
      if (NON_MATH_RE.test(f)) return `$${f}$`
      return render(f, false)
    })
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, f) => render(f, false))
}
