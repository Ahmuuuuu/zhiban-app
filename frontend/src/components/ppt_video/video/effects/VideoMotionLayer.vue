<template>
  <div
    class="video-motion-layer"
    :class="[`video-motion-layer--${variant}`, `shape-${layoutSeed % 7}`]"
    aria-hidden="true"
  >
    <span
      v-for="index in 4"
      :key="`orb-${index}`"
      class="motion-orb"
      :style="{ '--i': index }"
    ></span>
    <span
      v-for="index in 3"
      :key="`slash-${index}`"
      class="motion-slash"
      :style="{ '--i': index }"
    ></span>

    <template v-if="variant === 'vocabulary'">
      <span
        v-for="(term, index) in motionTerms"
        :key="`${term}-${index}`"
        class="motion-word"
        :style="{ '--i': index }"
      >{{ term }}</span>
    </template>

    <template v-else-if="variant === 'formula'">
      <span
        v-for="index in 6"
        :key="index"
        class="motion-equation"
        :style="{ '--i': index }"
      ></span>
    </template>

    <template v-else>
      <span
        v-for="index in 5"
        :key="index"
        class="motion-card"
        :style="{ '--i': index }"
      ></span>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getSlideTerms } from '../logic/videoSlideClassifier'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  },
  variant: {
    type: String,
    default: 'keypoint'
  },
  layoutSeed: {
    type: Number,
    default: 0
  }
})

const motionTerms = computed(() => {
  const terms = getSlideTerms(props.slide).slice(0, 7)
  return terms.length ? terms : ['Focus', 'Review', 'Practice']
})
</script>

<style scoped>
.video-motion-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
  overflow: hidden;
  pointer-events: none;
}

.motion-card,
.motion-word,
.motion-equation,
.motion-orb,
.motion-slash {
  position: absolute;
  display: block;
}

.motion-orb {
  width: clamp(44px, 6vw, 92px);
  aspect-ratio: 1;
  left: calc(12% + (var(--i) - 1) * 21%);
  top: calc(12% + (var(--i) % 3) * 24%);
  border: 1px solid color-mix(in srgb, var(--video-accent-soft, #6ec6ff) 62%, transparent);
  border-radius: 50%;
  opacity: 0.24;
  animation: motion-orb 7s ease-in-out infinite;
  animation-delay: calc(var(--i) * -0.6s);
}

.motion-orb::after {
  content: "";
  position: absolute;
  inset: 28%;
  border-radius: inherit;
  background: var(--video-accent-soft, #6ec6ff);
  opacity: 0.18;
}

.motion-slash {
  width: clamp(84px, 12vw, 180px);
  height: 18px;
  right: calc(8% + var(--i) * 18%);
  top: calc(20% + var(--i) * 19%);
  border-radius: 999px;
  background: color-mix(in srgb, var(--video-warm, #ffd166) 44%, transparent);
  transform: rotate(-18deg);
  opacity: 0.22;
  animation: motion-slash 6.4s ease-in-out infinite;
  animation-delay: calc(var(--i) * -0.48s);
}

.motion-card {
  width: clamp(86px, 10vw, 150px);
  height: clamp(46px, 5vw, 74px);
  left: calc(8% + var(--i) * 17%);
  top: calc(16% + (var(--i) % 3) * 20%);
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 8px;
  background: color-mix(in srgb, var(--video-accent, #2f7de1) 18%, transparent);
  box-shadow: 0 18px 42px rgba(3, 16, 36, 0.14);
  animation: motion-card 5.8s ease-in-out infinite;
  animation-delay: calc(var(--i) * -0.42s);
}

.shape-1 .motion-card {
  border-radius: 999px;
}

.shape-2 .motion-card {
  border-radius: 50%;
  width: clamp(72px, 8vw, 120px);
  height: clamp(72px, 8vw, 120px);
}

.shape-3 .motion-card {
  border-radius: 6px 26px 6px 26px;
  transform: rotate(-8deg);
}

.shape-4 .motion-card {
  clip-path: polygon(8% 0, 100% 0, 92% 100%, 0 100%);
}

.shape-5 .motion-card {
  border-radius: 22px 22px 6px 22px;
}

.shape-6 .motion-card {
  width: clamp(44px, 6vw, 84px);
  height: clamp(96px, 12vw, 170px);
  border-radius: 999px;
}

.motion-card::after {
  content: "";
  position: absolute;
  left: 12px;
  right: 12px;
  top: 50%;
  height: 2px;
  background: rgba(255, 255, 255, 0.52);
  box-shadow: 0 10px 0 rgba(255, 255, 255, 0.28);
}

.motion-word {
  left: calc(6% + var(--i) * 11%);
  top: calc(18% + (var(--i) % 4) * 15%);
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 999px;
  background: color-mix(in srgb, var(--video-accent-soft, #6ec6ff) 20%, transparent);
  color: var(--video-chip-text, rgba(255, 255, 255, 0.86));
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 900;
  animation: motion-word 6.2s ease-in-out infinite;
  animation-delay: calc(var(--i) * -0.36s);
}

.motion-equation {
  width: clamp(120px, 13vw, 220px);
  height: 1px;
  left: calc(10% + (var(--i) % 3) * 28%);
  top: calc(18% + var(--i) * 10%);
  background: var(--video-line, rgba(255, 255, 255, 0.58));
  animation: motion-equation 4.8s ease-in-out infinite;
  animation-delay: calc(var(--i) * -0.28s);
}

@keyframes motion-orb {
  0%, 100% { opacity: 0.12; transform: translate3d(0, 0, 0) scale(0.84); }
  45% { opacity: 0.34; transform: translate3d(18px, -22px, 0) scale(1.08); }
  72% { opacity: 0.22; transform: translate3d(-10px, 12px, 0) scale(0.96); }
}

@keyframes motion-slash {
  0%, 100% { opacity: 0.12; transform: rotate(-18deg) translateX(-16px); }
  50% { opacity: 0.34; transform: rotate(-18deg) translateX(18px); }
}

.motion-equation::before,
.motion-equation::after {
  content: "";
  position: absolute;
  top: -12px;
  width: 24px;
  height: 24px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 6px;
}

.motion-equation::before {
  left: 0;
}

.motion-equation::after {
  right: 0;
}

@keyframes motion-card {
  0%, 100% { opacity: 0.24; transform: translateY(0) scale(0.96); }
  50% { opacity: 0.58; transform: translateY(-14px) scale(1); }
}

@keyframes motion-word {
  0%, 100% { opacity: 0.3; transform: translate3d(0, 0, 0); }
  50% { opacity: 0.78; transform: translate3d(10px, -12px, 0); }
}

@keyframes motion-equation {
  0%, 100% { opacity: 0.22; transform: translateX(-8px); }
  50% { opacity: 0.66; transform: translateX(12px); }
}
</style>
