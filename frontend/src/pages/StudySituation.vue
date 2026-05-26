<template>
  <main class="study-panel">
    <header class="panel-header">
      <div class="header-title-row">
        <PageBackButton />
        <router-link class="home-pill" to="/">&#x8FD4;&#x56DE;&#x9996;&#x9875;</router-link>
        <div>
          <p class="eyebrow">Study Status</p>
          <h1>&#x5B66;&#x4E60;&#x60C5;&#x51B5;</h1>
          <p>&#x6C47;&#x603B;&#x8FD1;&#x671F;&#x5B66;&#x4E60;&#x72B6;&#x6001;&#xFF0C;&#x5FEB;&#x901F;&#x770B;&#x5230;&#x8FDB;&#x5EA6;&#x3001;&#x6D3B;&#x8DC3;&#x5EA6;&#x548C;&#x5F85;&#x52A0;&#x5F3A;&#x5185;&#x5BB9;&#x3002;</p>
        </div>
      </div>

      <UserAccountButton class="header-account" variant="home" logged-out-meta="&#x70B9;&#x51FB;&#x767B;&#x5F55;" />
    </header>

    <div class="dashboard-board">
      <section class="top-zone">
        <article class="profile-panel panel-card">
          <div class="section-title">
            <UserRound :size="18" />
            <h2>&#x4EBA;&#x7269;&#x753B;&#x50CF;</h2>
          </div>

          <div class="profile-body">
            <div class="avatar-frame">
              <img :src="avatarUrl" alt="avatar" />
            </div>

            <div class="radar-wrap">
              <svg viewBox="0 0 220 220" role="img" aria-label="profile radar">
                <polygon
                  v-for="ring in radarRings"
                  :key="ring"
                  :points="radarRingPoints(ring)"
                  class="radar-grid"
                  :class="{ muted: ring < 100 }"
                />
                <line
                  v-for="axis in radarAxes"
                  :key="axis.angle"
                  :x1="radarCenter"
                  :y1="radarCenter"
                  :x2="axis.x"
                  :y2="axis.y"
                  class="radar-axis"
                />
                <polygon :points="radarPoints" class="radar-score" />
                <text v-for="label in radarLabels" :key="label.text" :x="label.x" :y="label.y" text-anchor="middle">
                  <tspan :x="label.x" dy="-12" class="radar-value">{{ label.value }}</tspan>
                  <tspan :x="label.x" dy="13">{{ label.text }}</tspan>
                  <tspan :x="label.x" dy="13" class="radar-label-en">{{ label.en }}</tspan>
                </text>
              </svg>
            </div>
          </div>
        </article>

        <aside class="right-stack">
          <article class="duration-panel panel-card">
          <div class="section-title">
            <Clock3 :size="18" />
            <h2>&#x5B66;&#x4E60;&#x65F6;&#x957F;</h2>
          </div>
          <div class="duration-ring">
            <strong>{{ studyMinutes }}</strong>
            <span>min</span>
          </div>
          <p>&#x672C;&#x5468;&#x7D2F;&#x8BA1;&#xFF0C;&#x6BD4;&#x4E0A;&#x5468;&#x63D0;&#x5347; {{ weeklyGrowth }}%</p>
          </article>

          <article class="tag-panel panel-card">
          <div class="section-title">
            <BadgeCheck :size="18" />
            <h2>&#x4EBA;&#x7269;&#x753B;&#x50CF;&#x6807;&#x7B7E;</h2>
          </div>
          <div class="tag-list">
            <span v-for="tag in learnerTags" :key="tag">{{ tag }}</span>
          </div>
          </article>
        </aside>

        <article class="current-path-panel panel-card">
          <div class="section-title">
            <Route :size="18" />
            <h2>&#x6B63;&#x5728;&#x8FDB;&#x884C;&#x7684;&#x5B66;&#x4E60;&#x8DEF;&#x5F84;</h2>
          </div>
          <p v-if="!currentPaths.length" class="path-empty">&#x6682;&#x65E0;&#x6B63;&#x5728;&#x8FDB;&#x884C;&#x7684;&#x5B66;&#x4E60;&#x8DEF;&#x5F84;</p>
          <ol v-else class="path-list compact">
            <li v-for="item in currentPaths" :key="item.id">
              <router-link class="path-link" :to="{ name: 'learningPath', query: { pathId: item.id } }">
                <span>{{ item.index }}</span>
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.time }} · {{ item.score }}</p>
                  <div class="path-progress"><span :style="{ width: `${item.percent}%` }"></span></div>
                </div>
              </router-link>
            </li>
          </ol>
        </article>

        <article class="accuracy-panel panel-card">
          <div class="section-title">
            <TrendingUp :size="18" />
            <h2>&#x505A;&#x9898;&#x6B63;&#x786E;&#x7387;</h2>
          </div>
          <svg class="line-chart" viewBox="0 0 460 180" role="img" aria-label="accuracy line chart">
            <line x1="28" y1="22" x2="28" y2="146" />
            <line x1="28" y1="146" x2="432" y2="146" />
            <polyline :points="accuracyLine" />
            <circle v-for="point in accuracyPoints" :key="point.day" :cx="point.x" :cy="point.y" r="4" />
            <text v-for="point in accuracyPoints" :key="`${point.day}-label`" :x="point.x" y="168">{{ point.day }}</text>
          </svg>
        </article>
      </section>

      <section class="bottom-zone">
        <article class="path-panel panel-card">
          <div class="section-title">
            <Route :size="18" />
            <h2>&#x5DF2;&#x5B8C;&#x6210;&#x7684;&#x5B66;&#x4E60;&#x8DEF;&#x5F84;</h2>
          </div>
          <p v-if="!completedPaths.length" class="path-empty">&#x6682;&#x65E0;&#x5DF2;&#x5B8C;&#x6210;&#x5B66;&#x4E60;&#x8DEF;&#x5F84;</p>
          <ol v-else class="path-list">
            <li v-for="item in completedPaths" :key="item.id">
              <router-link class="path-link" :to="{ name: 'learningPath', query: { pathId: item.id } }">
                <span>{{ item.index }}</span>
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.time }} · {{ item.score }}</p>
                </div>
              </router-link>
            </li>
          </ol>
        </article>

        <div class="insight-stack">
          <article class="weak-panel panel-card">
            <div class="section-title">
              <Target :size="18" />
              <h2>&#x8584;&#x5F31;&#x77E5;&#x8BC6;&#x70B9;</h2>
            </div>
            <div class="weak-list">
              <div v-for="item in weakPoints" :key="item.name" class="weak-row">
                <div>
                  <strong>{{ item.name }}</strong>
                  <span>{{ item.tip }}</span>
                </div>
                <div class="weak-bar">
                  <span :style="{ width: `${item.value}%` }"></span>
                </div>
              </div>
            </div>
          </article>

          <article class="suggestion-panel panel-card">
            <div class="section-title">
              <Lightbulb :size="18" />
              <h2>&#x5B66;&#x4E60;&#x5EFA;&#x8BAE;</h2>
            </div>
            <ul>
              <li v-for="item in suggestions" :key="item">{{ item }}</li>
            </ul>
          </article>
        </div>

        <article class="feedback-panel panel-card">
          <div class="section-title">
            <MessageSquareText :size="18" />
            <h2>&#x8D44;&#x6E90;&#x4F7F;&#x7528;&#x53CD;&#x9988;</h2>
          </div>
          <div class="feedback-summary">
            <div v-for="item in resourceFeedback" :key="item.label">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </div>
          </div>
          <p>&#x8BB2;&#x89E3;&#x578B;&#x8D44;&#x6E90;&#x5B8C;&#x6210;&#x7387;&#x8F83;&#x9AD8;&#xFF0C;&#x5EFA;&#x8BAE;&#x5C06;&#x8584;&#x5F31;&#x77E5;&#x8BC6;&#x70B9;&#x4F18;&#x5148;&#x8F6C;&#x6210;&#x77ED;&#x8BB2;&#x4E49;&#x548C;&#x4E13;&#x9879;&#x7EC3;&#x4E60;&#x3002;</p>
        </article>
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  BadgeCheck,
  Clock3,
  Lightbulb,
  MessageSquareText,
  Route,
  Target,
  TrendingUp,
  UserRound
} from 'lucide-vue-next'
import { getPortraitRadar, getStudyStats } from '../api/apis'
import UserAccountButton from '../components/UserAccountButton.vue'
import PageBackButton from '../components/PageBackButton.vue'
import avatarUrl from '../assets/pic/study-pet-reference-cutout.png'

