<template>
  <section class="video-progress" aria-label="视频进度">
    <div class="video-progress__meta">
      <span>{{ currentLabel }}</span>
      <b>{{ durationLabel }}</b>
    </div>
    <div class="video-progress__track">
      <span class="video-progress__fill" :style="{ width: `${safeProgress}%` }"></span>
      <span class="video-progress__thumb" :style="{ left: `${safeProgress}%` }"></span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentTime: {
    type: Number,
    default: 0
  },
  duration: {
    type: Number,
    default: 0
  }
})

const formatTime = seconds => {
  if (!Number.isFinite(seconds) || seconds <= 0) return '00:00'
  const total = Math.floor(seconds)
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

const safeProgress = computed(() => {
  if (!Number.isFinite(props.duration) || props.duration <= 0) return 0
  return Math.min(100, Math.max(0, (props.currentTime / props.duration) * 100))
})

const currentLabel = computed(() => formatTime(props.currentTime))
const durationLabel = computed(() => formatTime(props.duration))
</script>

<style scoped>
.video-progress {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.video-progress__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.video-progress__meta b {
  color: rgba(31, 51, 86, 0.56);
}

.video-progress__track {
  position: relative;
  height: 8px;
  border-radius: 999px;
  background: rgba(201, 220, 233, 0.76);
  overflow: hidden;
}

.video-progress__fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #2f7de1, #5bc9bc);
  box-shadow: 0 0 18px rgba(47, 125, 225, 0.28);
}

.video-progress__thumb {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  border: 3px solid #ffffff;
  border-radius: 999px;
  background: #2f7de1;
  box-shadow: 0 8px 20px rgba(31, 51, 86, 0.22);
  transform: translate(-50%, -50%);
}
</style>
