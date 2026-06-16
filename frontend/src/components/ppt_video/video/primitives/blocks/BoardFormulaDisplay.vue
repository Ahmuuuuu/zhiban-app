<template>
  <div class="board-formula-display" v-html="renderMath(formula)"></div>
</template>

<script setup>
import { renderMath } from '../../../../../utils/renderMath'

defineProps({
  formula: {
    type: String,
    required: true
  }
})
</script>

<style scoped>
.board-formula-display {
  min-height: 88px;
  padding: 18px;
  border-radius: var(--bfd-radius, 18px);
  border: 1px solid var(--video-card-border);
  background:
    radial-gradient(circle at center, color-mix(in srgb, var(--video-warm, #ffd166) 18%, transparent), transparent 64%),
    var(--video-card-strong);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    0 22px 54px var(--video-shadow);
  display: grid;
  place-items: center;
  overflow: hidden;
  animation: formula-pulse 2.8s ease-in-out infinite;
}

.board-formula-display :deep(.katex-display) {
  margin: 0;
}

.board-formula-display :deep(.katex) {
  max-width: 100%;
  font-size: clamp(18px, 2.1vw, 36px);
}

@keyframes formula-pulse {
  0%, 100% {
    box-shadow:
      inset 0 0 0 1px color-mix(in srgb, var(--video-text) 8%, transparent),
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      0 22px 54px var(--video-shadow);
  }
  50% {
    box-shadow:
      inset 0 0 0 1px color-mix(in srgb, var(--video-text) 36%, transparent),
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      0 0 36px color-mix(in srgb, var(--video-accent, #2f7de1) 24%, transparent),
      0 22px 54px var(--video-shadow);
  }
}
</style>