const zh = codes => codes.map(code => String.fromCharCode(code)).join('')

const studyMinutes = 486
const weeklyGrowth = 18

const learnerTags = [
  zh([0x7a33, 0x5b9a, 0x578b, 0x5b66, 0x4e60, 0x8005]),
  zh([0x56fe, 0x50cf, 0x8bb0, 0x5fc6, 0x5f3a]),
  zh([0x9002, 0x5408, 0x5206, 0x6bb5, 0x590d, 0x76d8]),
  zh([0x7ec3, 0x4e60, 0x53cd, 0x9988, 0x654f, 0x611f]),
  zh([0x5468, 0x672b, 0x6d3b, 0x8dc3])
]

const fallbackRadarData = [
  { key: 'focus', label: zh([0x4e13, 0x6ce8, 0x5ea6]), en: 'Focus', value: 82 },
  { key: 'initiative', label: zh([0x4e3b, 0x52a8, 0x6027]), en: 'Initiative', value: 68 },
  { key: 'review', label: zh([0x590d, 0x76d8, 0x529b]), en: 'Review', value: 74 },
  { key: 'completion', label: zh([0x5b8c, 0x6210, 0x5ea6]), en: 'Completion', value: 88 },
  { key: 'understanding', label: zh([0x7406, 0x89e3, 0x529b]), en: 'Understanding', value: 72 },
  { key: 'transfer', label: zh([0x8fc1, 0x79fb, 0x529b]), en: 'Transfer', value: 63 }
]
const radarData = ref(fallbackRadarData)
const radarEnglishMap = {
  memory: 'Memory',
  understanding: 'Understanding',
  application: 'Application',
  analysis: 'Analysis',
  breadth: 'Breadth',
  persistence: 'Persistence'
}

