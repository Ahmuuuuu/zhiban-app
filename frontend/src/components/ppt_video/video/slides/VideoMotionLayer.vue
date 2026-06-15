<template>
  <div class="video-motion-layer" :class="`video-motion-layer--${variant}`" aria-hidden="true">
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
import { getSlideTerms } from './videoSlideClassifier'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  },
  variant: {
    type: String,
    default: 'keypoint'
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
.motion-equation {
  position: absolute;
  display: block;
}

.motion-card {
  width: clamp(86px, 10vw, 150px);
  height: clamp(46px, 5vw, 74px);
  left: calc(8% + var(--i) * 17%);
  top: calc(16% + (var(--i) % 3) * 20%);
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 18px 42px rgba(3, 16, 36, 0.14);
  animation: motion-card 5.8s ease-in-out infinite;
  animation-delay: calc(var(--i) * -0.42s);
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
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.86);
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
  background: rgba(255, 255, 255, 0.58);
  animation: motion-equation 4.8s ease-in-out infinite;
  animation-delay: calc(var(--i) * -0.28s);
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
