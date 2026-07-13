<template>
  <section
    class="video-vocabulary-slide video-fit-stage"
    :class="{ 'is-dense': vocabCards.length > 6, 'is-flipped': flip }"
  >
    <BoardHeaderBlock
      class="video-vocabulary-slide__header"
      :kicker="slide.chapterTitle"
      :title="slide.title"
      :summary="slide.summary"
    />

    <div class="vocab-deck">
      <article
        v-for="(card, index) in vocabCards"
        :key="`${index}-${card.word}`"
        :style="{ '--delay': index }"
      >
        <b>{{ card.word }}</b>
        <span>{{ card.meaning }}</span>
      </article>
    </div>

    <div class="scene-board">
      <ChalkTag>Scene Practice</ChalkTag>
      <p v-html="renderMath(exampleText)"></p>
      <div class="scene-bars">
        <i
          v-for="dot in 5"
          :key="dot"
          :style="{ '--dot': dot }"
        ></i>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath } from '../../../../utils/renderMath'
import ChalkTag from '../primitives/atoms/ChalkTag.vue'
import BoardHeaderBlock from '../primitives/blocks/BoardHeaderBlock.vue'

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

const vocabCards = computed(() => {
  const items = Array.isArray(props.slide.items) ? props.slide.items : []
  const cards = []
  items.forEach(item => {
    const text = String(item || '')
    const pairs = text.match(/[A-Za-z][A-Za-z-]{2,}(?:\s*\([^)]{1,18}\)|（[^）]{1,18}）)?/g) || []
    pairs.forEach(pair => {
      const word = pair.replace(/[（(].*$/, '').trim()
      const meaning = pair.match(/[（(]([^）)]+)[）)]/)?.[1] || '重点词汇'
      cards.push({ word, meaning })
    })
  })
  return cards.length ? cards : [{ word: props.slide.title, meaning: props.slide.summary || '核心表达' }]
})

const exampleText = computed(() => props.slide.items?.[0] || props.slide.summary || '')
const flip = computed(() => Number(props.slide?.index || 0) % 2 === 1)
</script>

<style scoped>
.video-vocabulary-slide {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 390px);
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-areas:
    "header scene"
    "deck   scene";
  gap: calc(var(--video-gap) * 0.8) var(--video-gap);
}

/* ===== flip: scene on left ===== */
.video-vocabulary-slide.is-flipped {
  grid-template-columns: minmax(300px, 390px) minmax(0, 1fr);
  grid-template-areas:
    "scene header"
    "scene deck";
}

/* ===== Dense — only shrink, keep layout ===== */
.video-vocabulary-slide.is-dense {
  gap: calc(var(--video-gap) * 0.58) calc(var(--video-gap) * 0.78);
}

/* ===== grid areas ===== */
.video-vocabulary-slide__header { grid-area: header; }

/* ===== Header (via BoardHeaderBlock) ===== */
.video-vocabulary-slide :deep(.video-vocabulary-slide__header.board-header-block) {
  animation: vocab-rise 0.58s ease both;
}

.video-vocabulary-slide.is-dense :deep(.video-vocabulary-slide__header.board-header-block h2) {
  font-size: var(--video-title-tight-size);
}

.video-vocabulary-slide.is-dense :deep(.video-vocabulary-slide__header.board-header-block p) {
  max-width: 100%;
  font-size: clamp(12px, 0.94vw, 16px);
  line-height: 1.45;
}

/* ===== Vocab Deck ===== */
.vocab-deck {
  grid-area: deck;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  align-content: start;
  overflow: hidden;
}

.video-vocabulary-slide.is-dense .vocab-deck {
  gap: 9px;
}

.vocab-deck article {
  min-height: 0;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid var(--video-card-border);
  background:
    radial-gradient(circle at 18% 18%, color-mix(in srgb, var(--video-warm, #ffd166) 22%, transparent), transparent 38%),
    var(--video-card-bg);
  display: grid;
  gap: 6px;
  overflow: hidden;
  box-shadow: 0 18px 42px var(--video-shadow);
  animation: vocab-card 0.62s ease both;
  animation-delay: calc(var(--delay) * 0.08s);
}

.video-vocabulary-slide.is-dense .vocab-deck article {
  padding: 11px;
  gap: 5px;
}

.vocab-deck b {
  font-size: clamp(17px, 1.55vw, 28px);
  line-height: 1;
  color: var(--video-accent, currentColor);
}

.vocab-deck span {
  color: var(--video-muted);
  font-size: clamp(11px, 0.84vw, 14px);
  line-height: 1.28;
}

/* ===== Scene Board ===== */
.scene-board {
  grid-area: scene;
  position: relative;
  overflow: hidden;
  padding: var(--video-panel-padding);
  border: 1px solid var(--video-card-border);
  border-radius: 8px;
  background:
    linear-gradient(140deg, color-mix(in srgb, var(--video-accent-soft, #6ec6ff) 20%, transparent), transparent 58%),
    var(--video-card-bg);
  display: grid;
  align-content: center;
  gap: 18px;
  box-shadow: 0 22px 54px var(--video-shadow);
}

.scene-board p {
  margin: 0;
  color: var(--video-text);
  font-size: clamp(15px, 1.45vw, 28px);
  line-height: 1.42;
  max-height: 58%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 7;
  -webkit-box-orient: vertical;
}

.scene-bars {
  position: absolute;
  inset: auto 24px 24px;
  height: 42px;
  display: flex;
  gap: 8px;
  align-items: end;
}

.scene-bars i {
  width: 100%;
  max-width: 14px;
  height: calc(12px + var(--dot) * 5px);
  border-radius: 999px;
  background: var(--video-number-bg);
  animation: vocab-wave 1.2s ease-in-out infinite;
  animation-delay: calc(var(--dot) * -0.1s);
}

/* ===== Animations ===== */
@keyframes vocab-rise {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes vocab-card {
  from { opacity: 0; transform: rotateY(-12deg) translateY(12px); }
  to   { opacity: 1; transform: rotateY(0) translateY(0); }
}

@keyframes vocab-wave {
  0%, 100% { transform: scaleY(0.62); opacity: 0.56; }
  50%      { transform: scaleY(1);    opacity: 1; }
}
</style>
