<template>
  <section
    class="video-keypoint-slide"
    :class="`layout-${layoutSeed}`"
  >
    <div class="video-keypoint-slide__hero">
      <span>{{ slide.chapterTitle }}</span>
      <h2>{{ slide.title }}</h2>
      <p>{{ slide.summary }}</p>
    </div>

    <div class="video-keypoint-slide__cards">
      <article
        v-for="(item, index) in displayItems"
        :key="`${index}-${item}`"
        :style="{ '--delay': index }"
        :class="{ featured: index === 0 }"
      >
        <b>{{ index + 1 }}</b>
        <span v-html="renderMath(item)"></span>
      </article>
    </div>

    <div class="video-keypoint-slide__visual">
      <div class="visual-focus">
        <span
          v-for="index in 4"
          :key="index"
          :style="{ '--line': index }"
        ></span>
      </div>
      <div class="term-cloud">
        <b
          v-for="(term, index) in terms"
          :key="term"
          :style="{ '--delay': index }"
        >{{ term }}</b>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath } from '../../../../utils/renderMath'
import { getSlideTerms } from './videoSlideClassifier'

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

const displayItems = computed(() => {
  const items = Array.isArray(props.slide.items) ? props.slide.items : []
  return items.length ? items.slice(0, 3) : [props.slide.summary].filter(Boolean)
})

const terms = computed(() => getSlideTerms(props.slide))
</script>

<style scoped>
.video-keypoint-slide {
  position: absolute;
  inset: 82px 54px 104px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 390px);
  grid-template-rows: minmax(0, 0.72fr) minmax(160px, 0.9fr);
  grid-template-areas:
    "hero visual"
    "cards visual";
  gap: 22px 28px;
  color: var(--video-text);
}

.video-keypoint-slide.layout-1 {
  grid-template-columns: minmax(300px, 390px) minmax(0, 1fr);
  grid-template-areas:
    "visual hero"
    "visual cards";
}

.video-keypoint-slide.layout-2 {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(120px, 0.52fr) minmax(180px, 0.72fr);
  grid-template-areas:
    "hero"
    "visual"
    "cards";
}

.video-keypoint-slide.layout-3 {
  grid-template-columns: minmax(0, 0.72fr) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  grid-template-areas:
    "hero cards"
    "visual cards";
}

.video-keypoint-slide.layout-4 {
  grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-areas:
    "hero hero"
    "cards visual";
}

.video-keypoint-slide.layout-3 .video-keypoint-slide__cards {
  grid-template-columns: 1fr;
  align-content: center;
}

.video-keypoint-slide.layout-4 .video-keypoint-slide__cards {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-content: start;
}

.video-keypoint-slide__hero {
  grid-area: hero;
  display: flex;
  flex-direction: column;
  justify-content: end;
  gap: 14px;
  animation: slide-rise 0.64s ease both;
}

.video-keypoint-slide__hero > span {
  width: fit-content;
  min-height: 30px;
  padding: 0 11px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  display: inline-flex;
  align-items: center;
  color: var(--video-soft);
  font-size: 12px;
  font-weight: 900;
  backdrop-filter: blur(10px);
}

.video-keypoint-slide h2 {
  max-width: 760px;
  margin: 0;
  font-size: clamp(30px, 3.8vw, 56px);
  line-height: 1.12;
  text-shadow: 0 4px 24px var(--video-shadow);
}

.video-keypoint-slide h2::after {
  content: "";
  display: block;
  width: min(520px, 70%);
  height: 4px;
  margin-top: 20px;
  border-radius: 999px;
  background: var(--video-line);
}

.video-keypoint-slide__hero p {
  max-width: 720px;
  margin: 0;
  color: var(--video-muted);
  font-size: clamp(15px, 1.2vw, 19px);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}

.video-keypoint-slide__cards {
  grid-area: cards;
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.video-keypoint-slide__cards article {
  min-height: 0;
  padding: 16px 18px;
  border: 1px solid var(--video-card-border);
  border-radius: 8px;
  background: var(--video-card-bg);
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  backdrop-filter: blur(12px);
  box-shadow: 0 18px 42px var(--video-shadow);
  animation: card-pop 0.52s ease both;
  animation-delay: calc(var(--delay) * 0.09s + 0.12s);
}

.video-keypoint-slide__cards article.featured {
  background: var(--video-card-strong);
}

.video-keypoint-slide__cards b {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: var(--video-number-bg);
  color: var(--video-number-text);
  display: grid;
  place-items: center;
}

.video-keypoint-slide__cards span {
  color: var(--video-muted);
  font-size: clamp(15px, 1.18vw, 20px);
  line-height: 1.48;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.video-keypoint-slide__visual {
  grid-area: visual;
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--video-card-border);
  border-radius: 8px;
  background: var(--video-card-bg);
  box-shadow: 0 20px 52px var(--video-shadow);
  backdrop-filter: blur(14px);
  animation: panel-in 0.72s ease both;
}

.visual-focus {
  position: absolute;
  left: 28px;
  right: 28px;
  top: 36px;
  height: 46%;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  background:
    linear-gradient(rgba(255, 255, 255, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 22px 22px;
  overflow: hidden;
}

.visual-focus::after {
  content: "";
  position: absolute;
  inset: 0;
  background: #ffffff;
  opacity: 0.14;
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
}

.term-cloud b {
  min-height: 30px;
  padding: 0 11px;
  border: 1px solid var(--video-card-border);
  border-radius: 999px;
  background: var(--video-chip-bg);
  color: var(--video-chip-text);
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
  animation: term-float 3.2s ease-in-out infinite;
  animation-delay: calc(var(--delay) * -0.18s);
}

@keyframes slide-rise {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes card-pop {
  from { opacity: 0; transform: translateY(14px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes panel-in {
  from { opacity: 0; transform: translateX(18px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes term-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

@keyframes visual-scan {
  0%, 25% { transform: translateX(-82%); }
  70%, 100% { transform: translateX(82%); }
}

@keyframes visual-line {
  0%, 100% { opacity: 0.42; transform: scaleX(0.86); transform-origin: left; }
  50% { opacity: 0.9; transform: scaleX(1); transform-origin: left; }
}

@media (max-width: 980px) {
  .video-keypoint-slide {
    inset: 72px 24px 104px;
    grid-template-columns: 1fr;
    grid-template-rows: auto auto minmax(160px, 1fr);
    grid-template-areas:
      "hero"
      "cards"
      "visual";
  }
}
</style>
