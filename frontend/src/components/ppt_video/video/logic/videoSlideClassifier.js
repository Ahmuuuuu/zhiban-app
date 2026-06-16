/**
 * 分类逻辑：后端 layout 字段说了算，前端不再猜内容。
 *
 * 后端 LLM 产出 title + bullets + 可选 layout，
 * layout 取值：intro | formula | vocabulary | keypoint（或不传）
 * 不传 layout 默认走 keypoint。
 */

export const classifyVideoSlide = slide => {
  // 第一张永远是 intro
  if (Number(slide?.index || 0) === 0) return 'intro'

  const layout = String(slide?.layout || '').toLowerCase()

  if (layout === 'formula') return 'formula'
  if (layout === 'vocabulary') return 'vocabulary'
  if (layout === 'intro') return 'intro'

  // 其他所有情况 → keypoint
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
