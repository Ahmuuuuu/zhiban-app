<template>
  <div class="comparison-grid">
    <article class="comparison-card">
      <b>A</b>
      <p
        v-for="(block, index) in leftBlocks"
        :key="index"
        v-html="renderMath(displayBlockText(block.text, 110))"
      ></p>
    </article>
    <article class="comparison-card comparison-card--accent">
      <b>B</b>
      <p
        v-for="(block, index) in rightBlocks"
        :key="index"
        v-html="renderMath(displayBlockText(block.text, 110))"
      ></p>
    </article>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath } from '../../utils/renderMath'

const props = defineProps({
  blocks: {
    type: Array,
    default: () => []
  },
  displayBlockText: {
    type: Function,
    required: true
  }
})

const leftBlocks = computed(() => props.blocks.filter((_, index) => index % 2 === 0).slice(0, 4))
const rightBlocks = computed(() => props.blocks.filter((_, index) => index % 2 === 1).slice(0, 4))
</script>
