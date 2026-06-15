<template>
  <div class="video-slide-canvas">
    <VideoAmbientBackground
      class="video-slide-canvas__background"
      :background-url="resolvedBackgroundUrl"
      :active="isPlaying"
    />
    <VideoMotionLayer
      :slide="slide"
      :variant="variant"
    />

    <VideoStageInfo
      :chapter-count="slideCount"
      :duration-label="durationLabel"
    />

    <VideoSlideRenderer
      :slide="slide"
      :variant="variant"
    />

    <VideoWaveform
      v-if="showWaveform"
      class="video-slide-canvas__wave"
      :active="isPlaying"
    />

    <slot name="controls"></slot>
    <slot name="progress"></slot>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VideoAmbientBackground from '../VideoAmbientBackground.vue'
import VideoStageInfo from '../VideoStageInfo.vue'
import VideoWaveform from '../VideoWaveform.vue'
import { selectVideoBackground } from '../videoAssets'
import VideoMotionLayer from './VideoMotionLayer.vue'
import VideoSlideRenderer from './VideoSlideRenderer.vue'
import { classifyVideoSlide } from './videoSlideClassifier'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  },
  slideCount: {
    type: Number,
    default: 0
  },
  durationLabel: {
    type: String,
    default: '00:00'
  },
  isPlaying: {
    type: Boolean,
    default: false
  },
  hasStarted: {
    type: Boolean,
    default: false
  },
  backgroundUrl: {
    type: String,
    default: ''
  }
})

const variant = computed(() => classifyVideoSlide(props.slide))
const resolvedBackgroundUrl = computed(() => props.backgroundUrl || selectVideoBackground({
  title: props.slide?.title,
  content: [
    props.slide?.summary,
    props.slide?.text,
    ...(props.slide?.items || [])
  ].join(' ')
}))
const showWaveform = computed(() => !props.hasStarted || props.isPlaying)
</script>

<style scoped>
.video-slide-canvas {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0e2444;
}

.video-slide-canvas__wave {
  z-index: 4;
}

.video-slide-canvas__background {
  z-index: 0;
}
</style>
