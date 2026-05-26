import { ref } from 'vue'
import { narrateResource, resolveApiUrl } from '../api/apis'

const narrationState = ref({
  resourceId: '',
  loading: false,
  playing: false,
  sectionIndex: 0,
  sections: []
})

let audio = null

const unwrapData = result => result?.data?.data ?? result?.data ?? result ?? {}

const getResourceIdFromUrl = url => {
  const match = String(url || '').match(/\/resource\/([^/?#]+)(?:\/download)?/i)
  return match?.[1] || ''
}

const normalizeSections = narration => {
  const sections = Array.isArray(narration)
    ? narration
    : narration?.sections || narration?.slides || narration?.data?.sections || []

  return (Array.isArray(sections) ? sections : [])
    .map((section, index) => ({
      index: section.index ?? index,
      title: section.title || `第 ${index + 1} 段`,
      text: section.text || '',
      audioUrl: resolveApiUrl(section.audio_url || section.audioUrl || '')
    }))
    .filter(section => section.audioUrl)
}

export const getNarratableResourceId = resource => {
  const directId =
    resource?.resourceId ||
    resource?.resource_id ||
    resource?.sourceId ||
    resource?.source_id ||
    resource?.fileId ||
    resource?.file_id ||
    ''

  if (directId) return String(directId)

  const docId = String(resource?.doc_id || resource?.id || '')
  if (/^generated-\d+$/.test(docId)) return docId.replace(/^generated-/, '')
  if (/^\d+$/.test(docId)) return docId

  return getResourceIdFromUrl(resource?.downloadUrl || resource?.download_url || resource?.url)
}

export const canNarrateResource = resource => {
  const resourceId = getNarratableResourceId(resource)
  if (!resourceId) return false

  const text = String(`${resource?.type || ''} ${resource?.fileType || ''} ${resource?.category || ''} ${resource?.filename || ''} ${resource?.title || ''}`).toLowerCase()
  if (/image|png|jpg|jpeg|webp|gif|video|mp4|mov|quiz|exercise|question|exam/.test(text)) return false

  return /ppt|document|doc|md|case|reading|mindmap|mind_map|mind-map|resource|reference|note|text/.test(text) || Boolean(resource?.content || resource?.fullContent)
}

export function useResourceNarration() {
  const stopCurrentAudio = () => {
    if (audio) {
      audio.pause()
      audio.src = ''
      audio = null
    }
    narrationState.value = {
      ...narrationState.value,
      playing: false,
      loading: false
    }
  }

  const playSection = (resourceId, sections, index = 0) => {
    const section = sections[index]
    if (!section?.audioUrl) {
      narrationState.value = { ...narrationState.value, playing: false, loading: false }
      return
    }

    if (audio) audio.pause()
    audio = new Audio(section.audioUrl)
    narrationState.value = {
      resourceId,
      loading: false,
      playing: true,
      sectionIndex: index,
      sections
    }

    audio.onended = () => {
      if (index + 1 < sections.length) {
        playSection(resourceId, sections, index + 1)
      } else {
        narrationState.value = { ...narrationState.value, playing: false }
      }
    }
    audio.onerror = () => {
      narrationState.value = { ...narrationState.value, playing: false, loading: false }
    }
    audio.play().catch(() => {
      narrationState.value = { ...narrationState.value, playing: false, loading: false }
    })
  }

  const toggleNarration = async resource => {
    const resourceId = getNarratableResourceId(resource)
    if (!resourceId) return

    if (narrationState.value.resourceId === resourceId && narrationState.value.playing) {
      if (audio) audio.pause()
      narrationState.value = { ...narrationState.value, playing: false }
      return
    }

    if (narrationState.value.resourceId === resourceId && audio && narrationState.value.sections.length) {
      await audio.play()
      narrationState.value = { ...narrationState.value, playing: true }
      return
    }

    stopCurrentAudio()
    narrationState.value = {
      resourceId,
      loading: true,
      playing: false,
      sectionIndex: 0,
      sections: []
    }

    try {
      let sections = normalizeSections(resource.narration)
      if (!sections.length) {
        const result = await narrateResource(resourceId)
        const data = unwrapData(result)
        sections = normalizeSections(data)
        resource.narration = data
      }

      if (!sections.length) {
        window.alert('这个资源暂时没有可播放的语音内容。')
        narrationState.value = { ...narrationState.value, loading: false }
        return
      }

      playSection(resourceId, sections, 0)
    } catch (error) {
      console.error('[Narration] generate/play failed:', error)
      window.alert(error?.response?.data?.detail || error?.message || '音频生成失败，请稍后再试。')
      narrationState.value = { ...narrationState.value, loading: false, playing: false }
    }
  }

  const isNarrationLoading = resource => {
    return narrationState.value.loading && narrationState.value.resourceId === getNarratableResourceId(resource)
  }

  const isNarrationPlaying = resource => {
    return narrationState.value.playing && narrationState.value.resourceId === getNarratableResourceId(resource)
  }

  return {
    narrationState,
    canNarrateResource,
    getNarratableResourceId,
    toggleNarration,
    isNarrationLoading,
    isNarrationPlaying,
    stopCurrentAudio
  }
}
