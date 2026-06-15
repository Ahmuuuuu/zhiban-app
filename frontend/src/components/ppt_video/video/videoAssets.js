const backgroundModules = import.meta.glob('../../../assets/ppt_video/video/backgrounds/*.{png,jpg,jpeg,webp,avif}', {
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
    tone: 'light'
  },
  'huaban-4088235883.webp': {
    tone: 'light',
    text: '#173d2b',
    muted: 'rgba(23, 61, 43, 0.76)',
    soft: 'rgba(31, 87, 61, 0.92)',
    line: 'rgba(23, 91, 61, 0.72)',
    numberBg: '#173d2b',
    numberText: '#ffffff'
  },
  'huaban-4504637306.webp': {
    tone: 'light',
    text: '#25282d',
    muted: 'rgba(37, 40, 45, 0.72)',
    soft: 'rgba(55, 60, 68, 0.9)',
    line: 'rgba(37, 40, 45, 0.62)',
    numberBg: '#25282d',
    numberText: '#ffffff'
  },
  'huaban-4709109974.webp': {
    tone: 'light',
    text: '#25282d',
    muted: 'rgba(37, 40, 45, 0.72)',
    soft: 'rgba(55, 60, 68, 0.9)',
    line: 'rgba(37, 40, 45, 0.62)',
    numberBg: '#25282d',
    numberText: '#ffffff'
  },
  'huaban-5264385044.webp': {
    tone: 'light',
    text: '#1d3248',
    muted: 'rgba(29, 50, 72, 0.74)',
    soft: 'rgba(43, 76, 110, 0.9)',
    line: 'rgba(31, 99, 214, 0.62)',
    numberBg: '#1d3248',
    numberText: '#ffffff'
  },
  'huaban-5657800169.webp': {
    tone: 'dark',
    text: '#f4f1e8',
    muted: 'rgba(244, 241, 232, 0.78)',
    soft: 'rgba(255, 250, 235, 0.9)',
    line: 'rgba(244, 241, 232, 0.72)',
    numberBg: '#f4f1e8',
    numberText: '#204a37'
  },
  'huaban-6257671203.webp': {
    tone: 'dark',
    text: '#f4f1e8',
    muted: 'rgba(244, 241, 232, 0.78)',
    soft: 'rgba(255, 250, 235, 0.9)',
    line: 'rgba(244, 241, 232, 0.72)',
    numberBg: '#f4f1e8',
    numberText: '#204a37'
  },
  'huaban-6596237367.webp': {
    tone: 'light',
    text: '#123a68',
    muted: 'rgba(18, 58, 104, 0.74)',
    soft: 'rgba(27, 82, 140, 0.9)',
    line: 'rgba(18, 58, 104, 0.64)',
    numberBg: '#123a68',
    numberText: '#ffffff'
  },
  'huaban-6856619161.webp': {
    tone: 'light',
    text: '#25282d',
    muted: 'rgba(37, 40, 45, 0.72)',
    soft: 'rgba(55, 60, 68, 0.9)',
    line: 'rgba(37, 40, 45, 0.62)',
    numberBg: '#25282d',
    numberText: '#ffffff'
  },
  'huaban-7167290251.webp': {
    tone: 'light',
    text: '#25282d',
    muted: 'rgba(37, 40, 45, 0.72)',
    soft: 'rgba(55, 60, 68, 0.9)',
    line: 'rgba(37, 40, 45, 0.62)',
    numberBg: '#25282d',
    numberText: '#ffffff'
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
