<template>
  <main class="presentation-player">
    <header class="player-topbar">
      <button type="button" @pointerdown.prevent.stop="goBack" @click.prevent.stop="goBack">返回</button>
      <div>
        <span>Dynamic Lesson</span>
        <h1>{{ title }}</h1>
      </div>
      <span class="player-status" :class="presentationStatus">{{ statusText }}</span>
      <a v-if="presentationUrl" :href="presentationUrl" target="_blank" rel="noopener noreferrer">新窗口打开</a>
    </header>

    <section class="player-stage">
      <iframe
        v-if="presentationUrl"
        ref="frameRef"
        class="lesson-frame"
        :src="lessonHtml ? undefined : frameUrl"
        :srcdoc="lessonHtml || undefined"
        title="动态课件"
        allow="autoplay; fullscreen"
        @load="handleFrameLoad"
      ></iframe>
      <div v-else class="empty-state">没有找到课件地址</div>
      <div v-if="presentationStatus === 'generating'" class="loading-mask">
        正在等后端写入完整课件...
      </div>

      <aside class="teacher-pet" :class="{ speaking: isSpeaking }" aria-label="小知讲师">
        <div class="teacher-pet__bubble">
          <strong>小知讲师</strong>
          <span>{{ isSpeaking ? '正在讲解' : '小知待命' }}</span>
        </div>
        <div class="teacher-pet__body">
          <img :src="petImage" alt="" draggable="false" />
          <span class="teacher-pet__mouth"></span>
        </div>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPresentation, resolveApiUrl } from '../api/apis'
import petImage from '../assets/pic/zhiban-pet-base.png'

const route = useRoute()
const router = useRouter()
const frameRef = ref(null)
const isSpeaking = ref(false)
const activePresentationUrl = ref(resolveApiUrl(String(route.query.url || '')))
const frameVersion = ref(Date.now())
const presentationStatus = ref('loading')
const lessonHtml = ref('')
let audioPollTimer = 0
let presentationPollTimer = 0
let returning = false

const presentationId = computed(() => String(route.query.id || '').trim())
const chatGroupId = computed(() => {
  const raw = route.query.chat_group_id || route.query.chatGroupId || route.query.conversationId
  return String(Array.isArray(raw) ? raw[0] : raw || '').trim()
})
const presentationUrl = computed(() => activePresentationUrl.value)
const frameUrl = computed(() => {
  if (!activePresentationUrl.value) return ''
  const joiner = activePresentationUrl.value.includes('?') ? '&' : '?'
  return `${activePresentationUrl.value}${joiner}v=${frameVersion.value}`
})
const title = computed(() => String(route.query.title || '动态课件'))
const statusText = computed(() => {
  if (presentationStatus.value === 'ready') return '已完成'
  if (presentationStatus.value === 'failed') return '生成失败'
  if (presentationStatus.value === 'generating') return '生成中'
  return presentationId.value ? '检查中' : '预览'
})

const stopLessonMedia = () => {
  try {
    const win = frameRef.value?.contentWindow
    const doc = frameRef.value?.contentDocument || win?.document
    if (win?.currentAudio) win.currentAudio.pause?.()
    if (typeof win?.pauseAudio === 'function') win.pauseAudio()
    Array.from(doc?.querySelectorAll('audio, video') || []).forEach(media => {
      media.pause?.()
    })
  } catch {
    // Cross-origin fallback: srcdoc lessons are controllable, remote iframes may not be.
  }
}

const goBack = () => {
  if (returning) return
  returning = true
  stopLessonMedia()
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
  const bridgeScript = `
<script>
(function () {
  function notify() {
    try {
      window.parent.postMessage({
        type: 'zhiban:presentation-speaking',
        speaking: Boolean(window.isPlaying || (window.currentAudio && !window.currentAudio.paused && !window.currentAudio.ended))
      }, '*');
    } catch (e) {}
  }
  setInterval(notify, 160);
  document.addEventListener('click', function () { setTimeout(notify, 0); }, true);
})();
<\/script>`

  if (/<head[^>]*>/i.test(html)) {
    return html.replace(/<head[^>]*>/i, match => `${match}${baseTag}${bridgeScript}`)
  }

  return `${baseTag}${bridgeScript}${html}`
}

const loadLessonHtml = async () => {
  if (!activePresentationUrl.value) return

  try {
    const joiner = activePresentationUrl.value.includes('?') ? '&' : '?'
    const response = await fetch(`${activePresentationUrl.value}${joiner}v=${frameVersion.value}`)
    if (!response.ok) throw new Error(`HTML load failed: ${response.status}`)
    const html = await response.text()
    lessonHtml.value = prepareLessonHtml(html, activePresentationUrl.value)
  } catch (error) {
    console.warn('[PresentationPlayer] load html as srcdoc failed, fallback to iframe src:', error)
    lessonHtml.value = ''
  }
}

