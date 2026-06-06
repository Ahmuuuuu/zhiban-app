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
 * 修复 LLM 常见的 $ 错位问题：单字母变量前面漏了 $
 * "A$ 的列数" → "$A$ 的列数"
 * "矩阵 C$ 的第" → "矩阵 $C$ 的第"
 */
function fixDollarSigns(text) {
  // 修复：字母/数字后紧跟 $，但前面不是 $（即 $ 放反了）
  return text.replace(/(^|[^$\\{}^_])([A-Za-z0-9])\$(?=[\s，。、；：,.;:()（）、一-鿿])/g, '$1$$$2$$')
}

/**
 * 将文本中的 LaTeX 公式渲染为 HTML。
 * 支持：$$...$$ / \[...\] （块级），$...$ / \(...\) （行内）
 */
export function renderMath(text) {
  if (!text || typeof text !== 'string') return text

  const fixed = fixDollarSigns(text)

  // 按顺序处理：块级优先，避免 $ 干扰 $$
  return fixed
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, f) => render(f, true))
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, f) => render(f, true))
    .replace(/\$([^\s\$][\s\S]*?[^\s\\])\$/g, (_, f) => render(f, false))
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, f) => render(f, false))
}
