<template>
  <BoardSurface class="board-visual-block">
    <div class="visual-focus">
      <span
        v-for="index in 4"
        :key="index"
        :style="{ '--line': index }"
      ></span>
    </div>
    <div class="term-cloud">
      <ChalkTag
        v-for="(term, index) in terms"
        :key="term"
        :style="{ '--delay': index }"
      >
        {{ term }}
      </ChalkTag>
    </div>
  </BoardSurface>
</template>

<script setup>
import BoardSurface from '../atoms/BoardSurface.vue'
import ChalkTag from '../atoms/ChalkTag.vue'

defineProps({
  terms: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.board-visual-block {
  animation: visual-in 0.66s ease both;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.visual-focus {
  position: absolute;
  left: 28px;
  right: 28px;
  top: 34px;
  height: 48%;
  border: 1px solid color-mix(in srgb, var(--video-text) 16%, transparent);
  border-radius: inherit;
  overflow: hidden;
}

.visual-focus::after {
  content: "";
  position: absolute;
  inset: 0;
  background: #fff;
  opacity: 0.12;
  transform: translateX(-82%);
  animation: visual-scan 4.6s ease-in-out infinite;
}

.visual-focus span {
  position: absolute;
  left: 20px;
  right: calc(18px + var(--line) * 34px);
  top: calc(18px + var(--line) * 30px);
  height: 4px;
  border-radius: 999px;
  background: var(--video-line);
  animation: visual-line 3s ease-in-out infinite;
  animation-delay: calc(var(--line) * -0.28s);
}

.term-cloud {
  position: absolute;
  left: 22px;
  right: 22px;
  bottom: 22px;
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  max-height: 36%;
  overflow: hidden;
}

.term-cloud :deep(.chalk-tag) {
  animation: term-float 3.2s ease-in-out infinite;
  animation-delay: calc(var(--delay) * -0.18s);
}

@keyframes visual-in {
  from { opacity: 0; transform: translateX(18px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes visual-scan {
  0%, 25% { transform: translateX(-82%); }
  70%, 100% { transform: translateX(82%); }
}

@keyframes visual-line {
  0%, 100% { opacity: 0.42; transform: scaleX(0.86); transform-origin: left; }
  50% { opacity: 0.9; transform: scaleX(1); transform-origin: left; }
}

@keyframes term-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}
</style>
