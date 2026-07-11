import { resolveApiUrl } from '../api/apis'

const palettes = [
  ['#2f5d9f', '#58aeea', '#e9f7fb'],
  ['#1e8f8c', '#55c9a7', '#e9fbf6'],
  ['#8f5bbf', '#d9a7ff', '#f8f0ff'],
  ['#c96f22', '#f2b705', '#fff7df'],
  ['#d94d7b', '#ef8fb0', '#fff0f5'],
  ['#566bd8', '#8eb1ff', '#eff4ff']
]

const documentMotifs = [
  { icon: 'notes', side: '#f2b705' },
  { icon: 'chart', side: '#55c9a7' },
  { icon: 'stack', side: '#d9a7ff' },
  { icon: 'quote', side: '#ef8fb0' }
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
  if (title.length <= 10) return [title]
  return [title.slice(0, 10), title.slice(10, 20)]
}

const resourceKind = resource => {
  const text = String(`${resource?.type || ''} ${resource?.category || ''} ${resource?.categoryLabel || ''} ${resource?.title || ''}`).toLowerCase()
  if (/image|图片/.test(text)) return 'image'
  if (/video|mp4|视频/.test(text)) return 'video'
  if (/mind|xmind|导图/.test(text)) return 'mindmap'
  if (/ppt|powerpoint|presentation|slide/.test(text)) return 'ppt'
  if (/exercise|quiz|question|exam|题|练习/.test(text)) return 'exercise'
  return 'document'
}

const toDataSvg = svg => `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg.trim())}`

const renderPptCover = ({ primary, accent, rawTitle }) => {
  const [lineOne, lineTwo = ''] = splitTitleLines(rawTitle).map(escapeXml)
  return toDataSvg(`
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
  `)
}

const renderDocumentCover = ({ primary, accent, paper, rawTitle, resource }) => {
  const [lineOne, lineTwo = ''] = splitTitleLines(rawTitle).map(escapeXml)
  const motif = documentMotifs[hashText(rawTitle || resource?.doc_id) % documentMotifs.length]
  const motifSvg = {
    notes: `
      <rect x="0" y="0" width="86" height="12" rx="6" fill="${primary}" opacity="0.24"/>
      <rect x="0" y="28" width="118" height="12" rx="6" fill="${accent}" opacity="0.3"/>
      <rect x="0" y="56" width="72" height="12" rx="6" fill="${primary}" opacity="0.18"/>
    `,
    chart: `
      <rect x="0" y="38" width="18" height="42" rx="6" fill="${primary}" opacity="0.74"/>
      <rect x="30" y="14" width="18" height="66" rx="6" fill="${accent}" opacity="0.74"/>
      <rect x="60" y="28" width="18" height="52" rx="6" fill="${motif.side}" opacity="0.82"/>
      <path d="M0 16L30 2l30 16 34-12" fill="none" stroke="${primary}" stroke-width="6" stroke-linecap="round" opacity="0.32"/>
    `,
    stack: `
      <rect x="0" y="12" width="118" height="76" rx="12" fill="${primary}" opacity="0.16"/>
      <rect x="14" y="0" width="118" height="76" rx="12" fill="${accent}" opacity="0.24"/>
      <rect x="28" y="-12" width="118" height="76" rx="12" fill="#ffffff" opacity="0.76"/>
      <rect x="44" y="12" width="70" height="8" rx="4" fill="${primary}" opacity="0.26"/>
      <rect x="44" y="32" width="92" height="8" rx="4" fill="${accent}" opacity="0.32"/>
    `,
    quote: `
      <text x="0" y="70" font-family="Georgia, serif" font-size="92" font-weight="900" fill="${primary}" opacity="0.18">“</text>
      <rect x="48" y="18" width="88" height="10" rx="5" fill="${accent}" opacity="0.34"/>
      <rect x="48" y="42" width="118" height="10" rx="5" fill="${primary}" opacity="0.2"/>
      <rect x="48" y="66" width="68" height="10" rx="5" fill="${motif.side}" opacity="0.42"/>
    `
  }[motif.icon]

  return toDataSvg(`
    <svg xmlns="http://www.w3.org/2000/svg" width="520" height="280" viewBox="0 0 520 280">
      <defs>
        <linearGradient id="docBg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="${paper}"/>
          <stop offset="46%" stop-color="#ffffff"/>
          <stop offset="100%" stop-color="#eef6ff"/>
        </linearGradient>
        <linearGradient id="docBand" x1="0" x2="1">
          <stop offset="0%" stop-color="${primary}"/>
          <stop offset="52%" stop-color="${accent}"/>
          <stop offset="100%" stop-color="${motif.side}"/>
        </linearGradient>
        <filter id="docShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="12" stdDeviation="12" flood-color="#17345f" flood-opacity="0.16"/>
        </filter>
      </defs>
      <rect width="520" height="280" rx="24" fill="url(#docBg)"/>
      <path d="M0 0h520v80H0z" fill="url(#docBand)"/>
      <path d="M342 0h178v280H342z" fill="${primary}" opacity="0.06"/>
      <path d="M390 0c62 30 96 78 102 144 5 60-17 101-66 124h94V0z" fill="${accent}" opacity="0.12"/>
      <rect x="42" y="38" width="304" height="204" rx="18" fill="#ffffff" filter="url(#docShadow)"/>
      <rect x="42" y="38" width="304" height="44" rx="18" fill="#f7fbff"/>
      <path d="M42 64h304" stroke="${primary}" stroke-opacity="0.1" stroke-width="2"/>
      <rect x="66" y="58" width="76" height="10" rx="5" fill="${primary}" opacity="0.18"/>
      <rect x="264" y="56" width="42" height="14" rx="7" fill="${motif.side}" opacity="0.28"/>
      <text x="66" y="124" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="26" font-weight="900" fill="#17345f">${lineOne}</text>
      <text x="66" y="158" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="22" font-weight="800" fill="#4c6382">${lineTwo}</text>
      <rect x="66" y="184" width="218" height="8" rx="4" fill="${primary}" opacity="0.16"/>
      <rect x="66" y="206" width="176" height="8" rx="4" fill="${accent}" opacity="0.24"/>
      <rect x="66" y="224" width="238" height="8" rx="4" fill="${primary}" opacity="0.1"/>
      <g transform="translate(374 126)">
        <rect x="-18" y="-24" width="118" height="104" rx="20" fill="#ffffff" opacity="0.78"/>
        ${motifSvg}
      </g>
      <rect x="380" y="34" width="84" height="28" rx="14" fill="#ffffff" opacity="0.92"/>
      <text x="422" y="53" text-anchor="middle" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="15" font-weight="900" fill="${primary}">文档</text>
      <path d="M42 38h18v204H42z" fill="${motif.side}" opacity="0.82"/>
    </svg>
  `)
}