const radarAngles = [-90, -30, 30, 90, 150, 210]
const radarCenter = 110
const radarRadius = 72

const polarPoint = (angle, value) => {
  const rad = (Math.PI / 180) * angle
  const radius = radarRadius * (value / 100)
  return {
    x: Number((radarCenter + Math.cos(rad) * radius).toFixed(1)),
    y: Number((radarCenter + Math.sin(rad) * radius).toFixed(1))
  }
}

const radarRings = [100, 80, 60, 40, 20]
const radarRingPoints = value => radarAngles
  .map(angle => {
    const point = polarPoint(angle, value)
    return `${point.x},${point.y}`
  })
  .join(' ')
const radarAxes = radarAngles.map(angle => ({
  angle,
  ...polarPoint(angle, 100)
}))

const radarDots = computed(() => radarData.value.map((item, index) => ({
  ...item,
  ...polarPoint(radarAngles[index], item.value)
})))
const radarPoints = computed(() => radarDots.value.map(point => `${point.x},${point.y}`).join(' '))
const radarLabels = computed(() => radarData.value.map((item, index) => {
  const point = polarPoint(radarAngles[index], 134)
  return {
    text: item.label,
    en: item.en || radarEnglishMap[item.key] || item.key || '',
    value: item.value,
    x: point.x,
    y: point.y + 4
  }
}))

const unwrapApiData = result => result?.data?.data || result?.data || result

