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
  border-radius: 999px;
  background: rgba(201, 220, 233, 0.78);
  color: #5f8fc3;
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
  box-shadow: 0 0 0 4px rgba(95, 143, 195, 0.16);
}

.video-status.is-playing {
  background: rgba(91, 201, 188, 0.18);
  color: #148b7f;
}

.video-status.is-playing .video-status__dot {
  animation: status-pulse 1.4s ease-in-out infinite;
}

.video-status.is-paused {
  background: rgba(255, 205, 117, 0.22);
  color: #a66a14;
}

.video-status.is-empty {
  background: rgba(201, 220, 233, 0.46);
  color: rgba(95, 143, 195, 0.72);
}

@keyframes status-pulse {
  0%, 100% {
    box-shadow: 0 0 0 4px rgba(20, 139, 127, 0.16);
  }

  50% {
    box-shadow: 0 0 0 8px rgba(20, 139, 127, 0);
  }
}
</style>
