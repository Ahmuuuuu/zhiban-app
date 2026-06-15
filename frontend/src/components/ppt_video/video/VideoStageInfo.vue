<template>
  <div class="video-stage-info">
    <span>AI 课程视频</span>
    <b>{{ chapterCount }} 个章节</b>
    <b>{{ durationLabel }}</b>
  </div>
</template>

<script setup>
defineProps({
  chapterCount: {
    type: Number,
    default: 0
  },
  durationLabel: {
    type: String,
    default: '00:00'
  }
})
</script>

<style scoped>
.video-stage-info {
  position: absolute;
  z-index: 3;
  top: 18px;
  left: 18px;
  right: 18px;
  min-height: 34px;
  display: flex;
  align-items: center;
  gap: 8px;
  pointer-events: none;
}

.video-stage-info span,
.video-stage-info b {
  min-width: 0;
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  background: rgba(7, 18, 32, 0.46);
  color: rgba(255, 255, 255, 0.92);
  display: inline-flex;
  align-items: center;
  backdrop-filter: blur(12px);
  box-shadow: 0 12px 28px rgba(7, 18, 32, 0.16);
  font-size: 12px;
  font-weight: 900;
}

.video-stage-info b {
  color: rgba(215, 242, 246, 0.88);
}

@media (max-width: 640px) {
  .video-stage-info {
    top: 12px;
    left: 12px;
    right: 12px;
    flex-wrap: wrap;
  }
}
</style>