const normalizeRadarDimensions = result => {
  const raw = unwrapApiData(result) || {}
  const dimensions = Array.isArray(raw.dimensions)
    ? raw.dimensions
    : Array.isArray(raw.radar)
      ? raw.radar
      : Array.isArray(raw)
        ? raw
        : []

  return dimensions
    .map((item, index) => ({
      key: String(item.key || fallbackRadarData[index]?.key || ''),
      label: String(item.label || item.name || item.key || fallbackRadarData[index]?.label || ''),
      en: String(item.en || item.english || radarEnglishMap[item.key] || fallbackRadarData[index]?.en || ''),
      value: Math.max(0, Math.min(100, Math.round(Number(item.score ?? item.value ?? item.percent ?? 0))))
    }))
    .filter(item => item.label && Number.isFinite(item.value))
    .slice(0, 6)
}

const loadRadarData = async () => {
  try {
    const list = normalizeRadarDimensions(await getPortraitRadar())
    if (list.length >= 3) {
      radarData.value = list.length === 6 ? list : [...list, ...fallbackRadarData.slice(list.length)].slice(0, 6)
    }
  } catch (error) {
    console.warn('[StudySituation] load radar failed:', error)
  }
}

const accuracyData = [
  { day: zh([0x5468, 0x4e00]), value: 64 },
  { day: zh([0x5468, 0x4e8c]), value: 71 },
  { day: zh([0x5468, 0x4e09]), value: 69 },
  { day: zh([0x5468, 0x56db]), value: 78 },
  { day: zh([0x5468, 0x4e94]), value: 82 },
  { day: zh([0x5468, 0x516d]), value: 76 },
  { day: zh([0x5468, 0x65e5]), value: 86 }
]

const accuracyPoints = accuracyData.map((item, index) => ({
  ...item,
  x: 48 + index * 60,
  y: 146 - item.value * 1.28
}))
const accuracyLine = accuracyPoints.map(point => `${point.x},${point.y}`).join(' ')

const completedPaths = ref([])
const currentPaths = ref([])

const normalizePathCount = value => Math.max(0, Math.round(Number(value || 0)))
const pathFallbackTitle = zh([0x5b66, 0x4e60, 0x8def, 0x5f84])
const completedText = zh([0x5df2, 0x5b8c, 0x6210])
const nodeText = zh([0x4e2a, 0x8282, 0x70b9])
const progressText = zh([0x5b8c, 0x6210, 0x5ea6])

const normalizeLearningPaths = result => {
  const raw = unwrapApiData(result) || {}
  const paths = Array.isArray(raw.learning_paths)
    ? raw.learning_paths
    : Array.isArray(raw.learningPaths)
      ? raw.learningPaths
      : Array.isArray(raw.paths)
        ? raw.paths
        : []

  return paths
    .map(item => {
      const totalNodes = normalizePathCount(item.total_nodes ?? item.totalNodes)
      const completedNodes = normalizePathCount(item.completed_nodes ?? item.completedNodes)
      const progress = Number(item.progress ?? (totalNodes ? completedNodes / totalNodes : 0))

      return {
        id: item.path_id ?? item.pathId ?? item.id ?? `${item.goal || item.subject || item.title || ''}-${totalNodes}-${completedNodes}`,
        title: String(item.goal || item.subject || item.title || pathFallbackTitle),
        totalNodes,
        completedNodes,
        progress: Number.isFinite(progress) ? Math.max(0, Math.min(1, progress)) : 0
      }
    })
    .filter(item => item.id && (item.totalNodes > 0 || item.completedNodes > 0))
}

const formatPathCard = (item, index, isCompleted = false) => {
  const percent = Math.round(item.progress * 100)

  return {
    id: item.id,
    index: String(index + 1).padStart(2, '0'),
    title: item.title,
    time: `${item.completedNodes}/${item.totalNodes} ${nodeText}`,
    score: isCompleted ? completedText : `${progressText} ${percent}%`,
    percent
  }
}

