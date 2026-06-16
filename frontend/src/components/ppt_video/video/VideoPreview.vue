<template>
  <ResourceMediaFrame>
    <section class="video-preview-shell">
      <div class="video-stage">
        <VideoAmbientBackground
          :background-url="videoBackgroundUrl"
          :active="isPlaying"
        />

        <VideoStageInfo
          v-if="src"
          :chapter-count="chapters.length"
          :duration-label="durationLabel"
        />

        <video
          v-if="src"
          ref="videoRef"
          class="video-player"
          :src="src"
          :poster="posterUrl"
          :controls="hasStarted"
          preload="metadata"
          playsinline
          @loadeddata="captureFirstFrame"
          @loadedmetadata="syncVideoTime"
          @durationchange="syncVideoTime"
          @timeupdate="syncVideoTime"
          @play="hasStarted = true"
          @pause="isPlaying = false"
          @playing="isPlaying = true"
          @ended="handleVideoEnded"
        >
          您的浏览器不支持视频播放
        </video>

        <VideoPoster
          v-if="src && !hasStarted"
          :poster-url="posterUrl || videoBackgroundUrl"
          :title="title"
          :summary="summaryText"
          @play="playVideo"
        />

        <VideoWaveform
          v-if="!hasStarted"
          :active="isPlaying"
        />

        <p v-if="!src" class="video-empty">{{ fallbackText }}</p>
      </div>

      <aside class="video-side-panel">
        <VideoStatusBadge
          :is-playing="isPlaying"
          :has-started="hasStarted"
          :has-source="Boolean(src)"
        />
        <h3>{{ title || '未命名视频' }}</h3>
        <p>{{ summaryText }}</p>

        <VideoGlowProgress
          :current-time="currentTime"
          :duration="duration"
        />

        <VideoChapterList
          v-if="chapters.length"
          :chapters="chapters"
          :active-chapter-id="activeChapterId"
          @select="selectChapter"
        />

        <VideoTranscriptPanel
          v-if="transcriptParagraphs.length"
          :paragraphs="transcriptParagraphs"
        />
      </aside>
    </section>
  </ResourceMediaFrame>
</template>

<script setup>
import { computed, ref } from 'vue'
import ResourceMediaFrame from '../ppt/ResourceMediaFrame.vue'
import VideoAmbientBackground from './effects/VideoAmbientBackground.vue'
import VideoChapterList from './VideoChapterList.vue'
import VideoGlowProgress from './VideoGlowProgress.vue'
import VideoPoster from './VideoPoster.vue'
import VideoStageInfo from './VideoStageInfo.vue'
import VideoStatusBadge from './VideoStatusBadge.vue'
import VideoTranscriptPanel from './VideoTranscriptPanel.vue'
import VideoWaveform from './effects/VideoWaveform.vue'
import { selectVideoBackground } from './logic/videoAssets'

const props = defineProps({
  src: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: ''
  },
  fallbackText: {
    type: String,
    default: '暂无视频内容'
  },
  content: {
    type: String,
    default: ''
  }
})

const videoRef = ref(null)
const posterUrl = ref('')
const hasStarted = ref(false)
const isPlaying = ref(false)
const activeChapterId = ref('')
const currentTime = ref(0)
const duration = ref(0)

const cleanContent = computed(() => String(props.content || '').replace(/<!--[\s\S]*?-->/g, '').trim())

const videoBackgroundUrl = computed(() => selectVideoBackground({
  title: props.title,
  content: cleanContent.value
}))

const chapters = computed(() => {
  const lines = cleanContent.value.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  const headings = lines
    .map((line, index) => ({ line, index }))
    .filter(item => /^#{1,3}\s+/.test(item.line) || /^第[一二三四五六七八九十\d]+[章节讲]/.test(item.line))
    .slice(0, 8)

  if (headings.length) {
    return headings.map((item, index) => ({
      id: `chapter-${index}`,
      index,
      title: item.line.replace(/^#{1,3}\s+/, '').slice(0, 36)
    }))
  }

  return lines.slice(0, 4).map((line, index) => ({
    id: `chapter-${index}`,
    index,
    title: line.replace(/^[-*]\s+/, '').slice(0, 36) || `章节 ${index + 1}`
  }))
})

const transcriptParagraphs = computed(() => {
  const paragraphs = cleanContent.value
    .split(/\n{2,}|\r?\n(?=#{1,3}\s+)/)
    .map(text => text.replace(/^#{1,3}\s+/gm, '').trim())
    .filter(Boolean)
  return paragraphs.length ? paragraphs.slice(0, 8) : [props.fallbackText].filter(Boolean)
})

const summaryText = computed(() => {
  const text = String(props.content || props.fallbackText || '').replace(/\s+/g, ' ').trim()
  return text.length > 120 ? `${text.slice(0, 119)}...` : text || '点击封面开始播放课程视频。'
})

const formatTime = seconds => {
  if (!Number.isFinite(seconds) || seconds <= 0) return '00:00'
  const total = Math.floor(seconds)
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

const durationLabel = computed(() => formatTime(duration.value))

const captureFirstFrame = () => {
  if (posterUrl.value || !videoRef.value) return
  const video = videoRef.value
  try {
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth || 1280
    canvas.height = video.videoHeight || 720
    const context = canvas.getContext('2d')
    if (!context) return
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    posterUrl.value = canvas.toDataURL('image/jpeg', 0.78)
  } catch (error) {
    console.warn('视频首帧封面截取失败：', error)
  }
}

const syncVideoTime = () => {
  if (!videoRef.value) return
  currentTime.value = videoRef.value.currentTime || 0
  duration.value = Number.isFinite(videoRef.value.duration) ? videoRef.value.duration : 0
}

const handleVideoEnded = () => {
  isPlaying.value = false
  syncVideoTime()
}

const playVideo = async () => {
  if (!videoRef.value) return
  hasStarted.value = true
  try {
    await videoRef.value.play()
  } catch (error) {
    console.warn('视频播放启动失败：', error)
  }
}

const selectChapter = async chapter => {
  activeChapterId.value = chapter.id
  await playVideo()
}
</script>

<style scoped>
.video-preview-shell {
  width: 100%;
  height: 100%;
  min-height: 420px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 310px);
  gap: 18px;
  align-items: stretch;
}

.video-stage {
  position: relative;
  min-width: 0;
  min-height: 0;
  border-radius: 8px;
  overflow: hidden;
  background: #0f1f35;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}

.video-player {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  min-height: 420px;
  display: block;
  object-fit: contain;
  background: rgba(8, 18, 32, 0.58);
}

.video-side-panel {
  min-width: 0;
  min-height: 0;
  padding: 18px;
  border-radius: 8px;
  background: rgba(250, 250, 250, 0.86);
  border: 1px solid rgba(201, 220, 233, 0.7);
  color: #163f8f;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.video-side-panel h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.3;
}

.video-side-panel > p,
.video-empty {
  margin: 0;
  color: rgba(31, 51, 86, 0.72);
  line-height: 1.7;
}

.video-side-panel > p {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  overflow: hidden;
}

.video-empty {
  z-index: 2;
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  color: #c9dce9;
  text-align: center;
}

@media (max-width: 900px) {
  .video-preview-shell {
    grid-template-columns: 1fr;
  }

  .video-player,
  .video-stage {
    min-height: 280px;
  }
}
</style>
