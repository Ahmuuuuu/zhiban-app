<template>
  <section
    class="video-formula-slide"
    :class="[`layout-${layoutSeed}`, { 'is-dense': notes.length > 4 || formulas.length > 3 }]"
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
        <span v-html="karaokeNotes[index]"></span>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath, renderKaraokeHTML } from '../../../../utils/renderMath'

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

const formulas = computed(() => props.slide.formulas?.length ? props.slide.formulas : [props.slide.title])
const notes = computed(() => props.slide.items || [])

const karaokeNotes = computed(() => {
  const words = props.timedWords || []
  if (!words.length) return notes.value.map(item => renderMath(item))
  // TTS 全文顺序：title → formulas(text) → notes(items)
  // title 和 formulas 不以 karaoke 渲染，需跳过它们占用的词
  let offset = 0
  offset += renderKaraokeHTML(props.slide.title || '', words, offset).consumed
  for (const f of formulas.value) {
    offset += renderKaraokeHTML(f, words, offset).consumed
  }
  return notes.value.map(item => {
    const { html, consumed } = renderKaraokeHTML(item, words, offset)
    offset += consumed
    return html
  })
})
</script>

<style scoped>
.video-formula-slide {
  position: absolute;
  inset: 82px 54px 104px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: 28px;
  color: var(--video-text);
}

.video-formula-slide *,
.video-formula-slide *::before,
.video-formula-slide *::after {
  box-sizing: border-box;
}

.video-formula-slide.is-dense {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 0.72fr) minmax(0, 1fr);
  gap: 18px;
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
  min-height: 0;
  border: 1px solid var(--video-card-border);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--video-accent, #2f7de1) 16%, transparent), transparent 58%),
    var(--video-card-bg);
  backdrop-filter: blur(14px);
}

.video-formula-slide.layout-1 .formula-main,
.video-formula-slide.layout-1 .formula-notes {
  border-radius: 32px 8px 32px 8px;
}

.video-formula-slide.layout-2 .formula-main {
  border-radius: 999px;
  padding-inline: 72px;
}

.video-formula-slide.layout-2 .formula-notes {
  border-radius: 8px 34px 8px 34px;
}

.video-formula-slide.layout-3 .formula-main {
  clip-path: polygon(6% 0, 100% 0, 94% 100%, 0 100%);
}

.video-formula-slide.layout-3 .formula-notes {
  border-radius: 50%;
  aspect-ratio: 1;
  align-self: center;
}

.video-formula-slide.layout-4 .formula-main {
  border-radius: 50%;
  aspect-ratio: 1.35;
  align-self: center;
}

.video-formula-slide.layout-4 .formula-notes {
  clip-path: polygon(0 0, 94% 0, 100% 16%, 100% 100%, 6% 100%, 0 84%);
}

.formula-main {
  padding: 32px;
  display: grid;
  align-content: center;
  gap: 20px;
  animation: formula-in 0.62s ease both;
}

.video-formula-slide.is-dense .formula-main {
  padding: 22px;
  gap: 14px;
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

.video-formula-slide.is-dense .formula-main h2 {
  font-size: clamp(24px, 2.6vw, 38px);
}

.formula-box {
  min-height: 88px;
  padding: 18px;
  border-radius: 18px;
  background:
    radial-gradient(circle at center, color-mix(in srgb, var(--video-warm, #ffd166) 18%, transparent), transparent 64%),
    var(--video-card-strong);
  display: grid;
  place-items: center;
  overflow: hidden;
  animation: formula-pulse 2.8s ease-in-out infinite;
}

.video-formula-slide.is-dense .formula-box {
  min-height: 64px;
  padding: 12px;
}

.video-formula-slide.layout-2 .formula-box,
.video-formula-slide.layout-4 .formula-box {
  border-radius: 999px;
}

.formula-box :deep(.katex-display) {
  margin: 0;
}

.formula-box :deep(.katex) {
  max-width: 100%;
  font-size: clamp(18px, 2.1vw, 36px);
}

.formula-notes {
  padding: 22px;
  display: grid;
  gap: 12px;
  align-content: center;
  overflow: hidden;
}

.video-formula-slide.is-dense .formula-notes {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 9px;
  padding: 16px;
  align-content: start;
}

.formula-notes article {
  min-height: 64px;
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
  min-height: 0;
  padding: 10px;
  grid-template-columns: 26px minmax(0, 1fr);
}

.formula-notes article:nth-child(2n) {
  border-radius: 999px;
}

.formula-notes article:nth-child(3n) {
  border-radius: 8px 24px 8px 24px;
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

.video-formula-slide.is-dense .formula-notes b {
  width: 26px;
  height: 26px;
  font-size: 12px;
}

.formula-notes span {
  color: var(--video-muted);
  line-height: 1.32;
  font-size: clamp(11px, 0.88vw, 15px);
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