const loadCompletedPaths = async () => {
  try {
    const paths = normalizeLearningPaths(await getStudyStats())
    const finished = paths.filter(item => item.totalNodes > 0 && item.completedNodes >= item.totalNodes)
    const inProgress = paths.filter(item => item.totalNodes > 0 && item.completedNodes < item.totalNodes)
    completedPaths.value = finished.map((item, index) => formatPathCard(item, index, true))
    currentPaths.value = inProgress.map((item, index) => formatPathCard(item, index)).slice(0, 2)
  } catch (error) {
    console.warn('[StudySituation] load completed paths failed:', error)
  }
}

const weakPoints = [
  {
    name: zh([0x4e92, 0x8865, 0x8272, 0x5e94, 0x7528]),
    tip: zh([0x6982, 0x5ff5, 0x53ef, 0x590d, 0x8ff0, 0xff0c, 0x5e94, 0x7528, 0x9898, 0x6ce2, 0x52a8, 0x8f83, 0x5927]),
    value: 68
  },
  {
    name: zh([0x660e, 0x5ea6, 0x5bf9, 0x6bd4]),
    tip: zh([0x5bb9, 0x6613, 0x5ffd, 0x7565, 0x753b, 0x9762, 0x5c42, 0x6b21, 0x5173, 0x7cfb]),
    value: 56
  },
  {
    name: zh([0x8272, 0x5f69, 0x5fc3, 0x7406, 0x8054, 0x60f3]),
    tip: zh([0x6848, 0x4f8b, 0x8fc1, 0x79fb, 0x9700, 0x8981, 0x66f4, 0x591a, 0x7d20, 0x6750]),
    value: 61
  }
]

const suggestions = [
  zh([0x6bcf, 0x5929, 0x5b89, 0x6392, 0x20, 0x31, 0x35, 0x20, 0x5206, 0x949f, 0x590d, 0x76d8, 0x9519, 0x9898, 0x3002]),
  zh([0x4f18, 0x5148, 0x5b66, 0x4e60, 0x660e, 0x5ea6, 0x5bf9, 0x6bd4, 0x76f8, 0x5173, 0x8d44, 0x6e90, 0x3002]),
  zh([0x7528, 0x4e00, 0x7ec4, 0x771f, 0x5b9e, 0x4f5c, 0x54c1, 0x505a, 0x8272, 0x5f69, 0x5206, 0x6790, 0x8f93, 0x51fa, 0x3002])
]

const resourceFeedback = [
  { label: zh([0x8d44, 0x6e90, 0x6253, 0x5f00, 0x7387]), value: '92%' },
  { label: zh([0x7ec3, 0x4e60, 0x5b8c, 0x6210, 0x7387]), value: '76%' },
  { label: zh([0x6536, 0x85cf, 0x8d44, 0x6599]), value: '18' }
]

onMounted(() => {
  loadRadarData()
  loadCompletedPaths()
})
</script>

<style scoped>
.study-panel {
  width: 100%;
  height: 100vh;
  min-height: 0;
  padding: 26px 34px 30px;
  color: #163f8f;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: hidden;
}

.panel-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.home-pill {
  min-height: 56px;
  padding: 0 22px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: #163f8f;
  text-decoration: none;
  font-size: 14px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  box-shadow: 0 12px 28px rgba(22, 63, 143, 0.08);
}

.home-pill,
.header-account {
  transform: translateY(-10px);
}

.eyebrow {
  margin: 0 0 6px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.panel-header h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.15;
}

.panel-header p:last-child {
  margin: 8px 0 0;
  color: #5f8fc3;
  font-size: 14px;
}

.dashboard-board {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px 18px 0;
  display: grid;
  gap: 18px;
}

.dashboard-board::-webkit-scrollbar {
  width: 8px;
}

.dashboard-board::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(95, 143, 195, 0.45);
}

.top-zone,
.bottom-zone {
  display: grid;
  gap: 16px;
}

.top-zone {
  grid-template-columns: minmax(280px, 0.42fr) minmax(520px, 1fr) minmax(330px, 0.42fr);
  grid-template-areas:
    "profile profile side"
    "current accuracy side";
  align-items: stretch;
}

