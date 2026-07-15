<template>
  <section class="video-progress" aria-label="视频进度">
    <div class="video-progress__row">
      <span class="video-progress__time">{{ currentLabel }}</span>
      <button
        type="button"
        class="video-progress__play"
        :class="{ 'is-playing': isPlaying, 'is-disabled': !canPlay }"
        :disabled="!canPlay"
        :aria-label="isPlaying ? '暂停' : '播放'"
        @click="$emit('toggle-play')"
      >
        <span></span>
      </button>
      <div
        ref="trackRef"
        class="video-progress__track"
        role="slider"
        tabindex="0"
        :aria-valuemin="0"
        :aria-valuemax="Math.round(duration)"
        :aria-valuenow="Math.round(currentTime)"
        @pointerdown="handlePointer"
        @keydown.left.prevent="nudge(-5)"
        @keydown.right.prevent="nudge(5)"
      >
        <span
          v-for="segment in segments"
          :key="segment.id"
          class="video-progress__segment"
          :class="{ 'is-locked': segment.locked, 'is-ready': !segment.locked }"
          :style="{ left: `${segment.left}%`, width: `${segment.width}%` }"
        ></span>
        <span class="video-progress__fill" :style="{ width: `${safeProgress}%` }"></span>
        <button
          v-for="marker in markers"
          :key="marker.id"
          type="button"
          class="video-progress__marker"
          :class="{ 'is-locked': marker.locked }"
          :disabled="marker.locked"
          :style="{ left: `${marker.percent}%` }"
          :title="marker.label"
          @click.stop="seekToMarker(marker)"
        ></button>
        <span class="video-progress__thumb" :style="{ left: `${safeProgress}%` }"></span>
      </div>
      <span class="video-progress__time">{{ durationLabel }}</span>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  currentTime: {
    type: Number,
    default: 0
  },
  duration: {
    type: Number,
    default: 0
  },
  isPlaying: {
    type: Boolean,
    default: false
  },
  markers: {
    type: Array,
    default: () => []
  },
  segments: {
    type: Array,
    default: () => []
  },
  canPlay: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['toggle-play', 'seek'])
const trackRef = ref(null)

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

const segmentAt = time => props.segments.find(segment => time >= segment.start && time < segment.end)

const emitSeek = time => {
  const segment = segmentAt(time) || props.segments.at(-1)
  if (segment?.locked) return
  emit('seek', time)
}

const seekByClientX = clientX => {
  if (!trackRef.value || !props.duration) return
  const rect = trackRef.value.getBoundingClientRect()
  const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
  emitSeek(ratio * props.duration)
}

const handlePointer = event => {
  trackRef.value?.setPointerCapture?.(event.pointerId)
  seekByClientX(event.clientX)
  const move = moveEvent => seekByClientX(moveEvent.clientX)
  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up, { once: true })
}

const nudge = amount => {
  emitSeek(Math.min(Math.max(props.currentTime + amount, 0), props.duration || 0))
}

const seekToMarker = marker => {
  if (!marker.locked) emitSeek(marker.time)
}
</script>

<style scoped>
.video-progress {
  --player-blue: #6fa8dc;
  --player-blue-strong: #4f8fca;
  width: 100%;
  color: var(--player-blue);
}

.video-progress__row {
  min-width: 0;
  display: grid;
  grid-template-columns: auto 34px minmax(120px, 1fr) auto;
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

.video-progress__play {
  width: 34px;
  height: 34px;
  border: 2px solid var(--player-blue);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  display: grid;
  place-items: center;
  cursor: pointer;
  box-shadow: 0 0 0 1px rgba(111, 168, 220, 0.18);
}

.video-progress__play.is-disabled {
  opacity: 0.45;
  cursor: not-allowed;
  filter: grayscale(0.35);
}

.video-progress__play span {
  width: 0;
  height: 0;
  margin-left: 3px;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  border-left: 12px solid var(--player-blue);
}

.video-progress__play.is-playing span {
  width: 12px;
  height: 15px;
  margin-left: 0;
  border: 0;
  background:
    linear-gradient(90deg, var(--player-blue) 0 4px, transparent 4px 8px, var(--player-blue) 8px 12px);
}

.video-progress__track {
  position: relative;
  height: 6px;
  border: 1px solid var(--player-blue);
  border-radius: 999px;
  background: rgba(5, 12, 28, 0.2);
  cursor: pointer;
  overflow: visible;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.16);
  touch-action: none;
}

.video-progress__track:focus-visible {
  outline: 2px solid #ffffff;
  outline-offset: 3px;
}

.video-progress__fill {
  position: absolute;
  left: 3px;
  top: 3px;
  bottom: 3px;
  max-width: calc(100% - 6px);
  background: var(--player-blue);
  z-index: 2;
}

.video-progress__segment {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 999px;
  pointer-events: none;
  z-index: 1;
}

.video-progress__segment.is-ready {
  background: rgba(111, 168, 220, 0.2);
}

.video-progress__segment.is-locked {
  background:
    repeating-linear-gradient(
      135deg,
      rgba(245, 158, 11, 0.38) 0 6px,
      rgba(245, 158, 11, 0.14) 6px 12px
    );
}

.video-progress__marker {
  position: absolute;
  top: 50%;
  width: 5px;
  height: 5px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: var(--player-blue-strong);
  cursor: pointer;
  transform: translate(-50%, -50%);
  z-index: 3;
}

.video-progress__marker.is-locked {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.25);
  cursor: not-allowed;
}

.video-progress__thumb {
  position: absolute;
  top: 50%;
  width: 8px;
  height: 8px;
  border: 2px solid #ffffff;
  border-radius: 999px;
  background: var(--player-blue-strong);
  box-shadow: 0 0 0 2px rgba(79, 143, 202, 0.4);
  pointer-events: none;
  transform: translate(-50%, -50%);
  z-index: 4;
}

@media (max-width: 640px) {
  .video-progress__row {
    grid-template-columns: auto 30px minmax(80px, 1fr) auto;
  }

  .video-progress__play {
    width: 30px;
    height: 30px;
  }
}
</style>