const detectSpeaking = () => {
  try {
    const win = frameRef.value?.contentWindow
    const doc = frameRef.value?.contentDocument || win?.document
    const currentAudio = win?.currentAudio
    const audios = Array.from(doc?.querySelectorAll('audio') || [])
    const windowAudioPlaying = Boolean(
      win?.isPlaying ||
      (currentAudio && !currentAudio.paused && !currentAudio.ended)
    )
    const domAudioPlaying = audios.some(audio => !audio.paused && !audio.ended)
    isSpeaking.value = windowAudioPlaying || domAudioPlaying
  } catch {
    isSpeaking.value = false
  }
}

const handleFrameLoad = () => {
  window.clearInterval(audioPollTimer)
  detectSpeaking()
  audioPollTimer = window.setInterval(detectSpeaking, 180)
}

const handleLessonMessage = event => {
  if (event?.data?.type !== 'zhiban:presentation-speaking') return
  isSpeaking.value = Boolean(event.data.speaking)
}

const unwrapData = result => result?.data?.data ?? result?.data ?? result ?? {}

const refreshPresentationStatus = async () => {
  if (!presentationId.value) {
    presentationStatus.value = activePresentationUrl.value ? 'ready' : 'failed'
    return
  }

  try {
    const data = unwrapData(await getPresentation(presentationId.value))
    const nextStatus = data.status || (activePresentationUrl.value ? 'ready' : 'generating')
    presentationStatus.value = nextStatus
    if (data.file_url || data.fileUrl) {
      activePresentationUrl.value = resolveApiUrl(data.file_url || data.fileUrl)
    }
    if (nextStatus === 'ready' || nextStatus === 'failed') {
      frameVersion.value = Date.now()
      if (nextStatus === 'ready') {
        loadLessonHtml()
      }
    }
    // 只要还有章节音频未就绪，就继续轮询刷新 HTML
    const chapters = Array.isArray(data.chapters) ? data.chapters : []
    const allAudioReady = chapters.length > 0 && chapters.every(ch => ch.is_audio_ready)
    if (nextStatus === 'failed' || (nextStatus === 'ready' && allAudioReady)) {
      window.clearInterval(presentationPollTimer)
      presentationPollTimer = 0
    }
  } catch (error) {
    console.warn('[PresentationPlayer] status check failed:', error)
    if (activePresentationUrl.value) {
      presentationStatus.value = 'ready'
    } else {
      presentationStatus.value = 'failed'
    }
  }
}

onMounted(() => {
  window.addEventListener('message', handleLessonMessage)
  refreshPresentationStatus()
  loadLessonHtml()
  if (presentationId.value) {
    presentationPollTimer = window.setInterval(refreshPresentationStatus, 1800)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('message', handleLessonMessage)
  window.clearInterval(audioPollTimer)
  window.clearInterval(presentationPollTimer)
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
  background: rgba(255, 255, 255, 0.88);
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

.player-status {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(237, 249, 252, 0.82);
  color: #5f8fc3;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.player-status.ready {
  background: rgba(221, 248, 232, 0.9);
  color: #2f7d57;
}

.player-status.failed {
  background: rgba(255, 230, 230, 0.92);
  color: #b24141;
}

.player-stage {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 8px;
  background: #081733;
  box-shadow: 0 18px 44px rgba(22, 63, 143, 0.14);
}

.lesson-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
}

.empty-state {
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
  z-index: 4;
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
  right: clamp(16px, 3vw, 34px);
  bottom: clamp(16px, 3vw, 34px);
  z-index: 5;
  width: clamp(130px, 15vw, 210px);
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
  background:
    radial-gradient(circle at 52% 42%, rgba(245, 252, 255, 0.46), rgba(228, 246, 255, 0.32) 52%, rgba(208, 237, 252, 0.08) 76%, transparent);
  filter: blur(0.35px);
  transform: translate(-50%, -50%);
  opacity: 1;
}

.teacher-pet__mouth::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 52%;
  width: 28%;
  height: 24%;
  border: 1.5px solid rgba(48, 147, 214, 0.62);
  border-radius: 999px;
  background: rgba(57, 157, 220, 0.16);
  transform: translate(-50%, -50%) scaleY(0.52);
}

.teacher-pet.speaking .teacher-pet__mouth {
  animation: mouth-patch-talk 0.52s ease-in-out infinite;
}

.teacher-pet.speaking .teacher-pet__mouth::after {
  animation: mouth-talk 0.52s ease-in-out infinite;
}

@keyframes teacher-idle {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

@keyframes teacher-talk {
  0%, 100% { transform: translateY(0) rotate(-1deg); }
  50% { transform: translateY(-6px) rotate(1.4deg); }
}

@keyframes mouth-talk {
  0%, 100% { transform: translate(-50%, -50%) scale(0.86, 0.48); }
  50% { transform: translate(-50%, -50%) scale(1, 1.12); }
}

@keyframes mouth-patch-talk {
  0%, 100% { transform: translate(-50%, -50%) scaleY(1); }
  50% { transform: translate(-50%, -50%) scaleY(1.06); }
}

</style>