const renderGenericCover = ({ primary, accent, paper, kind, rawTitle }) => {
  const title = escapeXml(compactTitle(rawTitle))
  const label = escapeXml(typeLabels[kind] || '资源')

  return toDataSvg(`
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
  `)
}

const renderIllustratedResourceCover = ({ primary, accent, paper, kind, rawTitle, resource }) => {
  const [lineOne, lineTwo = ''] = splitTitleLines(rawTitle).map(escapeXml)
  const seed = hashText(rawTitle || resource?.doc_id || resource?.sourceId || kind)
  const warm = ['#f2b705', '#ef8fb0', '#55c9a7', '#8eb1ff'][seed % 4]
  const cool = ['#e9fbf6', '#eff4ff', '#fff7df', '#f8f0ff'][seed % 4]
  const accentTwo = ['#1e8f8c', '#566bd8', '#c96f22', '#8f5bbf'][seed % 4]
  const motif = {
    ppt: `
      <g transform="translate(318 66)">
        <rect x="24" y="20" width="132" height="92" rx="18" fill="#ffffff" opacity="0.7"/>
        <rect x="0" y="0" width="132" height="92" rx="18" fill="#ffffff" filter="url(#shadow)"/>
        <path d="M18 60c26-34 44-18 58-36 20 20 34 40 38 54H18z" fill="${accent}" opacity="0.3"/>
        <circle cx="94" cy="28" r="12" fill="${warm}" opacity="0.86"/>
        <rect x="18" y="18" width="52" height="8" rx="4" fill="${primary}" opacity="0.22"/>
        <rect x="18" y="36" width="76" height="7" rx="3.5" fill="${accentTwo}" opacity="0.24"/>
      </g>
    `,
    mindmap: `
      <g transform="translate(326 58)" fill="none" stroke-linecap="round">
        <path d="M72 76L26 34M72 76l76-36M72 76l-18 76M72 76l88 76" stroke="${primary}" stroke-width="8" opacity="0.2"/>
        <circle cx="72" cy="76" r="28" fill="#ffffff" stroke="${primary}" stroke-width="0" filter="url(#shadow)"/>
        <circle cx="26" cy="34" r="18" fill="${accent}" opacity="0.8"/>
        <circle cx="148" cy="40" r="22" fill="${warm}" opacity="0.86"/>
        <circle cx="54" cy="152" r="20" fill="${accentTwo}" opacity="0.78"/>
        <circle cx="160" cy="152" r="18" fill="#ffffff" opacity="0.82"/>
      </g>
    `,
    exercise: `
      <g transform="translate(330 62)">
        <rect x="10" y="0" width="132" height="160" rx="24" fill="#ffffff" filter="url(#shadow)"/>
        <path d="M34 46l16 16 34-38" fill="none" stroke="${accentTwo}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
        <rect x="34" y="86" width="84" height="10" rx="5" fill="${primary}" opacity="0.18"/>
        <rect x="34" y="112" width="64" height="10" rx="5" fill="${warm}" opacity="0.42"/>
        <circle cx="122" cy="34" r="32" fill="${accent}" opacity="0.16"/>
      </g>
    `,
    document: `
      <g transform="translate(322 54)">
        <rect x="22" y="20" width="118" height="154" rx="22" fill="${primary}" opacity="0.08"/>
        <rect x="0" y="0" width="124" height="160" rx="22" fill="#ffffff" filter="url(#shadow)"/>
        <path d="M92 0v42h32" fill="${cool}"/>
        <path d="M92 0v42h32" fill="none" stroke="${primary}" stroke-opacity="0.1" stroke-width="2"/>
        <rect x="24" y="48" width="58" height="9" rx="4.5" fill="${primary}" opacity="0.18"/>
        <rect x="24" y="74" width="80" height="9" rx="4.5" fill="${accent}" opacity="0.26"/>
        <rect x="24" y="100" width="66" height="9" rx="4.5" fill="${warm}" opacity="0.35"/>
      </g>
    `,
    video: `
      <g transform="translate(330 64)">
        <rect x="0" y="0" width="132" height="96" rx="16" fill="#ffffff" filter="url(#shadow)"/>
        <polygon points="52,28 52,68 92,48" fill="${warm}" opacity="0.86"/>
        <rect x="0" y="106" width="132" height="8" rx="4" fill="${primary}" opacity="0.18"/>
        <rect x="0" y="124" width="76" height="8" rx="4" fill="${accent}" opacity="0.32"/>
        <rect x="84" y="124" width="48" height="8" rx="4" fill="${warm}" opacity="0.22"/>
      </g>
    `
  }[kind] || `
    <g transform="translate(326 62)">
      <rect x="0" y="0" width="148" height="148" rx="34" fill="#ffffff" filter="url(#shadow)"/>
      <path d="M34 112c18-54 48-84 96-96" fill="none" stroke="${accent}" stroke-width="16" stroke-linecap="round" opacity="0.52"/>
      <circle cx="48" cy="48" r="20" fill="${warm}" opacity="0.86"/>
      <circle cx="104" cy="92" r="28" fill="${primary}" opacity="0.16"/>
    </g>
  `

  return toDataSvg(`
    <svg xmlns="http://www.w3.org/2000/svg" width="520" height="280" viewBox="0 0 520 280">
      <defs>
        <linearGradient id="learningBg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="${paper}"/>
          <stop offset="52%" stop-color="#ffffff"/>
          <stop offset="100%" stop-color="${cool}"/>
        </linearGradient>
        <linearGradient id="ribbon" x1="0" x2="1">
          <stop offset="0%" stop-color="${primary}"/>
          <stop offset="100%" stop-color="${accent}"/>
        </linearGradient>
        <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#17345f" flood-opacity="0.16"/>
        </filter>
      </defs>
      <rect width="520" height="280" rx="28" fill="url(#learningBg)"/>
      <path d="M0 0h520v76H0z" fill="url(#ribbon)" opacity="0.9"/>
      <circle cx="448" cy="48" r="96" fill="#ffffff" opacity="0.14"/>
      <circle cx="72" cy="242" r="116" fill="${accent}" opacity="0.12"/>
      <path d="M34 212c70-48 134-42 194 18 28 28 58 32 92 12" fill="none" stroke="${primary}" stroke-width="16" stroke-linecap="round" opacity="0.08"/>
      <rect x="38" y="42" width="236" height="176" rx="24" fill="#ffffff" opacity="0.74" filter="url(#shadow)"/>
      <rect x="62" y="68" width="88" height="10" rx="5" fill="${warm}" opacity="0.64"/>
      <text x="82" y="122" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="24" font-weight="900" fill="#17345f">${lineOne}</text>
      <text x="82" y="154" font-family="Microsoft YaHei, PingFang SC, sans-serif" font-size="20" font-weight="800" fill="#4c6382">${lineTwo}</text>
      <rect x="82" y="182" width="126" height="8" rx="4" fill="${primary}" opacity="0.16"/>
      <rect x="82" y="201" width="166" height="8" rx="4" fill="${accent}" opacity="0.18"/>
      ${motif}
    </svg>
  `)
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

const getGeneratedResourceCoverUrl = resource => {
  const kind = resourceKind(resource)
  if (kind === 'image' && resource?.previewUrl) return resolveApiUrl(resource.previewUrl)

  const [primary, accent, paper] = palettes[hashText(resource?.doc_id || resource?.sourceId || resource?.title) % palettes.length]
  const rawTitle = resource?.title || resource?.filename
  const coverContext = { primary, accent, paper, rawTitle, resource, kind }

  return renderIllustratedResourceCover(coverContext)
}

const shouldUseExplicitCover = resource => {
  // 只有图片有真实预览图才用原图做封面，其余全部走生成
  const kind = resourceKind(resource)
  return kind === 'image' && Boolean(resource?.previewUrl)
}

export const getResourceCoverUrl = resource => {
  const explicitCover = getExplicitResourceCoverUrl(resource)
  if (explicitCover && shouldUseExplicitCover(resource)) return explicitCover

  return getGeneratedResourceCoverUrl(resource)
}
