<template>
  <div
    class="video-slide-canvas"
    :class="[`is-${backgroundTone}-bg`, `layout-${layoutSeed}`]"
    :style="backgroundColorVars"
  >
    <VideoAmbientBackground
      class="video-slide-canvas__background"
      :background-url="resolvedBackgroundUrl"
      :active="isPlaying"
    />
    <VideoMotionLayer
      :slide="slide"
      :variant="variant"
      :layout-seed="layoutSeed"
    />
    <VideoSubjectAssetLayer
      :slide="slide"
      :variant="variant"
      :layout-seed="layoutSeed"
    />

    <VideoStageInfo
      :chapter-count="slideCount"
      :duration-label="durationLabel"
    />

    <VideoSlideRenderer
      :slide="slide"
      :variant="variant"
      :tone="backgroundTone"
      :layout-seed="layoutSeed"
    />

    <VideoWaveform
      v-if="showWaveform"
      class="video-slide-canvas__wave"
      :active="isPlaying"
    />

    <slot name="progress"></slot>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VideoAmbientBackground from '../VideoAmbientBackground.vue'
import VideoStageInfo from '../VideoStageInfo.vue'
import VideoWaveform from '../VideoWaveform.vue'
import { getVideoBackgroundStyle, getVideoBackgroundTone, selectVideoBackground } from '../videoAssets'
import VideoMotionLayer from './VideoMotionLayer.vue'
import VideoSlideRenderer from './VideoSlideRenderer.vue'
import VideoSubjectAssetLayer from './VideoSubjectAssetLayer.vue'
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
const backgroundTone = computed(() => getVideoBackgroundTone(resolvedBackgroundUrl.value))
const backgroundStyle = computed(() => getVideoBackgroundStyle(resolvedBackgroundUrl.value))
const backgroundColorVars = computed(() => {
  const style = backgroundStyle.value || {}
  return {
    ...(style.text ? { '--video-text': style.text } : {}),
    ...(style.muted ? { '--video-muted': style.muted } : {}),
    ...(style.soft ? { '--video-soft': style.soft } : {}),
    ...(style.line ? { '--video-line': style.line } : {}),
    ...(style.numberBg ? { '--video-number-bg': style.numberBg } : {}),
    ...(style.numberText ? { '--video-number-text': style.numberText } : {}),
    ...(style.cardBg ? { '--video-card-bg': style.cardBg } : {}),
    ...(style.cardStrong ? { '--video-card-strong': style.cardStrong } : {}),
    ...(style.cardBorder ? { '--video-card-border': style.cardBorder } : {}),
    ...(style.chipBg ? { '--video-chip-bg': style.chipBg } : {}),
    ...(style.chipText ? { '--video-chip-text': style.chipText } : {}),
    ...(style.accent ? { '--video-accent': style.accent } : {}),
    ...(style.accentSoft ? { '--video-accent-soft': style.accentSoft } : {}),
    ...(style.warm ? { '--video-warm': style.warm } : {})
  }
})
const layoutSeed = computed(() => Number(props.slide?.index || 0) % 7)
</script>

<style scoped>
.video-slide-canvas {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #0e2444;
  --video-text: #f8fbff;
  --video-muted: rgba(235, 246, 255, 0.78);
  --video-soft: rgba(215, 242, 246, 0.92);
  --video-card-bg: rgba(8, 22, 44, 0.36);
  --video-card-strong: rgba(8, 22, 44, 0.48);
  --video-card-border: rgba(220, 240, 255, 0.22);
  --video-shadow: rgba(0, 0, 0, 0.22);
  --video-line: rgba(255, 255, 255, 0.78);
  --video-chip-bg: rgba(255, 255, 255, 0.13);
  --video-chip-text: rgba(240, 250, 255, 0.92);
  --video-number-bg: #ffffff;
  --video-number-text: #1f63d6;
  --video-accent: #2f7de1;
  --video-accent-soft: #6ec6ff;
  --video-warm: #ffd166;
  --video-bg-shade: rgba(8, 28, 62, 0.38);
  --video-bg-glow: rgba(255, 255, 255, 0.14);
}

.video-slide-canvas.is-light-bg {
  --video-text: #14233a;
  --video-muted: rgba(25, 43, 68, 0.76);
  --video-soft: rgba(39, 75, 116, 0.92);
  --video-card-bg: rgba(255, 255, 255, 0.72);
  --video-card-strong: rgba(255, 255, 255, 0.84);
  --video-card-border: rgba(41, 91, 152, 0.16);
  --video-shadow: rgba(55, 82, 115, 0.12);
  --video-line: rgba(31, 99, 214, 0.72);
  --video-chip-bg: rgba(255, 255, 255, 0.82);
  --video-chip-text: rgba(20, 35, 58, 0.9);
  --video-number-bg: #1f63d6;
  --video-number-text: #ffffff;
  --video-bg-shade: rgba(255, 255, 255, 0.16);
  --video-bg-glow: rgba(255, 255, 255, 0.26);
}

.video-slide-canvas__wave {
  z-index: 4;
}

.video-slide-canvas__background {
  z-index: 0;
}

.video-slide-canvas :deep(.video-keypoint-slide),
.video-slide-canvas :deep(.video-vocabulary-slide),
.video-slide-canvas :deep(.video-formula-slide),
.video-slide-canvas :deep(.video-intro-slide) {
  z-index: 2;
}
</style>
