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

const splitTitleLines = value => {
  const title = String(value || '学习资源').replace(/\s+/g, ' ').trim()
  if (title.length <= 12) return [title]
  return [title.slice(0, 12), title.slice(12, 24)]
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

export const getExplicitResourceCoverUrl = resource => {
  const explicitCover =
    resource?.coverUrl ||
    resource?.cover_url ||
    resource?.thumbnailUrl ||
    resource?.thumbnail_url ||
    resource?.thumb_url ||
    ''
  return explicitCover ? resolveApiUrl(explicitCover) : ''
}

export const getResourceCoverUrl = resource => {
  const explicitCover = getExplicitResourceCoverUrl(resource)
  if (explicitCover) return explicitCover

  const kind = resourceKind(resource)
  if (kind === 'image' && resource?.previewUrl) return resolveApiUrl(resource.previewUrl)

  const [primary, accent, paper] = palettes[hashText(resource?.doc_id || resource?.sourceId || resource?.title) % palettes.length]
  const rawTitle = resource?.title || resource?.filename
  const title = escapeXml(compactTitle(rawTitle))
  const label = escapeXml(typeLabels[kind] || '资源')
  if (kind === 'ppt') {
    const [lineOne, lineTwo = ''] = splitTitleLines(rawTitle).map(escapeXml)
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="520" height="280" viewBox="0 0 520 280">
        <defs>
          <linearGradient id="pptBg" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="${primary}"/>
            <stop offset="56%" stop-color="${accent}"/>
            <stop offset="100%" stop-color="#ffffff"/>
          </linearGradient>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#163f8f" flood-opacity="0.18"/>
          </filter>
        </defs>
        <rect width="520" height="280" rx="20" fill="url(#pptBg)"/>
        <circle cx="452" cy="42" r="92" fill="#ffffff" opacity="0.14"/>
        <circle cx="64" cy="246" r="116" fill="#ffffff" opacity="0.12"/>
        <rect x="54" y="42" width="354" height="196" rx="12" fill="#ffffff" filter="url(#shadow)"/>
        <rect x="54" y="42" width="354" height="48" rx="12" fill="${primary}"/>
        <rect x="54" y="78" width="354" height="12" fill="${primary}"/>
        <text x="78" y="72" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="20" font-weight="900" fill="#ffffff">PPT</text>
        <text x="78" y="136" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="28" font-weight="900" fill="#17345f">${lineOne}</text>
        <text x="78" y="172" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="24" font-weight="800" fill="#31557f">${lineTwo}</text>
        <rect x="78" y="196" width="142" height="9" rx="4.5" fill="${accent}" opacity="0.62"/>
        <rect x="78" y="216" width="238" height="9" rx="4.5" fill="${primary}" opacity="0.18"/>
        <g transform="translate(424 76)">
          <rect x="0" y="0" width="58" height="40" rx="6" fill="#ffffff" opacity="0.9"/>
          <rect x="9" y="9" width="28" height="5" rx="2.5" fill="${primary}" opacity="0.65"/>
          <rect x="9" y="20" width="40" height="5" rx="2.5" fill="${accent}" opacity="0.55"/>
          <rect x="-18" y="58" width="58" height="40" rx="6" fill="#ffffff" opacity="0.74"/>
          <rect x="-9" y="67" width="32" height="5" rx="2.5" fill="${primary}" opacity="0.5"/>
          <rect x="-9" y="78" width="42" height="5" rx="2.5" fill="${accent}" opacity="0.48"/>
        </g>
      </svg>
    `.trim()
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
  }

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
