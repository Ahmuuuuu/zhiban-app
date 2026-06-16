<template>
  <div class="video-status" :class="statusClass">
    <span class="video-status__dot"></span>
    <span>{{ label }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isPlaying: {
    type: Boolean,
    default: false
  },
  hasStarted: {
    type: Boolean,
    default: false
  },
  hasSource: {
    type: Boolean,
    default: false
  }
})

const label = computed(() => {
  if (!props.hasSource) return '暂无视频'
  if (props.isPlaying) return '正在播放'
  if (props.hasStarted) return '已暂停'
  return '课程视频'
})

const statusClass = computed(() => ({
  'is-playing': props.isPlaying,
  'is-paused': props.hasStarted && !props.isPlaying,
  'is-empty': !props.hasSource
}))
</script>

<style scoped>
.video-status {
  width: fit-content;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(47, 125, 225, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: #1f63d6;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
}

.video-status__dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 4px rgba(31, 99, 214, 0.12);
}

.video-status.is-playing {
  border-color: rgba(31, 99, 214, 0.28);
  background: #ffffff;
  color: #1f63d6;
}

.video-status.is-playing .video-status__dot {
  animation: status-pulse 1.4s ease-in-out infinite;
}

.video-status.is-paused {
  border-color: rgba(95, 156, 255, 0.24);
  background: rgba(239, 246, 255, 0.86);
  color: #1f63d6;
}

.video-status.is-empty {
  border-color: rgba(201, 220, 233, 0.72);
  background: rgba(255, 255, 255, 0.56);
  color: rgba(53, 111, 184, 0.68);
}

@keyframes status-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 4px rgba(31, 99, 214, 0.16);
  }

  50% {
    box-shadow: 0 0 0 8px rgba(31, 99, 214, 0);
  }
}
</style>
