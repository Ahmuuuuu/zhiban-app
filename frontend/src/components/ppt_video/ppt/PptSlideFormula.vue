<template>
  <div class="formula-layout">
    <div class="formula-box" v-html="renderMath(formulaText)"></div>
    <div class="formula-points">
      <p
        v-for="(block, index) in formulaBlocks"
        :key="index"
        v-html="renderMath(displayBlockText(block.text, 180))"
      ></p>
    </div>
  </div>
</template>

<script setup>
import { renderMath } from '../../utils/renderMath'

defineProps({
  formulaText: {
    type: String,
    default: ''
  },
  formulaBlocks: {
    type: Array,
    default: () => []
  },
  displayBlockText: {
    type: Function,
    required: true
  }
})
</script>
