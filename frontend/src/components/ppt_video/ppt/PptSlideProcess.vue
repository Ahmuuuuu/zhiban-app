<template>
  <div class="process-strip">
    <article v-for="(block, index) in blocks.slice(0, 5)" :key="index" class="process-step">
      <b>{{ index + 1 }}</b>
      <span v-html="renderMath(displayBlockText(block.text, 140))"></span>
    </article>
  </div>
</template>

<script setup>
import { renderMath } from '../../../utils/renderMath'

defineProps({
  blocks: {
    type: Array,
    default: () => []
  },
  displayBlockText: {
    type: Function,
    required: true
  }
})
</script>
