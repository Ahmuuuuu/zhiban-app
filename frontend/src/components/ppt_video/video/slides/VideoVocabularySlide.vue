<template>
  <section
    class="video-vocabulary-slide"
    :class="[`layout-${layoutSeed}`, { 'is-dense': vocabCards.length > 6 }]"
  >
    <div class="video-vocabulary-slide__header">
      <span>{{ slide.chapterTitle }}</span>
      <h2>{{ slide.title }}</h2>
      <p>{{ slide.summary }}</p>
    </div>

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
      <span>Scene Practice</span>
      <p v-html="renderMath(exampleText)"></p>
      <div>
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
</script>

<style scoped>
.video-vocabulary-slide {
  position: absolute;
  inset: 82px 54px 104px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 390px);
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-areas:
    "header scene"
    "deck scene";
  gap: 22px 28px;
  color: var(--video-text);
}

.video-vocabulary-slide.layout-1 {
  grid-template-columns: minmax(300px, 390px) minmax(0, 1fr);
  grid-template-areas:
    "scene header"
    "scene deck";
}

.video-vocabulary-slide.layout-2 {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(160px, 0.62fr) minmax(180px, 1fr);
  grid-template-areas:
    "header"
    "scene"
    "deck";
}

.video-vocabulary-slide.layout-3 {
  grid-template-columns: minmax(0, 0.86fr) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  grid-template-areas:
    "header deck"
    "scene deck";
}

.video-vocabulary-slide.layout-4 {
  grid-template-columns: minmax(0, 1fr) minmax(300px, 360px);
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-areas:
    "header header"
    "deck scene";
}

.video-vocabulary-slide__header {
  grid-area: header;
  display: grid;
  align-content: end;
  gap: 12px;
  animation: vocab-rise 0.58s ease both;
}

.video-vocabulary-slide__header span,
.scene-board > span {
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

.video-vocabulary-slide h2 {
  margin: 0;
  font-size: clamp(30px, 3.7vw, 54px);
  line-height: 1.12;
}

.video-vocabulary-slide__header p {
  max-width: 720px;
  margin: 0;
  color: var(--video-muted);
  font-size: clamp(13px, 1.02vw, 18px);
  line-height: 1.55;
}

.vocab-deck {
  grid-area: deck;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  align-content: start;
}

.video-vocabulary-slide.is-dense .vocab-deck {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.video-vocabulary-slide.layout-3 .vocab-deck {
  grid-template-columns: 1fr;
}

.video-vocabulary-slide.layout-4 .vocab-deck {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.vocab-deck article {
  min-height: 98px;
  padding: 17px;
  border-radius: 8px;
  border: 1px solid var(--video-card-border);
  background:
    radial-gradient(circle at 18% 18%, color-mix(in srgb, var(--video-warm, #ffd166) 22%, transparent), transparent 38%),
    var(--video-card-bg);
  display: grid;
  gap: 8px;
  box-shadow: 0 18px 42px var(--video-shadow);
  animation: vocab-card 0.62s ease both;
  animation-delay: calc(var(--delay) * 0.08s);
}

.video-vocabulary-slide.is-dense .vocab-deck article {
  min-height: 72px;
  padding: 11px;
  gap: 5px;
}

.video-vocabulary-slide.layout-1 .vocab-deck article {
  min-height: 76px;
  border-radius: 999px;
  grid-template-columns: minmax(90px, 0.44fr) minmax(0, 1fr);
  align-items: center;
}

.video-vocabulary-slide.layout-2 .vocab-deck article {
  border-radius: 8px 28px 8px 28px;
  transform-origin: center;
}

.video-vocabulary-slide.layout-2 .vocab-deck article:nth-child(odd) {
  transform: rotate(-1.4deg);
}

.video-vocabulary-slide.layout-2 .vocab-deck article:nth-child(even) {
  transform: rotate(1.2deg);
}

.video-vocabulary-slide.layout-3 .vocab-deck article {
  border-radius: 50%;
  aspect-ratio: 1.22;
  place-items: center;
  text-align: center;
}

.video-vocabulary-slide.layout-3.is-dense .vocab-deck article {
  aspect-ratio: auto;
  border-radius: 18px;
}

.video-vocabulary-slide.layout-4 .vocab-deck article {
  border-radius: 6px;
  clip-path: polygon(0 0, 92% 0, 100% 18%, 100% 100%, 0 100%);
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

.scene-board {
  grid-area: scene;
  position: relative;
  overflow: hidden;
  padding: 28px;
  border: 1px solid var(--video-card-border);
  border-radius: 8px;
  background:
    linear-gradient(140deg, color-mix(in srgb, var(--video-accent-soft, #6ec6ff) 20%, transparent), transparent 58%),
    var(--video-card-bg);
  display: grid;
  align-content: center;
  gap: 18px;
}

.video-vocabulary-slide.layout-1 .scene-board {
  border-radius: 30px 8px 30px 8px;
}

.video-vocabulary-slide.layout-2 .scene-board {
  border-radius: 999px;
  padding-inline: 56px;
}

.video-vocabulary-slide.layout-3 .scene-board {
  clip-path: polygon(4% 0, 100% 0, 96% 100%, 0 100%);
}

.video-vocabulary-slide.layout-4 .scene-board {
  border-radius: 50%;
  aspect-ratio: 1;
}

.scene-board p {
  margin: 0;
  color: var(--video-text);
  font-size: clamp(15px, 1.45vw, 28px);
  line-height: 1.42;
}

.scene-board div {
  position: absolute;
  inset: auto 24px 24px;
  height: 42px;
  display: flex;
  gap: 8px;
  align-items: end;
}

.scene-board i {
  width: 100%;
  max-width: 14px;
  height: calc(12px + var(--dot) * 5px);
  border-radius: 999px;
  background: var(--video-number-bg);
  color: var(--video-number-text);
  animation: vocab-wave 1.2s ease-in-out infinite;
  animation-delay: calc(var(--dot) * -0.1s);
}

@keyframes vocab-rise {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes vocab-card {
  from { opacity: 0; transform: rotateY(-12deg) translateY(12px); }
  to { opacity: 1; transform: rotateY(0) translateY(0); }
}

@keyframes vocab-wave {
  0%, 100% { transform: scaleY(0.62); opacity: 0.56; }
  50% { transform: scaleY(1); opacity: 1; }
}
</style>
