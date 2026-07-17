<template>
  <main class="presentation-player">
    <header class="player-topbar">
      <button type="button" @click="goBack">返回</button>
      <div>
        <span>{{ returnFrom === 'path' ? '学习路径视频' : 'AI 学习视频' }}</span>
        <h1>{{ title }}</h1>
      </div>
      <VideoStatusBadge
        :is-playing="isPlaying"
        :has-started="hasStarted"
        :has-source="Boolean(activeSlide)"
      />
      <a v-if="presentationUrl" :href="presentationUrl" target="_blank" rel="noopener noreferrer">打开原始视频</a>
      <select class="theme-select" :value="activeTheme" @change="setTheme($event.target.value)">
        <option v-for="(t, key) in videoThemes" :key="key" :value="key">{{ t.label }}</option>
      </select>
    </header>

    <section class="player-stage" :style="themeStyles">
      <template v-if="activeSlide">
        <VideoAmbientBackground
          :background-url="videoBackgroundUrl"
          :active="isPlaying"
        />

        <div class="lesson-slide">
          <VideoSlideCanvas
            :slide="activeSlide"
            :slide-count="slides.length"
            :duration-label="durationLabel"
            :is-playing="isPlaying"
            :has-started="hasStarted"
            :background-url="videoBackgroundUrl"
            :timed-words="timedWords"
          >
            <template #progress>
              <VideoGlowProgress
                class="lesson-progress"
                :current-time="globalCurrentTime"
                :duration="totalDuration"
                :is-playing="isPlaying"
                :can-play="activeSlideReady"
                :markers="progressMarkers"
                :segments="progressSegments"
                @toggle-play="togglePlay"
                @seek="seekToGlobalTime"
              />
            </template>
          </VideoSlideCanvas>
          <div v-if="activeSlide?.isLocked" class="lesson-lock">
            <strong>片段制作中</strong>
            <span>音频尚未生成完成，完成后会自动解锁。</span>
          </div>
        </div>

        <audio
          ref="audioRef"
          :src="playableAudioUrl"
          preload="metadata"
          @loadedmetadata="syncAudioTime"
          @timeupdate="syncAudioTime"
          @play="handleAudioPlay"
          @pause="isPlaying = false"
          @ended="handleAudioEnded"
          @error="handleAudioError"
        ></audio>
      </template>

      <iframe
        v-else-if="presentationUrl"
        ref="frameRef"
        class="lesson-frame"
        :src="lessonHtml ? undefined : frameUrl"
        :srcdoc="lessonHtml || undefined"
        title="学习视频"
        allow="autoplay; fullscreen"
        @load="handleFrameLoad"
      ></iframe>

      <div v-else-if="presentationStatus === 'failed'" class="empty-state">视频生成失败</div>

      <div v-if="presentationStatus === 'generating'" class="loading-mask">
        正在等待后端写入完整视频...
      </div>

      <aside v-if="isPlaying" class="teacher-tip" aria-label="小知讲解提示">
        小知正在为你讲解
      </aside>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPresentation, resolveApiUrl } from '../api/apis'
import VideoAmbientBackground from '../components/ppt_video/video/effects/VideoAmbientBackground.vue'
import VideoGlowProgress from '../components/ppt_video/video/VideoGlowProgress.vue'
import VideoStatusBadge from '../components/ppt_video/video/VideoStatusBadge.vue'
import VideoSlideCanvas from '../components/ppt_video/video/slides/VideoSlideCanvas.vue'
import { selectVideoBackground } from '../components/ppt_video/video/logic/videoAssets'
import 'katex/dist/katex.min.css'

const route = useRoute()
const router = useRouter()
const frameRef = ref(null)
const audioRef = ref(null)
const activePresentationUrl = ref(resolveApiUrl(String(route.query.url || '')))
const frameVersion = ref(Date.now())
const presentationStatus = ref('loading')
const lessonHtml = ref('')
const presentationChapters = ref([])
const activeIndex = ref(0)
const currentTime = ref(0)
const duration = ref(0)
const knownDurations = ref({})
const hasStarted = ref(false)
const isPlaying = ref(false)
let audioPollTimer = 0
let silentPlaybackTimer = 0
let presentationPollTimer = 0
let returning = false
const failedAudioUrls = new Set()

