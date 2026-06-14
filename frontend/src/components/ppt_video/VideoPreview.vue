<template>
  <ResourceMediaFrame>
    <video
      v-if="src"
      class="video-preview"
      :src="src"
      controls
      :autoplay="autoplay"
      playsinline
    >
      您的浏览器不支持视频播放
    </video>
    <p v-else class="video-preview__empty">{{ fallbackText }}</p>
  </ResourceMediaFrame>
</template>

<script setup>
import ResourceMediaFrame from './ResourceMediaFrame.vue'

defineProps({
  src: {
    type: String,
    default: ''
  },
  autoplay: {
    type: Boolean,
    default: true
  },
  fallbackText: {
    type: String,
    default: '暂无视频内容'
  }
})
</script>

<style scoped>
.video-preview {
  width: min(100%, 980px);
  max-height: 100%;
  border-radius: 8px;
  background: #0f1f35;
  object-fit: contain;
}

.video-preview__empty {
  margin: auto;
  color: #5f8fc3;
}
</style>
