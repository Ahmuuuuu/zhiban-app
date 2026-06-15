<template>
  <component
    :is="componentName"
    :slide="slide"
  />
</template>

<script setup>
import { computed } from 'vue'
import VideoFormulaSlide from './VideoFormulaSlide.vue'
import VideoKeyPointSlide from './VideoKeyPointSlide.vue'
import VideoVocabularySlide from './VideoVocabularySlide.vue'

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

const componentMap = {
  formula: VideoFormulaSlide,
  vocabulary: VideoVocabularySlide,
  keypoint: VideoKeyPointSlide,
  comparison: VideoKeyPointSlide,
  process: VideoKeyPointSlide,
  summary: VideoKeyPointSlide
}

const componentName = computed(() => componentMap[props.variant] || VideoKeyPointSlide)
</script>