const videoThemes = {
  dark_cinematic: {
    label: '暗夜影院',
    bg: '#081733',
    accent: '#5bc9bc',
    highlight: '#ffd166',
    text: '#ffffff',
    muted: 'rgba(235, 246, 255, 0.76)',
    cardBg: 'rgba(255,255,255,0.12)',
    border: 'rgba(255,255,255,0.14)'
  },
  light_academic: {
    label: '明亮学术',
    bg: '#f0f4f8',
    accent: '#2f7de1',
    highlight: '#e63946',
    text: '#1a2a3a',
    muted: 'rgba(26, 42, 58, 0.68)',
    cardBg: 'rgba(255,255,255,0.9)',
    border: 'rgba(22, 63, 143, 0.16)'
  },
  nature: {
    label: '自然绿意',
    bg: '#0d2818',
    accent: '#34d399',
    highlight: '#fbbf24',
    text: '#ecfdf5',
    muted: 'rgba(236, 253, 245, 0.72)',
    cardBg: 'rgba(255,255,255,0.08)',
    border: 'rgba(255,255,255,0.12)'
  }
}

const activeTheme = ref(localStorage.getItem('zhiban-video-theme') || 'dark_cinematic')

const themeStyles = computed(() => {
  const t = videoThemes[activeTheme.value] || videoThemes.dark_cinematic
  return {
    '--player-bg': t.bg,
    '--player-accent': t.accent,
    '--player-highlight': t.highlight,
    '--player-text': t.text,
    '--player-muted': t.muted,
    '--player-card-bg': t.cardBg,
    '--player-border': t.border
  }
})

const setTheme = theme => {
  activeTheme.value = theme
  localStorage.setItem('zhiban-video-theme', theme)
}

const presentationId = computed(() => String(route.query.id || '').trim())
const chatGroupId = computed(() => {
  const raw = route.query.chat_group_id || route.query.chatGroupId || route.query.conversationId
  return String(Array.isArray(raw) ? raw[0] : raw || '').trim()
})
const returnFrom = computed(() => String(route.query.from || '').trim())
const presentationUrl = computed(() => activePresentationUrl.value)
const title = computed(() => String(route.query.title || slides.value[0]?.title || 'AI 学习视频'))

const appendFrameVersion = url => {
  if (!url) return ''
  try {
    const parsed = new URL(url, window.location.origin)
    parsed.searchParams.set('_t', String(frameVersion.value))
    return parsed.toString()
  } catch {
    const joiner = String(url).includes('?') ? '&' : '?'
    return `${url}${joiner}_t=${frameVersion.value}`
  }
}

const frameUrl = computed(() => appendFrameVersion(activePresentationUrl.value))

const unwrapData = result => result?.data?.data ?? result?.data ?? result ?? {}

const plainText = value => String(value || '')
  .replace(/<!--[\s\S]*?-->/g, ' ')
  .replace(/<[^>]+>/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()

const formulaPattern = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\))/g

const extractFormulas = value => {
  const text = String(value || '')
  return (text.match(formulaPattern) || [])
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 3)
}

const withoutFormulas = value => String(value || '').replace(formulaPattern, ' ')

const normalizeStructuredItems = values => (Array.isArray(values) ? values : [])
  .map(item => {
    if (typeof item === 'string') return item
    return item?.text || item?.content || item?.title || ''
  })
  .map(item => plainText(withoutFormulas(item)))
  .filter(Boolean)

const slideItems = slide => {
  const structured = [
    ...normalizeStructuredItems(slide?.items),
    ...normalizeStructuredItems(slide?.blocks),
    ...normalizeStructuredItems(slide?.bullets)
  ]
  const unique = structured.filter((item, index, array) => array.indexOf(item) === index)
  if (unique.length) return unique.slice(0, 6)

  const lineItems = plainText(withoutFormulas(slide?.text || ''))
    .split(/\n+/)
    .map(item => item.replace(/^[-*•\d.、\s]+/, '').trim())
    .filter(item => item.length >= 4)
  return lineItems.slice(0, 6)
}

const slideFormulas = slide => [
  ...extractFormulas(slide?.formula || ''),
  ...extractFormulas(slide?.text || ''),
  ...extractFormulas(slide?.content_html || ''),
  ...extractFormulas((slide?.bullets || []).join('\n'))
].filter((item, index, array) => array.indexOf(item) === index).slice(0, 3)

