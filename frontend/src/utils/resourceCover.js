import { resolveApiUrl } from '../api/apis'

const palettes = [
  ['#2f5d9f', '#58aeea', '#e9f7fb'],
  ['#1e8f8c', '#55c9a7', '#e9fbf6'],
  ['#8f5bbf', '#d9a7ff', '#f8f0ff'],
  ['#c96f22', '#f2b705', '#fff7df'],
  ['#d94d7b', '#ef8fb0', '#fff0f5'],
  ['#566bd8', '#8eb1ff', '#eff4ff']
]

const typeLabels = {
  document: '文档',
  reference: '文档',
  ppt: 'PPT',
  powerpoint: 'PPT',
  presentation: 'PPT',
  mindmap: '导图',
  exercise: '题库',
  quiz: '题库',
  image: '图片',
  video: '视频'
}

const escapeXml = value => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')

const hashText = value => {
  const text = String(value || '')
  let hash = 0
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(index)) | 0
  }
  return Math.abs(hash)
}

const compactTitle = value => {
  const title = String(value || '学习资源').replace(/\s+/g, ' ').trim()
  return title.length > 18 ? `${title.slice(0, 18)}...` : title
}

const resourceKind = resource => {
  const text = String(`${resource?.type || ''} ${resource?.category || ''} ${resource?.categoryLabel || ''} ${resource?.title || ''}`).toLowerCase()
  if (/image|图片/.test(text)) return 'image'
  if (/video|mp4|动态|视频/.test(text)) return 'video'
  if (/mind|xmind|导图/.test(text)) return 'mindmap'
  if (/ppt|powerpoint|presentation|slide/.test(text)) return 'ppt'
  if (/exercise|quiz|question|exam|题|练习/.test(text)) return 'exercise'
  return 'document'
}

export const getResourceCoverUrl = resource => {
  const explicitCover =
    resource?.coverUrl ||
    resource?.cover_url ||
    resource?.thumbnailUrl ||
    resource?.thumbnail_url ||
    resource?.thumb_url ||
    ''
  if (explicitCover) return resolveApiUrl(explicitCover)

  const kind = resourceKind(resource)
  if (kind === 'image' && resource?.previewUrl) return resolveApiUrl(resource.previewUrl)

  const [primary, accent, paper] = palettes[hashText(resource?.doc_id || resource?.sourceId || resource?.title) % palettes.length]
  const title = escapeXml(compactTitle(resource?.title || resource?.filename))
  const label = escapeXml(typeLabels[kind] || '资源')
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="520" height="280" viewBox="0 0 520 280">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="${paper}"/>
          <stop offset="100%" stop-color="#ffffff"/>
        </linearGradient>
        <linearGradient id="band" x1="0" x2="1">
          <stop offset="0%" stop-color="${primary}"/>
          <stop offset="100%" stop-color="${accent}"/>
        </linearGradient>
      </defs>
      <rect width="520" height="280" rx="28" fill="url(#bg)"/>
      <path d="M0 0h520v86H0z" fill="url(#band)" opacity="0.95"/>
      <circle cx="440" cy="56" r="74" fill="#fff" opacity="0.16"/>
      <circle cx="488" cy="26" r="36" fill="#fff" opacity="0.14"/>
      <rect x="34" y="36" width="92" height="34" rx="17" fill="#fff" opacity="0.9"/>
      <text x="80" y="59" text-anchor="middle" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="18" font-weight="800" fill="${primary}">${label}</text>
      <text x="34" y="150" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="32" font-weight="900" fill="#163f8f">${title}</text>
      <rect x="34" y="188" width="260" height="10" rx="5" fill="${primary}" opacity="0.18"/>
      <rect x="34" y="212" width="360" height="10" rx="5" fill="${primary}" opacity="0.12"/>
      <rect x="34" y="236" width="190" height="10" rx="5" fill="${primary}" opacity="0.12"/>
      <path d="M398 162c34 0 62 28 62 62h-62z" fill="${accent}" opacity="0.55"/>
      <path d="M398 224h62c0 34-28 62-62 62z" fill="${primary}" opacity="0.82" transform="translate(0 -62)"/>
    </svg>
  `.trim()

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}