.current-path-panel {
  grid-area: current;
}

.accuracy-panel {
  grid-area: accuracy;
}

.bottom-zone {
  grid-template-columns: minmax(280px, 0.42fr) minmax(520px, 1fr);
  grid-template-areas:
    "paths insight"
    "paths feedback";
}

.insight-stack {
  grid-area: insight;
  display: grid;
  grid-template-columns: minmax(300px, 1fr) minmax(260px, 0.82fr);
  gap: 16px;
}

.right-stack {
  grid-area: side;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(230px, 0.58fr) minmax(190px, 0.42fr);
  gap: 16px;
}

.panel-card {
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.94), rgba(237, 249, 252, 0.84)),
    #fafafa;
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
}

.profile-panel {
  grid-area: profile;
  min-height: 356px;
  padding: 22px;
}

.duration-panel {
  min-height: 0;
  padding: 20px;
}

.tag-panel {
  min-height: 0;
  padding: 20px;
}

.accuracy-panel {
  min-height: 220px;
  padding: 20px;
}

.current-path-panel {
  min-height: 220px;
  padding: 20px;
}

.path-panel {
  grid-area: paths;
  min-height: 430px;
  padding: 20px;
}

.weak-panel {
  min-height: 172px;
  padding: 20px;
}

.suggestion-panel {
  min-height: 172px;
  padding: 20px;
}

.feedback-panel {
  grid-area: feedback;
  min-height: 170px;
  padding: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #163f8f;
}

.section-title h2 {
  margin: 0;
  font-size: 16px;
  line-height: 1.3;
}

.profile-body {
  min-height: 276px;
  margin-top: 16px;
  display: grid;
  grid-template-columns: 230px minmax(280px, 1fr);
  align-items: center;
  gap: 28px;
}

.avatar-frame {
  width: 210px;
  aspect-ratio: 1;
  margin-left: 54px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 50%;
  background: #ffffff;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.avatar-frame img {
  width: 90%;
  height: 90%;
  object-fit: contain;
}

.radar-wrap {
  min-width: 0;
  display: flex;
  justify-content: center;
}

.radar-wrap svg {
  width: min(100%, 320px);
  height: auto;
  overflow: visible;
}

.radar-grid {
  fill: none;
  stroke: rgba(95, 143, 195, 0.36);
  stroke-width: 0.8;
}

.radar-axis {
  stroke: rgba(95, 143, 195, 0.24);
  stroke-width: 0.7;
}

.radar-score {
  fill: rgba(95, 143, 195, 0.24);
  stroke: #163f8f;
  stroke-width: 1.25;
}

.radar-wrap text,
.line-chart text {
  fill: #2f6698;
  font-size: 10px;
  font-weight: 400;
}

.radar-wrap .radar-value {
  fill: #0f3478;
  font-size: 12px;
  font-weight: 500;
}

.radar-wrap .radar-label-en {
  fill: rgba(47, 102, 152, 0.86);
  font-size: 6.8px;
  font-weight: 300;
}

.duration-ring {
  width: min(220px, 100%);
  aspect-ratio: 1;
  margin: 22px auto 0;
  border: 1px solid rgba(95, 143, 195, 0.38);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.54);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.duration-ring strong {
  color: #163f8f;
  font-size: 54px;
  line-height: 1;
}

.duration-ring span {
  color: #5f8fc3;
  font-size: 16px;
  font-weight: 900;
}

.duration-panel p,
.feedback-panel p {
  margin: 14px 0 0;
  color: #5f8fc3;
  font-size: 13px;
  line-height: 1.7;
}