const slides = computed(() => {
  const flattened = []
  presentationChapters.value.forEach((chapter, chapterIndex) => {
    const chapterTitle = chapter.title || `章节 ${chapterIndex + 1}`
    if (Array.isArray(chapter.slides) && chapter.slides.length) {
      chapter.slides.forEach((slide, slideIndex) => {
        const rawAudioUrl = slide.audio_url || slide.audioUrl || ''
        const wordTimestamps = slide.word_timestamps || slide.wordTimestamps || []
        const html = slide.content_html || ''
        const items = slideItems(slide)
        const formulas = slideFormulas(slide)
        const summary = plainText(withoutFormulas(slide.summary || slide.text || items.join('。') || html || chapterTitle))
        flattened.push({
          id: `slide-${chapterIndex}-${slideIndex}`,
          index: flattened.length,
          chapterTitle,
          title: slide.title || chapterTitle,
          layout: slide.layout || 'content',
          html,
          items,
          formulas,
          summary,
          subject: slide.subject || slide.discipline || chapter.subject || chapter.discipline || '',
          visual: slide.visual || slide.visual_hint || chapter.visual || null,
          theme: slide.theme || chapter.theme || '',
          audioUrl: resolveApiUrl(rawAudioUrl),
          isLocked: !rawAudioUrl,
          wordTimestamps,
          slideDurationMs: slide.duration_ms || slide.durationMs || 0
        })
      })
      return
    }

    const html = chapter.content_html || ''
    const formulas = extractFormulas(html)
    flattened.push({
      id: `slide-${chapterIndex}-0`,
      index: flattened.length,
      chapterTitle,
      title: chapterTitle,
      layout: chapter.type || 'content',
      html,
      items: [],
      formulas,
      summary: plainText(withoutFormulas(html || chapterTitle)),
      subject: chapter.subject || chapter.discipline || '',
      visual: chapter.visual || null,
      theme: chapter.theme || '',
      audioUrl: '',
      isLocked: true
    })
  })
  return flattened
})

const activeSlide = computed(() => slides.value[activeIndex.value] || null)
const activeSlideReady = computed(() => Boolean(activeSlide.value && !activeSlide.value.isLocked))
const activeAudioUrl = computed(() => activeSlide.value?.audioUrl || '')
const playableAudioUrl = ref('')
let playableAudioObjectUrl = ''
const videoBackgroundUrl = computed(() => selectVideoBackground({
  title: title.value,
  content: activeSlide.value?.summary || ''
}))

const getSlideDuration = slide => {
  const known = knownDurations.value[slide?.id]
  if (Number.isFinite(known) && known > 0) return known
  const declared = Number(slide?.slideDurationMs || 0) / 1000
  if (Number.isFinite(declared) && declared > 0) return declared
  const textLength = String(slide?.summary || '').length + (slide?.items || []).join('').length
  return Math.max(6, Math.min(18, Math.ceil(textLength / 34)))
}

const timelineSegments = computed(() => {
  let start = 0
  return slides.value.map((slide, index) => {
    const segmentDuration = getSlideDuration(slide)
    const segment = {
      id: slide.id,
      index,
      title: slide.title,
      locked: Boolean(slide.isLocked),
      start,
      duration: segmentDuration,
      end: start + segmentDuration
    }
    start += segmentDuration
    return segment
  })
})

const activeSegment = computed(() => timelineSegments.value[activeIndex.value] || null)
const totalDuration = computed(() => timelineSegments.value.at(-1)?.end || duration.value || 0)
const globalCurrentTime = computed(() => (activeSegment.value?.start || 0) + currentTime.value)
const progressMarkers = computed(() => timelineSegments.value
  .filter(segment => totalDuration.value > 0 && segment.start > 0)
  .map(segment => ({
    id: segment.id,
    label: segment.title,
    time: segment.start,
    percent: (segment.start / totalDuration.value) * 100,
    locked: segment.locked
  })))

const progressSegments = computed(() => timelineSegments.value
  .filter(segment => totalDuration.value > 0)
  .map(segment => ({
    id: segment.id,
    label: segment.title,
    start: segment.start,
    end: segment.end,
    locked: segment.locked,
    left: (segment.start / totalDuration.value) * 100,
    width: (segment.duration / totalDuration.value) * 100
  })))

const chapterNav = computed(() => slides.value.map(slide => ({
  id: slide.id,
  index: slide.index,
  title: slide.title
})))

const visualTerms = computed(() => {
  const text = [
    activeSlide.value?.title,
    ...(activeSlide.value?.items || [])
  ].join(' ')
  const english = text.match(/[A-Za-z][A-Za-z\s&-]{2,}/g) || []
  const chinese = text.match(/[\u4e00-\u9fa5]{2,6}/g) || []
  return [...english, ...chinese]
    .map(item => item.trim().replace(/[，。；：、,.]/g, ''))
    .filter(Boolean)
    .filter((item, index, array) => array.indexOf(item) === index)
    .slice(0, 8)
})

// 将词级 word_timestamps 插值为字级时间戳：每个词的时长均匀分给每个字
// 过滤标点/空白 — renderKaraokeHTML 也不消耗这些字符，需保持一致
const CHAR_PUNCT_RE = /^[\s，。、；：！？,.;:!?]+$/
const charTimestamps = computed(() => {
  const wts = activeSlide.value?.wordTimestamps
  if (!wts || !wts.length) return []
  const chars = []
  for (const wt of wts) {
    const segments = [...wt.text]
    const validSegs = segments.filter(s => !CHAR_PUNCT_RE.test(s))
    if (!validSegs.length) continue
    const perCharMs = wt.duration_ms / validSegs.length
    for (let i = 0; i < validSegs.length; i++) {
      chars.push({
        text: validSegs[i],
        offset_ms: wt.offset_ms + i * perCharMs,
        duration_ms: perCharMs
      })
    }
  }
  return chars
})

