<template>
  <section class="video-intro-slide">
    <div class="intro-profile">
      <span class="intro-kicker">学习画像</span>
      <h2>{{ learnerTitle }}</h2>
      <p>{{ introText }}</p>
      <div class="profile-metrics">
        <article
          v-for="(metric, index) in metrics"
          :key="metric.label"
          :style="{ '--delay': index }"
        >
          <b>{{ metric.value }}</b>
          <span>{{ metric.label }}</span>
        </article>
      </div>
    </div>

    <div class="intro-relation">
      <span class="intro-kicker">课程关系</span>
      <div class="relation-map">
        <i class="node node--learner">画像</i>
        <i class="node node--course">课程</i>
        <i class="node node--goal">目标</i>
        <span class="link link--one"></span>
        <span class="link link--two"></span>
        <span class="pulse"></span>
      </div>
      <div class="relation-tags">
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
import { getSlideTerms } from './videoSlideClassifier'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  }
})

const learnerTitle = computed(() => props.slide.title || '课程导入')
const introText = computed(() => props.slide.summary || '根据你的学习画像，把课程内容拆成更容易进入的学习路径。')
const terms = computed(() => getSlideTerms(props.slide).slice(0, 6))
const metrics = computed(() => [
  { value: '01', label: props.slide.chapterTitle || '课程起点' },
  { value: String((props.slide.items || []).length || 3).padStart(2, '0'), label: '关键线索' },
  { value: 'AI', label: '个性匹配' }
])
</script>

<style scoped>
.video-intro-slide {
  position: absolute;
  inset: 86px 58px 112px;
  display: grid;
  grid-template-columns: minmax(0, 0.94fr) minmax(320px, 0.76fr);
  gap: 34px;
  color: var(--video-text);
}

.intro-profile,
.intro-relation {
  min-width: 0;
  border: 1px solid var(--video-card-border);
  border-radius: 28px 8px 28px 8px;
  background:
    radial-gradient(circle at 18% 16%, color-mix(in srgb, var(--video-warm, #ffd166) 18%, transparent), transparent 34%),
    var(--video-card-bg);
  box-shadow: 0 24px 58px var(--video-shadow);
  backdrop-filter: blur(16px);
}

.intro-profile {
  padding: clamp(28px, 4vw, 56px);
  display: grid;
  align-content: center;
  gap: 22px;
  animation: intro-profile 0.72s ease both;
}

.intro-kicker {
  width: fit-content;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid var(--video-card-border);
  border-radius: 999px;
  background: var(--video-chip-bg);
  color: var(--video-soft);
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 900;
}

.intro-profile h2 {
  max-width: 760px;
  margin: 0;
  font-size: clamp(38px, 5vw, 76px);
  line-height: 1.04;
}

.intro-profile p {
  max-width: 780px;
  margin: 0;
  color: var(--video-muted);
  font-size: clamp(14px, 1.18vw, 22px);
  line-height: 1.52;
}

.profile-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.profile-metrics article {
  min-height: 92px;
  padding: 16px;
  border: 1px solid var(--video-card-border);
  border-radius: 999px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--video-accent, #2f7de1) 18%, transparent), transparent),
    var(--video-card-strong);
  display: grid;
  align-content: center;
  gap: 6px;
  animation: metric-in 0.5s ease both;
  animation-delay: calc(var(--delay) * 0.1s + 0.18s);
}

.profile-metrics article:nth-child(2) {
  border-radius: 50%;
  aspect-ratio: 1;
}

.profile-metrics article:nth-child(3) {
  border-radius: 8px 28px 8px 28px;
}

.profile-metrics b {
  color: var(--video-number-text);
  font-size: 24px;
  line-height: 1;
}

.profile-metrics span {
  color: var(--video-muted);
  font-size: 13px;
  font-weight: 800;
}

.intro-relation {
  position: relative;
  padding: 28px;
  display: grid;
  grid-template-rows: auto minmax(240px, 1fr) auto;
  gap: 18px;
  overflow: hidden;
  animation: intro-map 0.72s ease both;
}

.intro-relation::before {
  content: "";
  position: absolute;
  right: -36px;
  top: -36px;
  width: 138px;
  height: 138px;
  border: 1px solid var(--video-card-border);
  border-radius: 50%;
  background: color-mix(in srgb, var(--video-accent-soft, #6ec6ff) 18%, transparent);
  animation: orbit-soft 5.6s ease-in-out infinite;
}

.relation-map {
  position: relative;
  min-height: 300px;
}

.node {
  position: absolute;
  width: 88px;
  height: 88px;
  border: 1px solid var(--video-card-border);
  border-radius: 50%;
  background:
    radial-gradient(circle at 32% 26%, var(--video-accent-soft, #6ec6ff), transparent 32%),
    var(--video-number-bg);
  color: var(--video-number-text);
  display: grid;
  place-items: center;
  font-style: normal;
  font-weight: 900;
  box-shadow: 0 18px 36px var(--video-shadow);
  animation: node-float 3.6s ease-in-out infinite;
}

.node--course {
  border-radius: 26px 50% 50% 26px;
}

.node--goal {
  clip-path: polygon(50% 0, 100% 34%, 82% 100%, 18% 100%, 0 34%);
}

.node--learner {
  left: 8%;
  top: 34%;
}

.node--course {
  right: 8%;
  top: 18%;
  animation-delay: -0.7s;
}

.node--goal {
  right: 18%;
  bottom: 10%;
  animation-delay: -1.4s;
}

.link {
  position: absolute;
  height: 2px;
  background: var(--video-line);
  transform-origin: left;
  opacity: 0.7;
}

.link--one {
  left: 25%;
  top: 45%;
  width: 48%;
  transform: rotate(-16deg);
}

.link--two {
  left: 28%;
  top: 56%;
  width: 45%;
  transform: rotate(22deg);
}

.pulse {
  position: absolute;
  left: 50%;
  top: 49%;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--video-line);
  animation: pulse-travel 2.4s ease-in-out infinite;
}

.relation-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.relation-tags b {
  min-height: 30px;
  padding: 0 11px;
  border: 1px solid var(--video-card-border);
  border-radius: 999px;
  background: var(--video-chip-bg);
  color: var(--video-chip-text);
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  animation: term-float 3.2s ease-in-out infinite;
  animation-delay: calc(var(--delay) * -0.18s);
}

@keyframes intro-profile {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes intro-map {
  from { opacity: 0; transform: translateX(18px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes metric-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes node-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-9px); }
}

@keyframes pulse-travel {
  0% { transform: translate(-130px, -34px) scale(0.65); opacity: 0; }
  32% { opacity: 1; }
  100% { transform: translate(118px, 62px) scale(1); opacity: 0; }
}

@keyframes orbit-soft {
  0%, 100% { transform: translate3d(0, 0, 0) scale(0.92); opacity: 0.34; }
  50% { transform: translate3d(-18px, 20px, 0) scale(1.08); opacity: 0.62; }
}

@keyframes term-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
</style>
