const backgroundModules = import.meta.glob('../../../../assets/ppt_video/video/backgrounds/*.{png,jpg,jpeg,webp,avif}', {
  eager: true,
  import: 'default'
})

const splitPath = p => p.split(/[/\\]/)

const backgrounds = Object.entries(backgroundModules)
  .map(([path, url]) => {
    const segments = splitPath(path)
    return {
      path,
      name: segments.pop() || '',
      url
    }
  })
  .sort((a, b) => a.path.localeCompare(b.path))

const hashText = text => {
  let hash = 0
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash << 5) - hash) + text.charCodeAt(index)
    hash |= 0
  }
  return Math.abs(hash)
}

const backgroundStyleMap = {
  'huaban-3791568150.webp': {
    tone: 'light',
    accent: '#A8B396',
    accentSoft: '#F2ECD8',
    warm: '#A66D38',
    cardBg: 'rgba(242, 236, 216, 0.74)',
    cardStrong: 'rgba(168, 179, 150, 0.36)',
    cardBorder: 'rgba(86, 34, 16, 0.22)',
    chipBg: 'rgba(242, 236, 216, 0.86)',
    chipText: '#562210',
    line: 'rgba(166, 109, 56, 0.72)',
    numberBg: '#562210',
    numberText: '#F2ECD8'
  },
  'huaban-4088235883.webp': {
    tone: 'light',
    text: '#143D2A',
    muted: 'rgba(20, 61, 42, 0.76)',
    soft: '#275B40',
    accent: '#275B40',
    accentSoft: '#DDE8D6',
    warm: '#8D6B3F',
    cardBg: 'rgba(247, 250, 241, 0.78)',
    cardStrong: 'rgba(221, 232, 214, 0.58)',
    cardBorder: 'rgba(20, 61, 42, 0.18)',
    chipBg: 'rgba(221, 232, 214, 0.84)',
    chipText: '#143D2A',
    line: 'rgba(39, 91, 64, 0.72)',
    numberBg: '#143D2A',
    numberText: '#F7FAF1'
  },
  'huaban-4504637306.webp': {
    tone: 'light',
    text: '#842524',
    muted: 'rgba(132, 37, 36, 0.74)',
    soft: '#607756',
    accent: '#607756',
    accentSoft: '#E9DDC8',
    warm: '#BF6B4B',
    cardBg: 'rgba(233, 221, 200, 0.78)',
    cardStrong: 'rgba(96, 119, 86, 0.28)',
    cardBorder: 'rgba(132, 37, 36, 0.2)',
    chipBg: 'rgba(233, 221, 200, 0.88)',
    chipText: '#842524',
    line: 'rgba(191, 107, 75, 0.72)',
    numberBg: '#842524',
    numberText: '#F4EADB'
  },
  'huaban-4709109974.webp': {
    tone: 'light',
    text: '#562210',
    muted: 'rgba(86, 34, 16, 0.74)',
    soft: '#A8B396',
    accent: '#A8B396',
    accentSoft: '#F2ECD8',
    warm: '#A66D38',
    cardBg: 'rgba(242, 236, 216, 0.74)',
    cardStrong: 'rgba(168, 179, 150, 0.36)',
    cardBorder: 'rgba(86, 34, 16, 0.22)',
    chipBg: 'rgba(242, 236, 216, 0.86)',
    chipText: '#562210',
    line: 'rgba(166, 109, 56, 0.72)',
    numberBg: '#562210',
    numberText: '#F2ECD8'
  },
  'huaban-5264385044.webp': {
    tone: 'light',
    text: '#111B49',
    muted: 'rgba(17, 27, 73, 0.74)',
    soft: '#52609C',
    accent: '#52609C',
    accentSoft: '#7E95B8',
    warm: '#E7DDCB',
    cardBg: 'rgba(231, 221, 203, 0.76)',
    cardStrong: 'rgba(126, 149, 184, 0.34)',
    cardBorder: 'rgba(17, 27, 73, 0.2)',
    chipBg: 'rgba(231, 221, 203, 0.88)',
    chipText: '#111B49',
    line: 'rgba(82, 96, 156, 0.72)',
    numberBg: '#111B49',
    numberText: '#E7DDCB'
  },
  'huaban-5657800169.webp': {
    tone: 'dark',
    text: '#F4F1E8',
    muted: 'rgba(244, 241, 232, 0.78)',
    soft: '#D8D1BD',
    accent: '#2E5A44',
    accentSoft: 'rgba(46, 90, 68, 0.36)',
    warm: '#E8C75F',
    cardBg: 'rgba(20, 45, 35, 0.42)',
    cardStrong: 'rgba(46, 90, 68, 0.52)',
    cardBorder: 'rgba(244, 241, 232, 0.24)',
    chipBg: 'rgba(46, 90, 68, 0.62)',
    chipText: '#F4F1E8',
    line: 'rgba(232, 199, 95, 0.78)',
    numberBg: '#F4F1E8',
    numberText: '#254A39'
  },
  'huaban-6257671203.webp': {
    tone: 'dark',
    text: '#F4F1E8',
    muted: 'rgba(244, 241, 232, 0.78)',
    soft: '#D8D1BD',
    accent: '#2E5A44',
    accentSoft: 'rgba(46, 90, 68, 0.36)',
    warm: '#E8C75F',
    cardBg: 'rgba(20, 45, 35, 0.42)',
    cardStrong: 'rgba(46, 90, 68, 0.52)',
    cardBorder: 'rgba(244, 241, 232, 0.24)',
    chipBg: 'rgba(46, 90, 68, 0.62)',
    chipText: '#F4F1E8',
    line: 'rgba(232, 199, 95, 0.78)',
    numberBg: '#F4F1E8',
    numberText: '#254A39'
  },
  'huaban-6596237367.webp': {
    tone: 'light',
    text: '#1E466C',
    muted: 'rgba(30, 70, 108, 0.72)',
    soft: '#7FA7C5',
    accent: '#7FA7C5',
    accentSoft: '#B4D3DE',
    warm: '#EFE0C9',
    cardBg: 'rgba(247, 250, 252, 0.78)',
    cardStrong: 'rgba(180, 211, 222, 0.46)',
    cardBorder: 'rgba(30, 70, 108, 0.16)',
    chipBg: 'rgba(239, 224, 201, 0.86)',
    chipText: '#1E466C',
    line: 'rgba(127, 167, 197, 0.72)',
    numberBg: '#1E466C',
    numberText: '#F7FAFC'
  },
  'huaban-6856619161.webp': {
    tone: 'light',
    text: '#0C5318',
    muted: 'rgba(12, 83, 24, 0.74)',
    soft: '#2B7229',
    accent: '#2B7229',
    accentSoft: '#E5E2AE',
    warm: '#F4EED6',
    cardBg: 'rgba(248, 248, 244, 0.78)',
    cardStrong: 'rgba(229, 226, 174, 0.52)',
    cardBorder: 'rgba(12, 83, 24, 0.18)',
    chipBg: 'rgba(244, 238, 214, 0.88)',
    chipText: '#0C5318',
    line: 'rgba(43, 114, 41, 0.72)',
    numberBg: '#0C5318',
    numberText: '#F8F8F4'
  },
  'huaban-7167290251.webp': {
    tone: 'light',
    text: '#24272D',
    muted: 'rgba(36, 39, 45, 0.72)',
    soft: '#59606B',
    accent: '#59606B',
    accentSoft: '#E4E6EA',
    warm: '#B88A55',
    cardBg: 'rgba(246, 247, 248, 0.78)',
    cardStrong: 'rgba(228, 230, 234, 0.7)',
    cardBorder: 'rgba(36, 39, 45, 0.16)',
    chipBg: 'rgba(228, 230, 234, 0.88)',
    chipText: '#24272D',
    line: 'rgba(89, 96, 107, 0.66)',
    numberBg: '#24272D',
    numberText: '#F6F7F8'
  }
}

const lightNamePattern = /light|white|paper|green|blue/i
const darkNamePattern = /dark|black|cinema/i

export const selectVideoBackground = ({ title = '', content = '' } = {}) => {
  if (!backgrounds.length) return ''
  const seed = `${title} ${content}`.trim() || 'video-preview'
  return backgrounds[hashText(seed) % backgrounds.length].url
}

export const getVideoBackgroundStyle = backgroundUrl => {
  const target = backgrounds.find(item => item.url === backgroundUrl)
  const name = target?.name || String(backgroundUrl || '')
  const configured = backgroundStyleMap[name]
  if (configured) return configured
  if (darkNamePattern.test(name)) return { tone: 'dark' }
  if (lightNamePattern.test(name)) return { tone: 'light' }
  return { tone: 'dark' }
}

export const getVideoBackgroundTone = backgroundUrl => {
  return getVideoBackgroundStyle(backgroundUrl).tone || 'dark'
}

export const videoAssetStats = {
  backgroundCount: backgrounds.length
}