const activeCharIndex = computed(() => {
  const cts = charTimestamps.value
  if (!cts.length) return -1
  const ms = currentTime.value * 1000
  let lo = 0, hi = cts.length
  while (lo < hi) {
    const mid = (lo + hi) >>> 1
    if (cts[mid].offset_ms <= ms) lo = mid + 1
    else hi = mid
  }
  return lo - 1
})

const timedWords = computed(() => {
  const cts = charTimestamps.value
  if (!cts.length) {
    if (activeSlide.value && activeSlide.value.audioUrl) {
      console.warn('[Karaoke] 有音频但 wordTimestamps 为空:', activeSlide.value.id, activeSlide.value.title?.slice(0, 20))
    }
    return []
  }
  const currentIdx = activeCharIndex.value
  return cts.map((ct, i) => ({
    text: ct.text,
    isDone: i <= currentIdx,
    isCurrent: i === currentIdx + 1
  }))
})

const formatTime = seconds => {
  if (!Number.isFinite(seconds) || seconds <= 0) return '00:00'
  const total = Math.floor(seconds)
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

const durationLabel = computed(() => formatTime(totalDuration.value))

const stopLessonMedia = () => {
  window.clearInterval(silentPlaybackTimer)
  silentPlaybackTimer = 0
  audioRef.value?.pause?.()
  try {
    const win = frameRef.value?.contentWindow
    const doc = frameRef.value?.contentDocument || win?.document
    if (win?.currentAudio) win.currentAudio.pause?.()
    if (typeof win?.pauseAudio === 'function') win.pauseAudio()
    Array.from(doc?.querySelectorAll('audio, video') || []).forEach(media => media.pause?.())
  } catch {}
  isPlaying.value = false
}

const goBack = () => {
  if (returning) return
  returning = true
  stopLessonMedia()
  if (returnFrom.value === 'path') {
    router.push({ name: 'learningPath' })
    return
  }
  router.push({
    name: 'chat',
    query: chatGroupId.value ? { chat_group_id: chatGroupId.value } : {}
  })
}

const getBackendBase = url => {
  try {
    return new URL('/', url).toString()
  } catch {
    return '/'
  }
}

const prepareLessonHtml = (html, url) => {
  const baseTag = `<base href="${getBackendBase(url)}">`
  if (/<head[^>]*>/i.test(html)) {
    return html.replace(/<head[^>]*>/i, match => `${match}${baseTag}`)
  }
  return `${baseTag}${html}`
}

const loadLessonHtml = async () => {
  if (!activePresentationUrl.value || slides.value.length) return
  try {
    const token = localStorage.getItem('token')
    const response = await fetch(appendFrameVersion(activePresentationUrl.value), {
      headers: {
        'ngrok-skip-browser-warning': 'true',
        ...(token ? { token } : {})
      }
    })
    if (!response.ok) throw new Error(`HTML load failed: ${response.status}`)
    const html = await response.text()
    lessonHtml.value = prepareLessonHtml(html, activePresentationUrl.value)
  } catch (error) {
    console.warn('[VideoPlayer] load html as srcdoc failed, fallback to iframe src:', error)
    lessonHtml.value = ''
  }
}

const clearPlayableAudioUrl = () => {
  if (playableAudioObjectUrl) {
    URL.revokeObjectURL(playableAudioObjectUrl)
    playableAudioObjectUrl = ''
  }
  playableAudioUrl.value = ''
}

const loadPlayableAudio = async url => {
  clearPlayableAudioUrl()
  if (!url) return

  const expectedUrl = url
  try {
    const token = localStorage.getItem('token')
    const response = await fetch(url, {
      headers: {
        'ngrok-skip-browser-warning': 'true',
        ...(token ? { token } : {})
      }
    })
    if (!response.ok) throw new Error(`Audio load failed: ${response.status}`)

    const contentType = response.headers.get('content-type') || ''
    if (contentType && !/audio|mpeg|octet-stream/i.test(contentType)) {
      throw new Error(`Unexpected audio content-type: ${contentType}`)
    }

    const blob = await response.blob()
    if (activeAudioUrl.value !== expectedUrl) return
    playableAudioObjectUrl = URL.createObjectURL(blob)
    playableAudioUrl.value = playableAudioObjectUrl
    await nextTick()
    syncAudioTime()
    if (isPlaying.value) {
      window.clearInterval(silentPlaybackTimer)
      silentPlaybackTimer = 0
      audioRef.value?.play?.().catch(error => {
        console.warn('[VideoPlayer] blob audio play failed:', error)
        startSilentPlayback()
      })
    }
  } catch (error) {
    console.warn('[VideoPlayer] audio fetch failed, fallback to direct src:', error)
    if (activeAudioUrl.value === expectedUrl) {
      playableAudioUrl.value = expectedUrl
    }
  }
}

const syncAudioTime = () => {
  if (!audioRef.value) return
  currentTime.value = audioRef.value.currentTime || 0
  duration.value = Number.isFinite(audioRef.value.duration) ? audioRef.value.duration : getSlideDuration(activeSlide.value)
  if (activeSlide.value?.id && Number.isFinite(audioRef.value.duration) && audioRef.value.duration > 0) {
    knownDurations.value = {
      ...knownDurations.value,
      [activeSlide.value.id]: audioRef.value.duration
    }
  }
}

const handleAudioPlay = () => {
  window.clearInterval(silentPlaybackTimer)
  silentPlaybackTimer = 0
  hasStarted.value = true
  isPlaying.value = true
}

const startSilentPlayback = () => {
  hasStarted.value = true
  isPlaying.value = true
  window.clearInterval(silentPlaybackTimer)
  silentPlaybackTimer = window.setInterval(() => {
    const nextTime = currentTime.value + 0.25
    const currentDuration = getSlideDuration(activeSlide.value)
    if (nextTime >= currentDuration) {
      currentTime.value = currentDuration
      handleAudioEnded()
      return
    }
    currentTime.value = nextTime
  }, 250)
}

const handleAudioError = () => {
  const url = activeAudioUrl.value || ''
  if (url && !failedAudioUrls.has(url)) {
    failedAudioUrls.add(url)
    console.warn('[VideoPlayer] audio load failed, fallback to silent timeline:', url)
  }
  if (isPlaying.value || hasStarted.value) startSilentPlayback()
}

const handleAudioEnded = () => {
  isPlaying.value = false
  syncAudioTime()
  if (activeIndex.value < slides.value.length - 1) nextSlide(true)
}

const togglePlay = async () => {
  hasStarted.value = true
  if (!activeSlideReady.value) return
  if (!audioRef.value || !activeAudioUrl.value || !playableAudioUrl.value) {
    if (isPlaying.value) {
      window.clearInterval(silentPlaybackTimer)
      silentPlaybackTimer = 0
      isPlaying.value = false
    } else {
      startSilentPlayback()
    }
    return
  }
  if (isPlaying.value) {
    window.clearInterval(silentPlaybackTimer)
    silentPlaybackTimer = 0
    audioRef.value.pause()
    isPlaying.value = false
    return
  }
  try {
    await audioRef.value.play()
  } catch (error) {
    console.warn('[VideoPlayer] audio play failed:', error)
    startSilentPlayback()
  }
}

const setSlide = async (index, offset = 0) => {
  const targetIndex = Math.min(Math.max(index, 0), slides.value.length - 1)
  const target = slides.value[targetIndex]
  if (!target || target.isLocked) return false
  stopLessonMedia()
  activeIndex.value = targetIndex
  currentTime.value = Math.max(0, offset)
  duration.value = getSlideDuration(activeSlide.value)
  await nextTick()
  syncAudioTime()
  if (audioRef.value && Number.isFinite(offset) && offset > 0) {
    audioRef.value.currentTime = Math.min(offset, audioRef.value.duration || getSlideDuration(activeSlide.value))
    syncAudioTime()
  }
  return true
}

const prevSlide = () => setSlide(activeIndex.value - 1)
const nextSlide = autoplay => {
  const nextIndex = slides.value.findIndex((slide, index) => index > activeIndex.value && !slide.isLocked)
  if (nextIndex < 0) return
  setSlide(nextIndex).then(ok => {
    if (ok && autoplay) togglePlay()
  })
}

const seekToGlobalTime = async targetTime => {
  if (!timelineSegments.value.length) return
  const clamped = Math.min(Math.max(Number(targetTime) || 0, 0), totalDuration.value)
  const segment = timelineSegments.value.find(item => clamped >= item.start && clamped < item.end)
    || timelineSegments.value.at(-1)
  if (!segment || segment.locked) return
  const offset = Math.max(0, clamped - segment.start)
  const shouldResume = isPlaying.value
  const ok = await setSlide(segment.index, offset)
  if (ok && shouldResume) togglePlay()
}

const selectNavSlide = chapter => {
  const index = slides.value.findIndex(slide => slide.id === chapter.id)
  if (index >= 0) setSlide(index)
}

const handleFrameLoad = () => {
  window.clearInterval(audioPollTimer)
  audioPollTimer = 0
}

const refreshPresentationStatus = async () => {
  if (!presentationId.value) {
    presentationStatus.value = activePresentationUrl.value ? 'ready' : 'failed'
    loadLessonHtml()
    return
  }

  try {
    const data = unwrapData(await getPresentation(presentationId.value))
    presentationStatus.value = data.status || 'ready'
    if (data.file_url || data.fileUrl) {
      activePresentationUrl.value = resolveApiUrl(data.file_url || data.fileUrl)
      loadLessonHtml()
    }
    if (Array.isArray(data.chapters)) {
      presentationChapters.value = data.chapters
      lessonHtml.value = ''
    }
    const allAudioReady = data.chapters?.length && data.chapters.every(ch => ch.is_audio_ready)
    if (presentationStatus.value === 'failed' || (presentationStatus.value === 'ready' && allAudioReady)) {
      window.clearInterval(presentationPollTimer)
      presentationPollTimer = 0
    }
  } catch (error) {
    console.warn('[VideoPlayer] status check failed:', error)
    presentationStatus.value = activePresentationUrl.value ? 'ready' : 'failed'
    loadLessonHtml()
  }
}

watch(activeAudioUrl, newUrl => {
  currentTime.value = 0
  duration.value = 0
  loadPlayableAudio(newUrl)
  nextTick(syncAudioTime)
  // 当音频 URL 从无到有时，从静音模式切换到真实音频播放
}, { immediate: true })

watch(slides, nextSlides => {
  if (activeIndex.value >= nextSlides.length) activeIndex.value = 0
})

onMounted(() => {
  refreshPresentationStatus()
  loadLessonHtml()
  if (presentationId.value) {
    presentationPollTimer = window.setInterval(refreshPresentationStatus, 1800)
  }
})

onBeforeUnmount(() => {
  stopLessonMedia()
  clearPlayableAudioUrl()
  window.clearInterval(audioPollTimer)
  window.clearInterval(silentPlaybackTimer)
  silentPlaybackTimer = 0
  window.clearInterval(presentationPollTimer)
  presentationPollTimer = 0
})
</script>

<style scoped>
.presentation-player {
  width: 100%;
  height: 100vh;
  padding: 18px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
  color: #163f8f;
}

.player-topbar {
  min-height: 62px;
  padding: 10px 14px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 14px 34px rgba(22, 63, 143, 0.08);
  display: flex;
  align-items: center;
  gap: 14px;
}

.player-topbar div {
  min-width: 0;
  flex: 1;
}

.player-topbar span {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.player-topbar h1 {
  margin: 2px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 18px;
}

.player-topbar button,
.player-topbar a {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 8px;
  background: #fff;
  color: #163f8f;
  font: inherit;
  font-weight: 900;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.player-stage {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 8px;
  background: var(--player-bg, #081733);
  box-shadow: 0 18px 44px rgba(22, 63, 143, 0.14);
  display: block;
  padding: 16px;
}

.lesson-slide {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: 8px;
  overflow: hidden;
  background: color-mix(in srgb, var(--player-bg, #081733) 58%, transparent);
  box-shadow: inset 0 0 0 1px var(--player-border, rgba(255, 255, 255, 0.08));
}

.lesson-slide__content {
  position: absolute;
  z-index: 2;
  inset: 82px 54px 104px;
  color: var(--player-text, #fff);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 390px);
  grid-template-rows: minmax(0, 0.72fr) minmax(160px, 0.9fr);
  grid-template-areas:
    "hero visual"
    "cards visual";
  gap: 22px 28px;
  align-items: stretch;
}

.lesson-hero {
  grid-area: hero;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: end;
  gap: 14px;
}

.lesson-slide__kicker {
  width: fit-content;
  min-height: 30px;
  padding: 0 11px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  display: inline-flex;
  align-items: center;
  color: rgba(215, 242, 246, 0.92);
  font-size: 12px;
  font-weight: 900;
  backdrop-filter: blur(10px);
}

.lesson-slide h2 {
  max-width: 760px;
  margin: 0;
  font-size: clamp(30px, 3.8vw, 56px);
  line-height: 1.12;
  text-shadow: 0 4px 24px rgba(0, 0, 0, 0.34);
}

.lesson-slide h2::after {
  content: "";
  display: block;
  width: min(520px, 70%);
  height: 4px;
  margin-top: 20px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--player-highlight, #ffd166), var(--player-accent, #5bc9bc), transparent);
}

.lesson-hero p {
  max-width: 720px;
  margin: 0;
  color: var(--player-muted, rgba(235, 246, 255, 0.76));
  font-size: clamp(15px, 1.2vw, 19px);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}

.lesson-card-wall {
  grid-area: cards;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
  align-content: stretch;
}

.lesson-card-wall article {
  min-height: 0;
  padding: 16px 18px;
  border: 1px solid var(--player-border, rgba(220, 240, 255, 0.18));
  border-radius: 8px;
  background: linear-gradient(135deg, var(--player-card-bg, rgba(255, 255, 255, 0.12)), rgba(255, 255, 255, 0.05));
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  backdrop-filter: blur(12px);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.16);
}

.lesson-card-wall article.featured {
  grid-column: auto;
  min-height: 0;
  background:
    radial-gradient(circle at 88% 22%, var(--player-highlight, rgba(255, 209, 102, 0.18)), transparent 36%),
    linear-gradient(135deg, color-mix(in srgb, var(--player-accent, #5bc9bc) 18%, transparent), rgba(255, 255, 255, 0.07));
}

.lesson-card-wall b {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--player-highlight, #ffd166), var(--player-accent, #5bc9bc));
  color: #12223a;
  display: grid;
  place-items: center;
}

.lesson-card-wall span,
.lesson-slide__empty {
  color: var(--player-muted, rgba(235, 246, 255, 0.86));
  font-size: clamp(15px, 1.18vw, 20px);
  line-height: 1.48;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.lesson-card-wall article.featured span {
  font-size: clamp(17px, 1.38vw, 22px);
}

.lesson-visual-board {
  grid-area: visual;
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--player-border, rgba(220, 240, 255, 0.18));
  border-radius: 8px;
  background:
    radial-gradient(circle at 50% 42%, var(--player-highlight, rgba(255, 209, 102, 0.16)), transparent 32%),
    linear-gradient(145deg, var(--player-card-bg, rgba(255, 255, 255, 0.11)), rgba(255, 255, 255, 0.045));
  box-shadow: 0 20px 52px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(14px);
}

.lesson-orbit {
  position: absolute;
  left: 50%;
  top: 43%;
  width: min(260px, 62%);
  aspect-ratio: 1;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  transform: translate(-50%, -50%);
}

.lesson-orbit::before,
.lesson-orbit::after {
  content: "";
  position: absolute;
  inset: 14%;
  border: 1px solid rgba(91, 201, 188, 0.28);
  border-radius: inherit;
}

.lesson-orbit::after {
  inset: 31%;
  border-color: color-mix(in srgb, var(--player-highlight, #ffd166) 34%, transparent);
}

.lesson-orbit span {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--player-highlight, #ffd166), var(--player-accent, #5bc9bc));
  transform:
    rotate(calc(var(--dot) * 60deg))
    translateX(118px)
    rotate(calc(var(--dot) * -60deg));
  box-shadow: 0 0 24px rgba(91, 201, 188, 0.32);
}

.lesson-term-cloud {
  position: absolute;
  left: 22px;
  right: 22px;
  bottom: 22px;
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.lesson-term-cloud b {
  max-width: 100%;
  min-height: 30px;
  padding: 0 11px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.13);
  color: rgba(240, 250, 255, 0.9);
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
}

.lesson-formula-stack {
  position: absolute;
  inset: 28px;
  display: grid;
  align-content: center;
  gap: 16px;
}

.lesson-formula {
  min-height: 72px;
  padding: 18px 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(5, 16, 30, 0.32);
  color: #fff;
  display: grid;
  place-items: center;
  overflow: hidden;
  font-size: clamp(20px, 2vw, 32px);
}

.lesson-formula :deep(.katex-display) {
  margin: 0;
}

.lesson-formula :deep(.katex) {
  max-width: 100%;
  overflow: hidden;
  font-size: 1em;
}

.lesson-controls {
  position: absolute;
  z-index: 4;
  left: 34px;
  bottom: 54px;
  display: flex;
  gap: 10px;
}

.lesson-controls button {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-weight: 900;
  cursor: pointer;
  backdrop-filter: blur(10px);
}

.lesson-controls button.primary {
  background: linear-gradient(135deg, #2f7de1, var(--player-accent, #5bc9bc));
}

.lesson-controls button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.lesson-progress {
  position: absolute;
  z-index: 4;
  left: 34px;
  right: 34px;
  bottom: 18px;
}

.lesson-lock {
  position: absolute;
  z-index: 6;
  left: 50%;
  bottom: 76px;
  min-width: min(360px, calc(100% - 48px));
  padding: 12px 16px;
  border: 1px solid rgba(251, 191, 36, 0.56);
  border-radius: 8px;
  background: rgba(18, 24, 38, 0.78);
  color: #fff7d6;
  display: grid;
  gap: 4px;
  text-align: center;
  transform: translateX(-50%);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(14px);
  pointer-events: none;
}

.lesson-lock strong {
  font-size: 14px;
}

.lesson-lock span {
  color: rgba(255, 247, 214, 0.82);
  font-size: 12px;
  font-weight: 800;
}

.lesson-side {
  display: none;
  position: relative;
  z-index: 2;
  min-width: 0;
  min-height: 0;
  padding: 18px;
  border-radius: 8px;
  background: rgba(250, 250, 250, 0.9);
  border: 1px solid rgba(201, 220, 233, 0.7);
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.lesson-side h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.3;
}

.lesson-side > p {
  margin: 0;
  color: rgba(31, 51, 86, 0.72);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  overflow: hidden;
}

.lesson-frame {
  grid-column: 1 / -1;
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
}

.empty-state,
.loading-mask {
  position: relative;
  z-index: 3;
}

.empty-state {
  grid-column: 1 / -1;
  height: 100%;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 900;
}

.loading-mask {
  position: absolute;
  left: 50%;
  top: 18px;
  min-height: 38px;
  padding: 0 16px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  transform: translateX(-50%);
  font-size: 13px;
  font-weight: 900;
  box-shadow: 0 12px 28px rgba(22, 63, 143, 0.14);
}

.teacher-pet {
  position: absolute;
  right: clamp(24px, 4vw, 54px);
  bottom: clamp(18px, 3vw, 34px);
  z-index: 5;
  width: clamp(104px, 11vw, 170px);
  pointer-events: none;
  filter: drop-shadow(0 18px 26px rgba(0, 0, 0, 0.24));
}

.teacher-pet__bubble {
  width: max-content;
  max-width: 190px;
  margin: 0 auto 8px;
  padding: 8px 11px;
  border: 1px solid rgba(201, 220, 233, 0.86);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.93);
  display: grid;
  gap: 2px;
  text-align: center;
}

.teacher-pet__bubble strong {
  font-size: 13px;
}

.teacher-pet__bubble span {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.teacher-pet__body {
  position: relative;
  animation: teacher-idle 2.6s ease-in-out infinite;
}

.teacher-pet.speaking .teacher-pet__body {
  animation: teacher-talk 0.7s ease-in-out infinite;
}

.teacher-pet__body img {
  display: block;
  position: relative;
  z-index: 2;
  width: 100%;
  aspect-ratio: 1;
  object-fit: contain;
  user-select: none;
}

.teacher-pet__mouth {
  position: absolute;
  left: 44.5%;
  top: 41%;
  z-index: 4;
  width: 14%;
  height: 7%;
  border-radius: 999px;
  background: radial-gradient(circle at 52% 42%, rgba(245, 252, 255, 0.46), rgba(228, 246, 255, 0.32) 52%, transparent);
  transform: translate(-50%, -50%);
}

.teacher-pet.speaking .teacher-pet__mouth {
  animation: mouth-patch-talk 0.52s ease-in-out infinite;
}

@keyframes teacher-idle {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

@keyframes teacher-talk {
  0%, 100% { transform: translateY(0) rotate(-1deg); }
  50% { transform: translateY(-6px) rotate(1.4deg); }
}

.theme-select {
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 8px;
  background: #fff;
  color: #163f8f;
  font: inherit;
  font-weight: 800;
  font-size: 13px;
  cursor: pointer;
}

.lesson-karaoke {
  max-width: 720px;
  max-height: 4.8em;
  margin-top: 6px;
  font-size: clamp(17px, 1.4vw, 22px);
  line-height: 1.6;
  display: flex;
  flex-wrap: wrap;
  gap: 0 0.3em;
  overflow: hidden;
}

.presentation-player :deep(.karaoke-word) {
  position: relative;
  z-index: 30 !important;
  display: inline;
  opacity: 0.36;
  transition: opacity 0.1s ease, background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
  border-radius: 4px;
  padding: 0 2px;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}

.presentation-player :deep(.karaoke-word.is-done) {
  opacity: 1;
  color: var(--video-text, var(--player-text, #fff));
}

.presentation-player :deep(.karaoke-word.is-current) {
  opacity: 1;
  color: #e63946 !important;
  background: transparent !important;
  font-weight: 900;
  text-shadow:
    0 0 1px rgba(255, 255, 255, 0.72),
    0 0 14px rgba(230, 57, 70, 0.42);
  box-shadow: none;
}

@keyframes mouth-patch-talk {
  0%, 100% { transform: translate(-50%, -50%) scaleY(1); }
  50% { transform: translate(-50%, -50%) scaleY(1.08); }
}

@media (max-width: 980px) {
  .lesson-slide__content {
    inset: 72px 24px 104px;
    grid-template-columns: 1fr;
    grid-template-rows: auto auto minmax(160px, 1fr);
    grid-template-areas:
      "hero"
      "cards"
      "visual";
  }

  .lesson-card-wall {
    grid-template-columns: 1fr;
  }

  .lesson-card-wall article.featured {
    grid-column: auto;
  }

  .lesson-visual-board {
    min-height: 160px;
  }

  .teacher-pet {
    right: 18px;
    width: 96px;
  }
}
</style>
