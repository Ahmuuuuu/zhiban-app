<template>
  <section
    class="video-formula-slide"
    :class="`layout-${layoutSeed}`"
  >
    <div class="formula-main">
      <span>{{ slide.chapterTitle }}</span>
      <h2>{{ slide.title }}</h2>
      <div
        v-for="formula in formulas"
        :key="formula"
        class="formula-box"
        v-html="renderMath(formula)"
      ></div>
    </div>

    <div class="formula-notes">
      <article
        v-for="(item, index) in notes"
        :key="`${index}-${item}`"
        :style="{ '--delay': index }"
      >
        <b>{{ index + 1 }}</b>
        <span v-html="renderMath(item)"></span>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath } from '../../../../utils/renderMath'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  },
  layoutSeed: {
    type: Number,
    default: 0
  }
})

const formulas = computed(() => props.slide.formulas?.length ? props.slide.formulas.slice(0, 3) : [props.slide.title])
const notes = computed(() => (props.slide.items || []).slice(0, 4))
</script>

<style scoped>
.video-formula-slide {
  position: absolute;
  inset: 82px 54px 104px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: 28px;
  color: var(--video-text);
}

.video-formula-slide.layout-1 {
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
}

.video-formula-slide.layout-1 .formula-main {
  order: 2;
}

.video-formula-slide.layout-1 .formula-notes {
  order: 1;
}

.video-formula-slide.layout-2 {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 0.74fr) minmax(160px, 0.48fr);
}

.video-formula-slide.layout-2 .formula-notes {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: stretch;
}

.video-formula-slide.layout-3,
.video-formula-slide.layout-4 {
  grid-template-columns: minmax(0, 0.78fr) minmax(0, 1fr);
}

.video-formula-slide.layout-3 .formula-main {
  transform-origin: left center;
}

.video-formula-slide.layout-4 .formula-main {
  min-height: 0;
}

.formula-main,
.formula-notes {
  min-width: 0;
  border: 1px solid var(--video-card-border);
  border-radius: 8px;
  background: var(--video-card-bg);
  backdrop-filter: blur(14px);
}

.formula-main {
  padding: 32px;
  display: grid;
  align-content: center;
  gap: 20px;
  animation: formula-in 0.62s ease both;
}

.formula-main > span {
  width: fit-content;
  min-height: 30px;
  padding: 0 11px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.12);
  display: inline-flex;
  align-items: center;
  color: var(--video-soft);
  font-size: 12px;
  font-weight: 900;
}

.formula-main h2 {
  margin: 0;
  font-size: clamp(28px, 3vw, 46px);
  line-height: 1.15;
}

.formula-box {
  min-height: 104px;
  padding: 22px;
  border-radius: 8px;
  background: var(--video-card-strong);
  display: grid;
  place-items: center;
  overflow: hidden;
  animation: formula-pulse 2.8s ease-in-out infinite;
}

.formula-box :deep(.katex-display) {
  margin: 0;
}

.formula-box :deep(.katex) {
  max-width: 100%;
  overflow: hidden;
  font-size: clamp(24px, 2.7vw, 42px);
}

.formula-notes {
  padding: 22px;
  display: grid;
  gap: 12px;
  align-content: center;
}

.formula-notes article {
  min-height: 72px;
  padding: 14px;
  border-radius: 8px;
  background: var(--video-card-strong);
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  animation: note-in 0.5s ease both;
  animation-delay: calc(var(--delay) * 0.09s);
}

.formula-notes b {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: var(--video-number-bg);
  color: var(--video-number-text);
  display: grid;
  place-items: center;
}

.formula-notes span {
  color: var(--video-muted);
  line-height: 1.45;
  font-size: 15px;
}

@keyframes formula-in {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes formula-pulse {
  0%, 100% { box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08); }
  50% { box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.36), 0 0 36px rgba(31, 99, 214, 0.14); }
}

@keyframes note-in {
  from { opacity: 0; transform: translateX(12px); }
  to { opacity: 1; transform: translateX(0); }
}
</style>
