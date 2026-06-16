const VALID_LAYOUTS = new Set(['intro', 'keypoint', 'formula', 'vocabulary'])

const hasFormula = slide => Array.isArray(slide?.formulas) && slide.formulas.length > 0

const hasVocabularySignal = slide => {
  const text = [
    slide?.title,
    slide?.summary,
    ...(slide?.items || [])
  ].join(' ')
  const englishTerms = text.match(/[A-Za-z][A-Za-z-]{2,}/g) || []
  return /词汇|单词|英语|例句|短语|vocabulary|word|phrase/i.test(text) || englishTerms.length >= 5
}

export const classifyVideoSlide = slide => {
  const layout = String(slide?.layout || '').toLowerCase()
  if (VALID_LAYOUTS.has(layout)) return layout
  // fallback heuristics — 后端未输出有效 layout 时兜底
  if (Number(slide?.index || 0) === 0) return 'intro'
  if (hasFormula(slide) || /formula|math|equation/.test(layout)) return 'formula'
  if (hasVocabularySignal(slide)) return 'vocabulary'
  return 'keypoint'
}

export const getSlideTerms = slide => {
  const text = [
    slide?.title,
    ...(slide?.items || [])
  ].join(' ')
  const english = text.match(/[A-Za-z][A-Za-z\s&-]{2,}/g) || []
  const chinese = text.match(/[一-龥]{2,6}/g) || []
  return [...english, ...chinese]
    .map(item => item.trim().replace(/[，。；：、,.]/g, ''))
    .filter(Boolean)
    .filter((item, index, array) => array.indexOf(item) === index)
    .slice(0, 8)
}