.tag-list {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag-list span {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(22, 63, 143, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.76);
  color: #163f8f;
  font-size: 13px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.line-chart {
  width: 100%;
  height: 170px;
  margin-top: 14px;
}

.line-chart line {
  stroke: rgba(95, 143, 195, 0.32);
  stroke-width: 1;
}

.line-chart polyline {
  fill: none;
  stroke: #163f8f;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.line-chart circle {
  fill: #ffffff;
  stroke: #163f8f;
  stroke-width: 2;
}

.path-list {
  margin: 22px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 14px;
}

.path-list.compact {
  margin-top: 16px;
  gap: 10px;
}

.path-list li {
  min-height: 76px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.7);
  overflow: hidden;
}

.path-link {
  min-height: 76px;
  padding: 13px;
  color: inherit;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-list.compact .path-link {
  min-height: 62px;
  padding: 12px;
}

.path-link > div {
  min-width: 0;
  flex: 1;
}

.path-list li:hover {
  border-color: rgba(22, 63, 143, 0.26);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 12px 24px rgba(22, 63, 143, 0.08);
}

.path-link > span {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #163f8f;
  color: #ffffff;
  font-size: 12px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.path-list strong,
.weak-row strong {
  color: #163f8f;
  font-size: 14px;
  line-height: 1.35;
}

.path-list p {
  margin: 6px 0 0;
  color: #5f8fc3;
  font-size: 12px;
}

.path-progress {
  height: 5px;
  margin-top: 8px;
  border-radius: 999px;
  background: rgba(201, 220, 233, 0.68);
  overflow: hidden;
}

.path-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #163f8f;
}

.path-empty {
  margin: 24px 0 0;
  padding: 18px;
  border: 1px dashed rgba(95, 143, 195, 0.42);
  border-radius: 8px;
  color: #5f8fc3;
  font-size: 13px;
  text-align: center;
  background: rgba(255, 255, 255, 0.52);
}

.weak-list {
  margin-top: 18px;
  display: grid;
  gap: 14px;
}

.weak-row {
  display: grid;
  grid-template-columns: minmax(150px, 0.55fr) minmax(180px, 1fr);
  align-items: center;
  gap: 14px;
}

.weak-row div:first-child {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.weak-row span {
  color: #5f8fc3;
  font-size: 12px;
  line-height: 1.45;
}

.weak-bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(201, 220, 233, 0.68);
  overflow: hidden;
}

.weak-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #163f8f;
}

.suggestion-panel ul {
  margin: 16px 0 0;
  padding-left: 18px;
  color: #163f8f;
  font-size: 13px;
  line-height: 1.8;
}

.suggestion-panel li + li {
  margin-top: 8px;
}

.feedback-summary {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.feedback-summary div {
  min-height: 74px;
  padding: 12px 8px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.7);
  display: grid;
  place-items: center;
  text-align: center;
}

.feedback-summary strong {
  color: #163f8f;
  font-size: 22px;
  line-height: 1;
}

.feedback-summary span {
  color: #5f8fc3;
  font-size: 11px;
  font-weight: 800;
}

@media (max-width: 1120px) {
  .top-zone,
  .bottom-zone {
    grid-template-columns: 1fr;
    grid-template-areas: none;
  }

  .right-stack,
  .insight-stack,
  .profile-panel,
  .duration-panel,
  .tag-panel,
  .current-path-panel,
  .accuracy-panel,
  .path-panel,
  .weak-panel,
  .suggestion-panel,
  .feedback-panel {
    grid-area: auto;
  }

  .right-stack {
    grid-template-rows: none;
  }

  .insight-stack {
    grid-template-columns: 1fr;
  }

  .path-panel {
    min-height: 0;
  }
}

@media (max-width: 720px) {
  .study-panel {
    height: auto;
    min-height: 100vh;
    padding: 20px;
    overflow: visible;
  }

  .panel-header,
  .header-title-row {
    flex-direction: column;
  }

  .dashboard-board {
    overflow: visible;
    padding-right: 0;
  }

  .profile-body,
  .weak-row,
  .feedback-summary {
    grid-template-columns: 1fr;
  }

  .avatar-frame {
    margin: 0 auto;
  }

  .duration-ring strong {
    font-size: 44px;
  }
}
</style>
