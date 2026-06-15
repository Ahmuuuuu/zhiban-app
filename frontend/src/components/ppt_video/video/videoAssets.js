const backgroundModules = import.meta.glob('../../../assets/ppt_video/video/backgrounds/*.{png,jpg,jpeg,webp,avif}', {
  eager: true,
  import: 'default'
})

const backgrounds = Object.entries(backgroundModules)
  .map(([path, url]) => ({
    path,
    name: path.split('/').pop() || '',
    url
  }))
  .sort((a, b) => a.path.localeCompare(b.path))

const hashText = text => {
  let hash = 0
  for (let index = 0; index < text.length; index += 1) {
    hash = ((hash << 5) - hash) + text.charCodeAt(index)
    hash |= 0
  }
  return Math.abs(hash)
}

export const selectVideoBackground = ({ title = '', content = '' } = {}) => {
  if (!backgrounds.length) return ''
  const seed = `${title} ${content}`.trim() || 'video-preview'
  return backgrounds[hashText(seed) % backgrounds.length].url
}

export const videoAssetStats = {
  backgroundCount: backgrounds.length
}
