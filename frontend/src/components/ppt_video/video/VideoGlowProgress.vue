<template>
  <section class="video-progress" aria-label="视频进度">
    <div class="video-progress__row">
      <span class="video-progress__time">{{ currentLabel }}</span>
      <div class="video-progress__track">
        <span class="video-progress__fill" :style="{ width: `${safeProgress}%` }"></span>
        <span class="video-progress__thumb" :style="{ left: `${safeProgress}%` }"></span>
      </div>
      <span class="video-progress__time">{{ durationLabel }}</span>
    </div>

    <div class="video-progress__controls" aria-hidden="true">
      <span class="control control--prev"></span>
      <span class="control control--back"></span>
      <span class="control control--play"></span>
      <span class="control control--next"></span>
      <span class="control control--forward"></span>
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
  --player-blue: #6fa8dc;
  --player-blue-strong: #4f8fca;
  width: 100%;
  display: grid;
  gap: 10px;
  color: var(--player-blue);
}

.video-progress__row {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(120px, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.video-progress__time {
  color: var(--player-blue);
  font-size: 13px;
  font-weight: 900;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 10px rgba(111, 168, 220, 0.22);
}

.video-progress__track {
  position: relative;
  height: 13px;
  border: 2px solid var(--player-blue);
  border-radius: 0;
  background: rgba(5, 12, 28, 0.18);
  overflow: visible;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.16);
}

.video-progress__fill {
  position: absolute;
  left: 3px;
  top: 3px;
  bottom: 3px;
  max-width: calc(100% - 6px);
  background: var(--player-blue);
}

.video-progress__thumb {
  position: absolute;
  top: 50%;
  width: 5px;
  height: 19px;
  border: 1px solid #ffffff;
  border-radius: 0;
  background: var(--player-blue-strong);
  box-shadow: 0 0 0 1px rgba(79, 143, 202, 0.36);
  transform: translate(-50%, -50%);
}

.video-progress__controls {
  min-height: 40px;
  display: grid;
  grid-template-columns: repeat(2, 26px) 1fr repeat(2, 26px);
  align-items: center;
  gap: 8px;
  padding: 0 34px;
}

.control {
  position: relative;
  width: 22px;
  height: 22px;
  border: 2px solid var(--player-blue);
  border-radius: 50%;
  background: rgba(111, 168, 220, 0.1);
  display: inline-block;
}

.control::before,
.control::after {
  content: "";
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.control--prev::before,
.control--back::before {
  left: 6px;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  border-right: 6px solid var(--player-blue);
}

.control--prev::after {
  left: 4px;
  width: 2px;
  height: 10px;
  background: var(--player-blue);
}

.control--next::before,
.control--forward::before {
  right: 6px;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  border-left: 6px solid var(--player-blue);
}

.control--next::after {
  right: 4px;
  width: 2px;
  height: 10px;
  background: var(--player-blue);
}

.control--play {
  justify-self: center;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 0;
  background: var(--player-blue);
  clip-path: polygon(50% 0, 61% 31%, 95% 31%, 67% 51%, 78% 86%, 50% 65%, 22% 86%, 33% 51%, 5% 31%, 39% 31%);
}

.control--play::before,
.control--play::after {
  width: 4px;
  height: 18px;
  background: rgba(5, 12, 28, 0.58);
}

.control--play::before {
  left: 16px;
}

.control--play::after {
  right: 16px;
}

@media (max-width: 640px) {
  .video-progress__controls {
    padding: 0 12px;
  }
}
</style>
