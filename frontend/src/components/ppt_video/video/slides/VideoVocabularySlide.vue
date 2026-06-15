<template>
  <section class="video-vocabulary-slide">
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
  }
})

const vocabCards = computed(() => {
  const items = Array.isArray(props.slide.items) ? props.slide.items : []
  const cards = []
  items.forEach(item => {
    const text = String(item || '')
    const pairs = text.match(/[A-Za-z][A-Za-z-]{2,}(?:\s*\([^)]{1,18}\)|（[^）]{1,18}）)?/g) || []
    pairs.slice(0, 3).forEach(pair => {
      const word = pair.replace(/[（(].*$/, '').trim()
      const meaning = pair.match(/[（(]([^）)]+)[）)]/)?.[1] || '重点词汇'
      cards.push({ word, meaning })
    })
  })
  return cards.length ? cards.slice(0, 6) : [{ word: props.slide.title, meaning: '核心表达' }]
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
  color: #fff;
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
  color: rgba(215, 242, 246, 0.92);
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
  color: rgba(235, 246, 255, 0.76);
  font-size: clamp(15px, 1.2vw, 19px);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.vocab-deck {
  grid-area: deck;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  align-content: start;
}

.vocab-deck article {
  min-height: 98px;
  padding: 17px;
  border-radius: 8px;
  border: 1px solid rgba(220, 240, 255, 0.18);
  background: rgba(255, 255, 255, 0.14);
  display: grid;
  gap: 8px;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.16);
  animation: vocab-card 0.62s ease both;
  animation-delay: calc(var(--delay) * 0.08s);
}

.vocab-deck b {
  font-size: clamp(21px, 2vw, 32px);
  line-height: 1;
}

.vocab-deck span {
  color: rgba(235, 246, 255, 0.74);
  font-size: 14px;
}

.scene-board {
  grid-area: scene;
  position: relative;
  overflow: hidden;
  padding: 28px;
  border: 1px solid rgba(220, 240, 255, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  display: grid;
  align-content: center;
  gap: 18px;
}

.scene-board p {
  margin: 0;
  color: rgba(245, 250, 255, 0.88);
  font-size: clamp(22px, 2.4vw, 34px);
  line-height: 1.4;
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
  background: #ffffff;
  color: #1f63d6;
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
