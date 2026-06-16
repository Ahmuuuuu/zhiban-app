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

/** 标点/空白 — 不需要 karaoke 高亮，也不消耗 timedWords */
const PUNCT_RE = /^[\s，。、；：！？,.;:!?]+$/

/**
 * 将文本渲染为带 karaoke 逐词高亮的 HTML。
 * 与 renderMath 一样处理 LaTeX，同时将普通文字按 timedWords 状态包入 karaoke span。
 *
 * @param {string} text - 待渲染文本
 * @param {Array<{text: string, isDone: boolean, isCurrent: boolean}>} timedWords - 全 slide 的词状态
 * @param {number} wordOffset - 当前 item 在 timedWords 中的起始下标
 * @returns {{ html: string, consumed: number }}
 */
export function renderKaraokeHTML(text, timedWords, wordOffset = 0) {
  if (!text || typeof text !== 'string') return { html: text, consumed: 0 }

  const fixed = fixBrokenLatex(text)
  const words = timedWords || []
  let wi = wordOffset
  let consumedTotal = 0
  let result = ''

  const parts = fixed.split(/(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[^\s\$][^\$]*?\$|\\\([\s\S]*?\\\))/g)

  for (const part of parts) {
    if (!part) continue

    // LaTeX 公式 — 直接渲染，不消耗 timedWords 位置
    if (/^\$\$|^\\\[|^\$|^\\\(/.test(part)) {
      if (part.startsWith('$$') || part.startsWith('\\[')) {
        const f = part.replace(/^\$\$|\$\$$/g, '').replace(/^\\\[|\\\]$/g, '')
        result += render(f, true)
      } else {
        const f = part.replace(/^\$|\$$/g, '').replace(/^\\\(|\\\)$/g, '')
        if (NON_MATH_RE.test(f)) {
          const stripped = f.replace(CJK_STRIP_RE, '').trim()
          if (stripped && stripped.length > 1) {
            try { result += render(stripped, false) } catch { result += `$${f}$` }
          } else {
            result += `$${f}$`
          }
        } else {
          result += render(f, false)
        }
      }
      continue
    }

    // 逐字拆分 — timedWords 已由上层插值为字级，每个 Unicode 字符对应一条
    const chars = [...part]
    for (const ch of chars) {
      if (PUNCT_RE.test(ch)) {
        result += ch
        continue
      }
      const tw = wi < words.length ? words[wi] : null
      const isDone = tw ? tw.isDone : true
      const isCurrent = tw ? tw.isCurrent : false
      const cls = `karaoke-word${isDone ? ' is-done' : ''}${isCurrent ? ' is-current' : ''}`
      result += `<span class="${cls}">${ch}</span>`
      wi++
      consumedTotal++
    }
  }

  return { html: result, consumed: consumedTotal }
}

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
