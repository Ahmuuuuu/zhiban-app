<template>
  <div class="content-card-grid">
    <article v-for="(block, index) in blocks.slice(0, 6)" :key="index">
      <span>{{ index + 1 }}</span>
      <p v-html="renderMath(displayBlockText(block.text, 105))"></p>
    </article>
  </div>
</template>

<script setup>
import { renderMath } from '../../utils/renderMath'

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
