<template>
  <main class="presentation-player">
    <header class="player-topbar">
      <button type="button" @click="goBack">返回</button>
      <div>
        <span>Dynamic Lesson</span>
        <h1>{{ title }}</h1>
      </div>
      <a v-if="presentationUrl" :href="presentationUrl" target="_blank" rel="noopener noreferrer">新窗口打开</a>
    </header>

    <section class="player-stage">
      <iframe
        v-if="presentationUrl"
        ref="frameRef"
        class="lesson-frame"
        :src="presentationUrl"
        title="动态课件"
        allow="autoplay; fullscreen"
        @load="handleFrameLoad"
      ></iframe>
      <div v-else class="empty-state">没有找到课件地址</div>

      <aside class="teacher-pet" :class="{ speaking: isSpeaking }" aria-label="小知讲师">
        <div class="teacher-pet__bubble">
          <strong>小知讲师</strong>
          <span>{{ isSpeaking ? '正在讲解' : '等待播放' }}</span>
        </div>
        <div class="teacher-pet__body">
          <img :src="petImage" alt="" draggable="false" />
          <span class="teacher-pet__mouth"></span>
          <span class="teacher-pet__pointer"></span>
        </div>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { resolveApiUrl } from '../api/apis'
import petImage from '../assets/pic/zhiban-pet-base.png'

const route = useRoute()
const router = useRouter()
const frameRef = ref(null)
const isSpeaking = ref(false)
let audioPollTimer = 0

const presentationUrl = computed(() => resolveApiUrl(String(route.query.url || '')))
const title = computed(() => String(route.query.title || '动态课件'))

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/chat')
}

const detectSpeaking = () => {
  try {
    const doc = frameRef.value?.contentDocument || frameRef.value?.contentWindow?.document
    const audios = Array.from(doc?.querySelectorAll('audio') || [])
    isSpeaking.value = audios.some(audio => !audio.paused && !audio.ended && audio.currentTime > 0)
  } catch {
    isSpeaking.value = false
  }
}

const handleFrameLoad = () => {
  window.clearInterval(audioPollTimer)
  detectSpeaking()
  audioPollTimer = window.setInterval(detectSpeaking, 180)
}

onBeforeUnmount(() => {
  window.clearInterval(audioPollTimer)
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
  width: 100%;
  aspect-ratio: 1;
  object-fit: contain;
  user-select: none;
}

.teacher-pet__mouth {
  position: absolute;
  left: 47%;
  top: 56%;
  width: 11%;
  height: 4%;
  border-radius: 999px;
  background: rgba(22, 63, 143, 0.78);
  transform: translate(-50%, -50%) scaleY(0.45);
  opacity: 0;
}

.teacher-pet.speaking .teacher-pet__mouth {
  opacity: 1;
  animation: mouth-talk 0.18s steps(2, end) infinite;
}

.teacher-pet__pointer {
  position: absolute;
  left: 5%;
  top: 34%;
  width: 34%;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, #fff7a8, #5f8fc3);
  transform-origin: 100% 50%;
  transform: rotate(-24deg);
  box-shadow: 0 0 12px rgba(255, 247, 168, 0.72);
}

.teacher-pet.speaking .teacher-pet__pointer {
  animation: pointer-wave 0.9s ease-in-out infinite;
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
  0% { transform: translate(-50%, -50%) scaleY(0.42); }
  100% { transform: translate(-50%, -50%) scaleY(2.3); }
}

@keyframes pointer-wave {
  0%, 100% { transform: rotate(-24deg); }
  50% { transform: rotate(-34deg); }
}
</style>
