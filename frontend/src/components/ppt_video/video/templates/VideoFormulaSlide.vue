<template>
  <section
    class="video-formula-slide video-fit-stage"
    :class="{ 'is-dense': notes.length > 4 || formulas.length > 3, 'is-flipped': flip }"
  >
    <div class="formula-main">
      <ChalkTag>{{ slide.chapterTitle }}</ChalkTag>
      <h2>{{ slide.title }}</h2>
      <BoardFormulaDisplay
        v-for="formula in formulas"
        :key="formula"
        :formula="formula"
      />
    </div>

    <div class="formula-notes">
      <article
        v-for="(item, index) in notes"
        :key="`${index}-${item}`"
        :style="{ '--delay': index }"
      >
        <ChalkNumber :value="index + 1" />
        <span v-html="renderMath(item)"></span>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath } from '../../../../utils/renderMath'
import ChalkTag from '../primitives/atoms/ChalkTag.vue'
import ChalkNumber from '../primitives/atoms/ChalkNumber.vue'
import BoardFormulaDisplay from '../primitives/blocks/BoardFormulaDisplay.vue'

const props = defineProps({
  slide: {
    type: Object,
    required: true
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

const formulas = computed(() => props.slide.formulas?.length
  ? props.slide.formulas
  : (props.slide.items?.length ? props.slide.items : [props.slide.title]))
const notes = computed(() => props.slide.items?.length ? [] : [])
const flip = computed(() => Number(props.slide?.index || 0) % 2 === 1)
</script>

<style scoped>
.video-formula-slide {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 340px);
  gap: var(--video-gap);
}

/* ===== flip: formulas on right ===== */
.video-formula-slide.is-flipped {
  grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
}

.video-formula-slide.is-flipped .formula-main { order: 2; }
.video-formula-slide.is-flipped .formula-notes { order: 1; }

/* ===== Dense — only shrink, keep layout ===== */
.video-formula-slide.is-dense {
  gap: 18px;
}

/* ===== Shared Panel Base ===== */
.formula-main,
.formula-notes {
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--video-card-border);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--video-accent, #2f7de1) 16%, transparent), transparent 58%),
    var(--video-card-bg);
  box-shadow: 0 22px 54px var(--video-shadow);
  backdrop-filter: blur(14px);
}

/* ===== formula-main ===== */
.formula-main {
  min-height: 0;
  padding: var(--video-panel-padding);
  display: grid;
  align-content: center;
  gap: calc(var(--video-gap) * 0.72);
  overflow: hidden;
  animation: formula-in 0.62s ease both;
}

.video-formula-slide.is-dense .formula-main {
  padding: 20px;
  gap: 14px;
}

.formula-main h2 {
  margin: 0;
  font-size: clamp(24px, 3.4cqw, 46px);
  line-height: 1.15;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.video-formula-slide.is-dense .formula-main h2 {
  font-size: clamp(22px, 2.4vw, 34px);
}

.video-formula-slide.is-dense :deep(.board-formula-display) {
  min-height: 60px;
  padding: 12px;
}

/* ===== formula-notes ===== */
.formula-notes {
  padding: calc(var(--video-panel-padding) * 0.72);
  display: grid;
  gap: 12px;
  align-content: center;
  overflow: hidden;
}

.video-formula-slide.is-dense .formula-notes {
  gap: 9px;
  padding: 16px;
  align-content: start;
}

.formula-notes article {
  --chalk-number-size: 30px;
  min-height: 0;
  padding: 12px;
  border-radius: 8px;
  background: var(--video-card-strong);
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  overflow: hidden;
  animation: note-in 0.5s ease both;
  animation-delay: calc(var(--delay) * 0.09s);
}

.video-formula-slide.is-dense .formula-notes article {
  --chalk-number-size: 26px;
  padding: 10px;
  grid-template-columns: 26px minmax(0, 1fr);
}

.formula-notes article:nth-child(2n) { border-radius: 999px; }
.formula-notes article:nth-child(3n) { border-radius: 8px 24px 8px 24px; }

.formula-notes span {
  color: var(--video-muted);
  line-height: 1.32;
  font-size: clamp(11px, 0.88vw, 15px);
}

/* ===== Animations ===== */
@keyframes formula-in {
  from { opacity: 0; transform: scale(0.98); }
  to   { opacity: 1; transform: scale(1); }
}

@keyframes note-in {
  from { opacity: 0; transform: translateX(12px); }
  to   { opacity: 1; transform: translateX(0); }
}
</style>
