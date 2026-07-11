<template>
  <div
    class="video-slide-canvas"
    :class="[`is-${backgroundTone}-bg`, `layout-${layoutSeed}`, styleVariantClass]"
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
      :layout-seed="contentLayoutSeed"
    />

    <VideoStageInfo
      :chapter-count="slideCount"
      :duration-label="durationLabel"
    />

    <VideoSlideRenderer
      :slide="slide"
      :variant="variant"
      :tone="backgroundTone"
      :layout-seed="contentLayoutSeed"
      :timed-words="timedWords"
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
import VideoAmbientBackground from '../effects/VideoAmbientBackground.vue'
import VideoMotionLayer from '../effects/VideoMotionLayer.vue'
import VideoSubjectAssetLayer from '../effects/VideoSubjectAssetLayer.vue'
import VideoWaveform from '../effects/VideoWaveform.vue'
import { getVideoBackgroundStyle, getVideoBackgroundTone, selectVideoBackground } from '../logic/videoAssets'
import VideoStageInfo from '../VideoStageInfo.vue'
import VideoSlideRenderer from './VideoSlideRenderer.vue'
import { classifyVideoSlide } from '../logic/videoSlideClassifier'

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
  },
  timedWords: {
    type: Array,
    default: () => []
  },
  styleVariant: {
    type: String,
    default: ''  // '', 'chalkboard', 'glass', 'neon', 'paper', 'midnight'
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
const contentLayoutSeed = computed(() => Number(props.slide?.index || 0) % 5)
const styleVariantClass = computed(() => props.styleVariant ? `variant-${props.styleVariant}` : '')
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

/* ===== 🎨 Style Variants — add via class on .video-slide-canvas ===== */

/* Chalkboard — 黑板粉笔 */
.video-slide-canvas.variant-chalkboard {
  background: #1a3a2a;
  --video-text: #e8e6d9;
  --video-muted: rgba(225, 222, 200, 0.72);
  --video-soft: rgba(199, 240, 200, 0.82);
  --video-card-bg: rgba(20, 48, 32, 0.42);
  --video-card-strong: rgba(20, 48, 32, 0.55);
  --video-card-border: rgba(180, 210, 170, 0.2);
  --video-shadow: rgba(0, 0, 0, 0.28);
  --video-line: rgba(220, 240, 210, 0.7);
  --video-chip-bg: rgba(255, 255, 255, 0.1);
  --video-chip-text: rgba(230, 240, 225, 0.88);
  --video-number-bg: #e8e6d9;
  --video-number-text: #1a3a2a;
  --video-accent: #7ec87b;
  --video-accent-soft: #b8e6b0;
  --video-warm: #f5d77a;
  --video-bg-shade: rgba(10, 32, 18, 0.48);
  --video-bg-glow: rgba(200, 240, 200, 0.1);
}

/* Glass — 毛玻璃现代风 */
.video-slide-canvas.variant-glass {
  background: #eef3f8;
  --video-text: #1a2332;
  --video-muted: rgba(40, 55, 78, 0.7);
  --video-soft: rgba(44, 82, 130, 0.85);
  --video-card-bg: rgba(255, 255, 255, 0.55);
  --video-card-strong: rgba(255, 255, 255, 0.72);
  --video-card-border: rgba(190, 210, 230, 0.46);
  --video-shadow: rgba(60, 90, 130, 0.1);
  --video-line: rgba(44, 100, 190, 0.5);
  --video-chip-bg: rgba(255, 255, 255, 0.7);
  --video-chip-text: rgba(20, 35, 60, 0.88);
  --video-number-bg: #2c64be;
  --video-number-text: #ffffff;
  --video-accent: #4a8de0;
  --video-accent-soft: #89c2f7;
  --video-warm: #f0a040;
  --video-bg-shade: rgba(255, 255, 255, 0.08);
  --video-bg-glow: rgba(255, 255, 255, 0.32);
}

/* Neon — 赛博霓虹 */
.video-slide-canvas.variant-neon {
  background: #0a0a14;
  --video-text: #e0e8ff;
  --video-muted: rgba(195, 205, 240, 0.72);
  --video-soft: rgba(140, 180, 255, 0.88);
  --video-card-bg: rgba(15, 15, 30, 0.55);
  --video-card-strong: rgba(20, 20, 40, 0.68);
  --video-card-border: rgba(120, 140, 220, 0.28);
  --video-shadow: rgba(80, 100, 255, 0.15);
  --video-line: rgba(130, 160, 255, 0.7);
  --video-chip-bg: rgba(80, 100, 255, 0.15);
  --video-chip-text: rgba(200, 210, 255, 0.9);
  --video-number-bg: #5064ff;
  --video-number-text: #ffffff;
  --video-accent: #7b8cff;
  --video-accent-soft: #b8c4ff;
  --video-warm: #ff79c6;
  --video-bg-shade: rgba(10, 10, 20, 0.52);
  --video-bg-glow: rgba(120, 140, 255, 0.16);
}

/* Paper — 纸质笔记本 */
.video-slide-canvas.variant-paper {
  background: #faf6ed;
  --video-text: #2c2416;
  --video-muted: rgba(60, 48, 28, 0.7);
  --video-soft: rgba(100, 72, 40, 0.8);
  --video-card-bg: rgba(255, 252, 245, 0.72);
  --video-card-strong: rgba(255, 252, 245, 0.86);
  --video-card-border: rgba(180, 160, 120, 0.28);
  --video-shadow: rgba(80, 50, 20, 0.08);
  --video-line: rgba(120, 90, 50, 0.42);
  --video-chip-bg: rgba(255, 252, 245, 0.78);
  --video-chip-text: rgba(50, 35, 18, 0.88);
  --video-number-bg: #8b6914;
  --video-number-text: #ffffff;
  --video-accent: #b8860b;
  --video-accent-soft: #e6c860;
  --video-warm: #d4875a;
  --video-bg-shade: rgba(250, 246, 237, 0.1);
  --video-bg-glow: rgba(255, 255, 255, 0.18);
}

/* Midnight — 午夜深蓝 + 金色点缀 */
.video-slide-canvas.variant-midnight {
  background: #0b1525;
  --video-text: #e2e9f5;
  --video-muted: rgba(200, 215, 235, 0.74);
  --video-soft: rgba(180, 210, 245, 0.86);
  --video-card-bg: rgba(12, 22, 40, 0.5);
  --video-card-strong: rgba(16, 28, 50, 0.62);
  --video-card-border: rgba(180, 190, 220, 0.2);
  --video-shadow: rgba(0, 0, 0, 0.28);
  --video-line: rgba(210, 200, 160, 0.62);
  --video-chip-bg: rgba(210, 180, 100, 0.14);
  --video-chip-text: rgba(235, 225, 200, 0.9);
  --video-number-bg: #c9a84c;
  --video-number-text: #0b1525;
  --video-accent: #d4af5e;
  --video-accent-soft: #f0d888;
  --video-warm: #e8b44c;
  --video-bg-shade: rgba(8, 16, 30, 0.5);
  --video-bg-glow: rgba(210, 180, 120, 0.12);
}

.video-slide-canvas__wave {
  z-index: 4;
}

.video-slide-canvas__background {
  z-index: 0;
}

.video-slide-canvas :deep(.blackboard-keypoint-template),
.video-slide-canvas :deep(.video-vocabulary-slide),
.video-slide-canvas :deep(.video-formula-slide),
.video-slide-canvas :deep(.video-intro-slide) {
  z-index: 2;
}
</style>
