<template>
  <div class="process-strip" :class="`process-strip--count-${displayBlocks.length}`">
    <article v-for="(block, index) in displayBlocks" :key="index" class="process-step">
      <b>{{ index + 1 }}</b>
      <span v-html="renderMath(displayBlockText(block.text, 140))"></span>
    </article>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath } from '../../../utils/renderMath'

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

const displayBlocks = computed(() => props.blocks.slice(0, 5))
</script>
