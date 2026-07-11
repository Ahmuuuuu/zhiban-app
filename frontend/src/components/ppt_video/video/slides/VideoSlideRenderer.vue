<template>
  <Transition :name="transitionName" mode="out-in">
    <component
      :is="componentName"
      :key="slide.id || slide.index || slide.title"
      :slide="slide"
      :tone="tone"
      :layout-seed="layoutSeed"
      :timed-words="timedWords"
    />
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import BlackboardKeypointTemplate from '../templates/BlackboardKeypointTemplate.vue'
import VideoFormulaSlide from '../templates/VideoFormulaSlide.vue'
import VideoIntroSlide from '../templates/VideoIntroSlide.vue'
import VideoVocabularySlide from '../templates/VideoVocabularySlide.vue'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  },
  variant: {
    type: String,
    default: 'keypoint'
  },
  tone: {
    type: String,
    default: 'dark'
  },
  layoutSeed: {
    type: Number,
    default: 0
  },
  timedWords: {
    type: Array,
    default: () => []
  }
})

const componentMap = {
  intro: VideoIntroSlide,
  formula: VideoFormulaSlide,
  vocabulary: VideoVocabularySlide,
  keypoint: BlackboardKeypointTemplate
}

const componentName = computed(() => componentMap[props.variant] || BlackboardKeypointTemplate)
const transitionName = computed(() => [
  'slide-swing',
  'slide-rise',
  'slide-zoom',
  'slide-wipe',
  'slide-drift',
  'slide-flip',
  'slide-iris'
][props.layoutSeed % 7])
</script>

<style scoped>
.slide-swing-enter-active,
.slide-swing-leave-active,
.slide-rise-enter-active,
.slide-rise-leave-active,
.slide-zoom-enter-active,
.slide-zoom-leave-active,
.slide-wipe-enter-active,
.slide-wipe-leave-active,
.slide-drift-enter-active,
.slide-drift-leave-active,
.slide-flip-enter-active,
.slide-flip-leave-active,
.slide-iris-enter-active,
.slide-iris-leave-active {
  transition:
    opacity 0.42s ease,
    transform 0.42s ease,
    filter 0.42s ease,
    clip-path 0.42s ease;
}

.slide-swing-enter-from {
  opacity: 0;
  transform: translateX(34px) rotate(1.2deg) scale(0.985);
  filter: blur(6px);
}

.slide-swing-leave-to {
  opacity: 0;
  transform: translateX(-30px) rotate(-1deg) scale(0.985);
  filter: blur(6px);
}

.slide-rise-enter-from {
  opacity: 0;
  transform: translateY(36px) scale(0.98);
}

.slide-rise-leave-to {
  opacity: 0;
  transform: translateY(-26px) scale(0.99);
}

.slide-zoom-enter-from {
  opacity: 0;
  transform: scale(0.94);
  filter: blur(8px);
}

.slide-zoom-leave-to {
  opacity: 0;
  transform: scale(1.04);
  filter: blur(8px);
}

.slide-wipe-enter-from {
  opacity: 0;
  clip-path: inset(0 100% 0 0);
}

.slide-wipe-leave-to {
  opacity: 0;
  clip-path: inset(0 0 0 100%);
}

.slide-drift-enter-from {
  opacity: 0;
  transform: translate(-24px, 20px) scale(0.98);
  filter: blur(5px);
}

.slide-drift-leave-to {
  opacity: 0;
  transform: translate(24px, -16px) scale(0.98);
  filter: blur(5px);
}

.slide-flip-enter-from {
  opacity: 0;
  transform: perspective(900px) rotateY(-18deg) translateX(28px);
  filter: blur(4px);
}

.slide-flip-leave-to {
  opacity: 0;
  transform: perspective(900px) rotateY(18deg) translateX(-28px);
  filter: blur(4px);
}

.slide-iris-enter-from {
  opacity: 0;
  transform: scale(0.98);
  clip-path: circle(0% at 50% 50%);
}

.slide-iris-leave-to {
  opacity: 0;
  transform: scale(1.02);
  clip-path: circle(0% at 50% 50%);
}
</style>
