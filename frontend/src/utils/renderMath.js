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
  // 1. 清理 \begin{env}...\end{env} 周围游离的 $，统一用 $$ 包裹
  //    LLM 常见错误：裸奔、$ 放一边、$...$ 内嵌块级环境
  text = text.replace(
    /\$*\\begin\{([a-zA-Z*]+)\}[\s\S]*?\\end\{\1\}\$*/g,
    (match) => `$$${match.replace(/^\$+|\$+$/g, '')}$$`,
  )
  // 2. $ 放反：数学表达式后紧跟 $ 但前面无 $ 配对 → 补开头的 $
  return text.replace(
    /(^|[^$\\{}^_])([A-Za-z0-9×÷±≤≥≠≈·∑∏∫√∞∂∇+\-*=<>]+)\$(?=[\s，。、；：,.;:()（）、一-鿿])/g,
    '$1$$$2$$',
  )
}

/** CJK 及中文标点 — 这些字符不应出现在纯数学公式中 */
const NON_MATH_RE = /[一-鿿㐀-䶿豈-﫿　-〿＀-￯]/
const CJK_STRIP_RE = /[一-鿿㐀-䶿豈-﫿　-〿＀-￯，。、；：！？（）【】《》""'']/g

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
      if (NON_MATH_RE.test(f)) {
        // 尝试剥离中文后渲染数学部分
        const stripped = f.replace(CJK_STRIP_RE, '').trim()
        if (stripped && stripped.length > 1) {
          try {
            return render(stripped, false)
          } catch {
            return `$${f}$`
          }
        }
        return `$${f}$`  // 纯中文，不渲染
      }
      return render(f, false)
    })
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, f) => render(f, false))
}
