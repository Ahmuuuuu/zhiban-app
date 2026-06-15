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
  if (Number(slide?.index || 0) === 0) return 'intro'
  const layout = String(slide?.layout || '').toLowerCase()
  if (hasFormula(slide) || /formula|math|equation/.test(layout)) return 'formula'
  if (/comparison|compare|contrast/.test(layout)) return 'comparison'
  if (/process|step|timeline/.test(layout)) return 'process'
  if (hasVocabularySignal(slide)) return 'vocabulary'
  if (/summary|review|recap/.test(layout) || /总结|回顾|小结/.test(`${slide?.title || ''} ${slide?.summary || ''}`)) return 'summary'
  return 'keypoint'
}

export const getSlideTerms = slide => {
  const text = [
    slide?.title,
    ...(slide?.items || [])
  ].join(' ')
  const english = text.match(/[A-Za-z][A-Za-z\s&-]{2,}/g) || []
  const chinese = text.match(/[\u4e00-\u9fa5]{2,6}/g) || []
  return [...english, ...chinese]
    .map(item => item.trim().replace(/[，。；：、,.]/g, ''))
    .filter(Boolean)
    .filter((item, index, array) => array.indexOf(item) === index)
    .slice(0, 8)
}
