<template>
  <main class="study-panel">
    <div class="page-bg-deco" aria-hidden="true">
      <span class="sweep sweep-one"></span>
      <span class="sweep sweep-two"></span>
    </div>
    <header class="panel-header">
      <div class="header-title-row">
        <div>
          <p class="eyebrow">Study Status</p>
          <h1>&#x5B66;&#x4E60;&#x60C5;&#x51B5;</h1>
          <p>&#x6C47;&#x603B;&#x8FD1;&#x671F;&#x5B66;&#x4E60;&#x72B6;&#x6001;&#xFF0C;&#x5FEB;&#x901F;&#x770B;&#x5230;&#x8FDB;&#x5EA6;&#x3001;&#x6D3B;&#x8DC3;&#x5EA6;&#x548C;&#x5F85;&#x52A0;&#x5F3A;&#x5185;&#x5BB9;&#x3002;</p>
        </div>
      </div>

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
              <img :src="displayAvatarUrl" alt="avatar" />
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
          <p>{{ studyTimeNote }}</p>
          </article>

          <article class="tag-panel panel-card">
          <div class="section-title">
            <BadgeCheck :size="18" />
            <h2>&#x4EBA;&#x7269;&#x753B;&#x50CF;&#x6807;&#x7B7E;</h2>
          </div>
          <div class="tag-list">
            <span v-for="tag in learnerTags" :key="tag">{{ tag }}</span>
          </div>
          <div v-if="knowledgeDistribution.length" class="mini-donut">
            <SimpleChart type="donut" :data="knowledgeDistribution" :size="150" unit="知识点" />
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
            <li v-for="(item, idx) in currentPaths" :key="item.id">
              <router-link class="path-link" :to="{ name: 'learningPath', query: { pathId: item.id } }">
                <span :style="{ background: progressBarColors[idx % progressBarColors.length] }">{{ item.index }}</span>
                <div>
                  <strong>{{ item.title }}</strong>
                  <p v-if="item.meta" class="path-meta">{{ item.meta }}</p>
                  <p>{{ item.time }} · {{ item.score }}</p>
                  <div class="path-progress"><span :style="{ width: `${item.percent}%`, background: progressBarColors[index % progressBarColors.length] }"></span></div>
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
          <p class="accuracy-summary">{{ accuracySummary }}</p>
          <svg class="line-chart" viewBox="0 0 460 180" role="img" aria-label="accuracy line chart">
            <g v-for="tick in accuracyTicks" :key="tick.value" class="chart-tick">
              <line :x1="chartLeft" :y1="tick.y" :x2="chartRight" :y2="tick.y" />
              <text :x="chartLeft - 10" :y="tick.y + 4" text-anchor="end">{{ tick.value }}%</text>
            </g>
            <line :x1="chartLeft" :y1="chartTop" :x2="chartLeft" :y2="chartBottom" class="chart-axis" />
            <line :x1="chartLeft" :y1="chartBottom" :x2="chartRight" :y2="chartBottom" class="chart-axis" />
            <polyline :points="accuracyLine" />
            <circle v-for="point in accuracyPoints" :key="`${point.day}-dot`" class="chart-point-dot" :cx="point.x" :cy="point.y" r="3" />
            <text v-for="point in accuracyPoints" :key="`${point.day}-label`" :x="point.x" y="168" text-anchor="middle">{{ point.day }}</text>
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
            <li v-for="(item, idx) in completedPaths" :key="item.id">
              <router-link class="path-link" :to="{ name: 'learningPath', query: { pathId: item.id } }">
                <span :style="{ background: progressBarColors[idx % progressBarColors.length] }">{{ item.index }}</span>
                <div>
                  <strong>{{ item.title }}</strong>
                  <p v-if="item.meta" class="path-meta">{{ item.meta }}</p>
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
            <p v-if="!weakPoints.length" class="path-empty">&#x6682;&#x65E0;&#x8584;&#x5F31;&#x77E5;&#x8BC6;&#x70B9;</p>
            <div v-else class="weak-list">
              <div v-for="item in weakPoints" :key="item.name" class="weak-row">
                <div>
                  <strong>{{ item.name }}</strong>
                  <span>{{ item.tip }}</span>
                </div>
                <div class="weak-bar">
                  <span :style="{ width: `${item.value}%`, background: progressBarColors[index % progressBarColors.length] }"></span>
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
            <p v-if="!suggestions.length" class="path-empty">&#x6682;&#x65E0;&#x5B66;&#x4E60;&#x5EFA;&#x8BAE;</p>
          </article>
        </div>

        <article class="feedback-panel panel-card">
          <div class="section-title">
            <MessageSquareText :size="18" />
            <h2>&#x8D44;&#x6E90;&#x4F7F;&#x7528;&#x53CD;&#x9988;</h2>
          </div>
          <div class="feedback-chart-row">
            <div class="feedback-summary">
              <div v-for="(item, idx) in resourceFeedback" :key="item.label" class="feedback-stat-card" :style="{ borderTopColor: progressBarColors[idx % progressBarColors.length] }">
                <strong :style="{ color: progressBarColors[idx % progressBarColors.length] }">{{ item.value }}</strong>
                <span>{{ item.label }}</span>
              </div>
            </div>
            <div v-if="resourceChartData.length" class="feedback-bar">
              <SimpleChart type="hbar" :data="resourceChartData" :width="280" :height="140" />
            </div>
          </div>
          <p>{{ resourceFeedbackText }}</p>
        </article>
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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
import SimpleChart from '../components/SimpleChart.vue'
import { getLearningGuidance, getPortrait, getPortraitRadar, getStudyCollections, getStudyExamWeekly, getStudyPathStats, getStudyStats, getUserProfile, normalizeAvatarUrl } from '../api/apis'

import avatarUrl from '../assets/pic/study-pet-reference-cutout.png'

const zh = codes => codes.map(code => String.fromCharCode(code)).join('')

const userAvatarUrl = ref(normalizeAvatarUrl(localStorage.getItem('avatar') || ''))
const displayAvatarUrl = computed(() => userAvatarUrl.value || avatarUrl)

const normalizeProfile = result => result?.data || result?.user || result || {}

const loadUserAvatar = async () => {
  try {
    const profile = normalizeProfile(await getUserProfile())
    userAvatarUrl.value = normalizeAvatarUrl(profile.avatar || localStorage.getItem('avatar') || '')
    if (profile.avatar) {
      localStorage.setItem('avatar', profile.avatar)
    }
  } catch {
    userAvatarUrl.value = normalizeAvatarUrl(localStorage.getItem('avatar') || '')
  }
}

const handleAvatarUpdated = event => {
  userAvatarUrl.value = normalizeAvatarUrl(event?.detail?.avatar || localStorage.getItem('avatar') || '')
}

const studyMinutes = ref(0)
const studyTimeNote = ref(zh([0x672c, 0x5468, 0x6682, 0x65e0, 0x5b66, 0x4e60, 0x65f6, 0x957f, 0x8bb0, 0x5f55]))

const learnerTags = ref([])

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

const formatMonthDay = date => `${date.getMonth() + 1}/${date.getDate()}`
const buildRecentDateLabels = () => {
  const today = new Date()
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today)
    date.setDate(today.getDate() - (6 - index))
    return {
      day: formatMonthDay(date),
      value: 0
    }
  })
}

const fallbackAccuracyData = buildRecentDateLabels()

const accuracyData = ref(fallbackAccuracyData)
const accuracySummary = ref(zh([0x6b63, 0x5728, 0x52a0, 0x8f7d, 0x6700, 0x8fd1, 0x37, 0x5929, 0x6b63, 0x786e, 0x7387]))
const chartLeft = 56
const chartRight = 432
const chartTop = 22
const chartBottom = 146
const chartHeight = chartBottom - chartTop
const accuracyTicks = [100, 75, 50, 25, 0].map(value => ({
  value,
  y: chartBottom - (value / 100) * chartHeight
}))
const accuracyPoints = computed(() => accuracyData.value.map((item, index) => ({
  ...item,
  x: chartLeft + 24 + index * ((chartRight - chartLeft - 48) / 6),
  y: chartBottom - (Math.max(0, Math.min(100, item.value)) / 100) * chartHeight
})))
const accuracyLine = computed(() => accuracyPoints.value.map(point => `${point.x},${point.y}`).join(' '))

const formatAccuracyDate = value => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return formatMonthDay(date)
}

const normalizeWeeklyAccuracy = result => {
  const raw = unwrapApiData(result) || {}
  const daily = Array.isArray(raw.daily) ? raw.daily : Array.isArray(raw) ? raw : []
  return {
    points: daily
    .map(item => {
      const score = Number(item.accuracy ?? item.correct_rate ?? item.correctRate ?? item.percentage ?? item.score)
      const normalized = score <= 1 ? score * 100 : score
      return {
        day: formatAccuracyDate(item.date || item.day || item.created_at || item.createdAt),
        value: Math.round(Math.max(0, Math.min(100, Number.isFinite(normalized) ? normalized : 0))),
        time: item.date || item.day || item.created_at || item.createdAt || ''
      }
    })
    .filter(item => item.day)
    .sort((a, b) => new Date(a.time) - new Date(b.time))
    .slice(-7),
    total: Number(raw.week_total ?? raw.weekTotal ?? daily.reduce((sum, item) => sum + Number(item.total || 0), 0)),
    correct: Number(raw.week_correct ?? raw.weekCorrect ?? daily.reduce((sum, item) => sum + Number(item.correct || 0), 0)),
    accuracy: Number(raw.week_accuracy ?? raw.weekAccuracy ?? 0)
  }
}

const completedPaths = ref([])
const currentPaths = ref([])

const normalizePathCount = value => Math.max(0, Math.round(Number(value || 0)))
const normalizePathPercent = value => {
  const number = Number(value || 0)
  if (!Number.isFinite(number)) return 0
  return Math.max(0, Math.min(1, number > 1 ? number / 100 : number))
}
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
      const progressData = item.progress && typeof item.progress === 'object' ? item.progress : {}
      const studyTime = item.study_time || item.studyTime || {}
      const weakList = Array.isArray(item.weak_points)
        ? item.weak_points
        : Array.isArray(item.weakPoints)
          ? item.weakPoints
          : []
      const totalNodes = normalizePathCount(item.total_nodes ?? item.totalNodes ?? progressData.total_nodes ?? progressData.totalNodes)
      const completedNodes = normalizePathCount(item.completed_nodes ?? item.completedNodes ?? progressData.completed_nodes ?? progressData.completedNodes)
      const progressValue = progressData.percentage ?? progressData.percent ?? item.progress ?? (totalNodes ? completedNodes / totalNodes : 0)

      return {
        id: item.path_id ?? item.pathId ?? item.id ?? `${item.goal || item.subject || item.title || ''}-${totalNodes}-${completedNodes}`,
        title: String(item.goal || item.subject || item.title || pathFallbackTitle),
        totalNodes,
        completedNodes,
        progress: normalizePathPercent(progressValue),
        currentNode: String(item.current_node || item.currentNode || progressData.current_node || progressData.currentNode || ''),
        weekMinutes: formatSecondsToMinutes(studyTime.week_seconds ?? studyTime.weekSeconds),
        totalMinutes: formatSecondsToMinutes(studyTime.total_seconds ?? studyTime.totalSeconds),
        weakCount: weakList.length
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
    percent,
    meta: [
      item.currentNode ? `${zh([0x5f53, 0x524d])} ${item.currentNode}` : '',
      item.weekMinutes ? `${zh([0x672c, 0x5468])} ${item.weekMinutes} min` : '',
      item.weakCount ? `${zh([0x8584, 0x5f31])} ${item.weakCount} ${zh([0x9879])}` : ''
    ].filter(Boolean).join(' · ')
  }
}

const weakPoints = ref([])
const suggestions = ref([])
const resourceFeedback = ref([])
const resourceFeedbackText = ref(zh([0x6682, 0x65e0, 0x8d44, 0x6e90, 0x4f7f, 0x7528, 0x8bb0, 0x5f55]))

// ---- chart data (for SimpleChart components) ----
const CHART_COLORS = [
  '#2563eb', '#0891b2', '#16a34a', '#7c3aed',
  '#e11d48', '#ea580c', '#eab308', '#6366f1',
  '#14b8a6', '#dc2626', '#a855f7', '#0ea5e9'
]

const knowledgeDistribution = computed(() => {
  const points = weakPoints.value
  if (!points.length) return []
  return points.slice(0, 6).map((point, i) => ({
    label: point.name.length > 6 ? point.name.slice(0, 6) + '…' : point.name,
    value: point.value,
    color: CHART_COLORS[i % CHART_COLORS.length]
  }))
})

const resourceChartData = computed(() => {
  const feedback = resourceFeedback.value
  if (!feedback.length) return []
  return feedback.slice(0, 5).map((item, i) => ({
    label: item.label,
    value: parseFloat(item.value) || 0,
    color: CHART_COLORS[i % CHART_COLORS.length]
  }))
})

// ---- color helpers for progress bars ----
const progressBarColors = ['#2563eb', '#16a34a', '#ea580c', '#7c3aed', '#e11d48', '#0891b2', '#eab308', '#6366f1']

const toPercent = value => `${Math.round(Math.max(0, Math.min(1, Number(value || 0))) * 100)}%`
const formatSecondsToMinutes = seconds => Math.round(Number(seconds || 0) / 60)

const normalizeWeakPoints = raw => {
  const list = Array.isArray(raw) ? raw : []
  return list.map(item => {
    const accuracy = Number(item.accuracy ?? item.correct_rate ?? 0)
    const normalizedAccuracy = accuracy > 1 ? accuracy / 100 : accuracy
    const severity = Math.round((1 - Math.max(0, Math.min(1, normalizedAccuracy))) * 100)
    const attempts = Number(item.total_attempts || 0)
    const levelMap = {
      beginner: zh([0x521d, 0x5b66]),
      learning: zh([0x5b66, 0x4e60, 0x4e2d])
    }

    return {
      name: String(item.tag || item.name || item.knowledge_tag || zh([0x672a, 0x547d, 0x540d, 0x77e5, 0x8bc6, 0x70b9])),
      tip: attempts
        ? `${levelMap[item.level] || item.level || zh([0x9700, 0x5de9, 0x56fa])} - ${zh([0x6b63, 0x786e, 0x7387])} ${toPercent(normalizedAccuracy)} - ${attempts} ${zh([0x6b21, 0x7ec3, 0x4e60])}`
        : `${levelMap[item.level] || item.level || zh([0x9700, 0x5de9, 0x56fa])} - ${zh([0x638c, 0x63e1, 0x5ea6])} ${toPercent(normalizedAccuracy)}`,
      value: severity
    }
  }).filter(item => item.name).slice(0, 4)
}

const normalizeGuidance = raw => {
  const text = String(raw || '').trim()
  if (!text) return []

  return text
    .split(/\r?\n|[.;]/)
    .map(line => line.replace(/^[-*#\d.\s]+/, '').trim())
    .filter(Boolean)
    .slice(0, 4)
}

const applyStudyStats = (stats, collections = [], pathStats = null) => {
  const studyTime = stats.study_time || stats.studyTime || {}
  const resources = stats.resources || {}
  const exam = stats.exam_summary || stats.examSummary || {}
  const dedicatedPaths = normalizeLearningPaths(pathStats)
  const paths = dedicatedPaths.length ? dedicatedPaths : normalizeLearningPaths(stats)
  const finished = paths.filter(item => item.totalNodes > 0 && item.completedNodes >= item.totalNodes)
  const inProgress = paths.filter(item => item.totalNodes > 0 && item.completedNodes < item.totalNodes)
  const weekMinutes = formatSecondsToMinutes(studyTime.week_seconds ?? studyTime.weekSeconds)
  const totalMinutes = formatSecondsToMinutes(studyTime.total_seconds ?? studyTime.totalSeconds)
  const activeDays = Number(studyTime.active_days ?? studyTime.activeDays ?? 0)
  const correctRate = Number(exam.correct_rate ?? exam.correctRate ?? 0)
  const completionRate = Number(exam.completion_rate ?? exam.completionRate ?? 0)
  const collectedCount = Array.isArray(collections) ? collections.length : Number(resources.collected_count || 0)

  studyMinutes.value = weekMinutes
  studyTimeNote.value = `${zh([0x672c, 0x5468, 0x7d2f, 0x8ba1])} ${weekMinutes} min - ${zh([0x7d2f, 0x8ba1])} ${totalMinutes} min - ${zh([0x6d3b, 0x8dc3])} ${activeDays} ${zh([0x5929])}`
  completedPaths.value = finished.reverse().map((item, index) => formatPathCard(item, index, true))
  currentPaths.value = inProgress.reverse().map((item, index) => formatPathCard(item, index)).slice(0, 2)
  weakPoints.value = normalizeWeakPoints(stats.weak_points || stats.weakPoints)
  if (!accuracyData.value.length) {
    accuracyData.value = buildRecentDateLabels()
    accuracySummary.value = `${zh([0x6700, 0x8fd1, 0x37, 0x5929, 0x6682, 0x65e0, 0x505a, 0x9898, 0x6570, 0x636e])} - ${zh([0x603b, 0x6b63, 0x786e, 0x7387])} ${toPercent(correctRate)}`
  }
  resourceFeedback.value = [
    { label: zh([0x8d44, 0x6e90, 0x6253, 0x5f00, 0x7387]), value: toPercent(resources.open_rate ?? resources.openRate) },
    { label: zh([0x7ec3, 0x4e60, 0x5b8c, 0x6210, 0x7387]), value: toPercent(completionRate) },
    { label: zh([0x67e5, 0x770b, 0x6b21, 0x6570]), value: String(resources.total_views ?? resources.totalViews ?? 0) },
    { label: zh([0x4e0b, 0x8f7d, 0x6b21, 0x6570]), value: String(resources.total_downloads ?? resources.totalDownloads ?? 0) },
    { label: zh([0x6536, 0x85cf, 0x8d44, 0x6599]), value: String(collectedCount) }
  ]
  resourceFeedbackText.value = `${zh([0x5171, 0x6709, 0x8d44, 0x6e90])} ${resources.total || 0} ${zh([0x4efd])} - ${zh([0x5df2, 0x9605, 0x8bfb])} ${resources.read_count ?? resources.readCount ?? 0} ${zh([0x4efd])} - ${zh([0x5f85, 0x9605, 0x8bfb])} ${resources.unread_count ?? resources.unreadCount ?? 0} ${zh([0x4efd])}`
  suggestions.value = normalizeGuidance(stats.learning_guidance || stats.learningGuidance)
}

const loadStudyDashboard = async () => {
  try {
    const statsResult = await getStudyStats()
    const stats = unwrapApiData(statsResult) || {}
    const [guidanceResult, collectionsResult, weeklyAccuracyResult, pathStatsResult] = await Promise.allSettled([
      getLearningGuidance(),
      getStudyCollections(),
      getStudyExamWeekly(),
      getStudyPathStats()
    ])
    const guidanceData = guidanceResult.status === 'fulfilled' ? unwrapApiData(guidanceResult.value) : {}
    const collectionsData = collectionsResult.status === 'fulfilled' ? unwrapApiData(collectionsResult.value) : []
    const weeklyAccuracy = weeklyAccuracyResult.status === 'fulfilled' ? normalizeWeeklyAccuracy(weeklyAccuracyResult.value) : { points: [] }
    const guidance = guidanceData?.guidance || stats.learning_guidance || stats.learningGuidance || ''
    const collections = Array.isArray(collectionsData) ? collectionsData : []

    if (weeklyAccuracyResult.status === 'rejected') {
      console.warn('[StudySituation] load weekly accuracy failed:', weeklyAccuracyResult.reason)
    }

    if (pathStatsResult.status === 'rejected') {
      console.warn('[StudySituation] load path stats failed:', pathStatsResult.reason)
    }

    if (weeklyAccuracy.points?.length) {
      accuracyData.value = weeklyAccuracy.points
      accuracySummary.value = `${zh([0x6700, 0x8fd1, 0x37, 0x5929])} ${weeklyAccuracy.total || 0} ${zh([0x9898])} - ${zh([0x6b63, 0x786e])} ${weeklyAccuracy.correct || 0} ${zh([0x9898])} - ${zh([0x6b63, 0x786e, 0x7387])} ${toPercent(weeklyAccuracy.accuracy)}`
    } else {
      accuracyData.value = buildRecentDateLabels()
    }
    const pathStats = pathStatsResult.status === 'fulfilled' ? unwrapApiData(pathStatsResult.value) : null
    applyStudyStats({ ...stats, learning_guidance: guidance }, collections, pathStats)
  } catch (error) {
    console.warn('[StudySituation] load dashboard failed:', error)
  }
}

const loadPortraitTags = async () => {
  try {
    const result = await getPortrait()
    const portrait = result?.data || result || {}
    let raw = portrait.personality_tags
    if (typeof raw === 'string') {
      try { raw = JSON.parse(raw) } catch { raw = [] }
    }
    learnerTags.value = Array.isArray(raw) ? raw : []
  } catch {
    learnerTags.value = []
  }
}

onMounted(() => {
  window.addEventListener('zhiban:user-avatar-updated', handleAvatarUpdated)
  loadUserAvatar()
  loadRadarData()
  loadPortraitTags()
  loadStudyDashboard()
})

onBeforeUnmount(() => {
  window.removeEventListener('zhiban:user-avatar-updated', handleAvatarUpdated)
})
</script>

<style scoped>
.study-panel {
  position: relative;
  isolation: isolate;
  width: 100%;
  height: 100vh;
  min-height: 0;
  padding: 26px 34px 30px;
  background: var(--color-bg, #f1f7fb);
  color: var(--color-text-heading, #163f8f);
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: hidden;
}

.page-bg-deco {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: var(--color-bg, #f1f7fb);
  overflow: hidden;
  pointer-events: none;
}

.page-bg-deco::before,
.page-bg-deco::after,
.sweep {
  position: absolute;
  display: block;
  border-radius: 50%;
  background: var(--color-bg-alt, #e9eff3);
}

.page-bg-deco::before,
.page-bg-deco::after {
  content: "";
}

.page-bg-deco::before {
  width: clamp(540px, 62vw, 760px);
  height: clamp(540px, 62vw, 760px);
  left: 50%;
  top: -96px;
  transform: translateX(-50%);
}

.page-bg-deco::after {
  width: clamp(420px, 48vw, 620px);
  height: clamp(420px, 48vw, 620px);
  right: clamp(-280px, -18vw, -170px);
  bottom: clamp(-310px, -24vw, -210px);
}

.sweep-one {
  width: clamp(320px, 34vw, 520px);
  height: clamp(320px, 34vw, 520px);
  left: clamp(-250px, -14vw, -140px);
  top: 118px;
}

.sweep-two {
  width: clamp(320px, 34vw, 520px);
  height: clamp(320px, 34vw, 520px);
  right: clamp(-220px, -12vw, -130px);
  top: -92px;
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
    "profile profile duration"
    "current accuracy tags";
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
  display: contents;
}

.panel-card {
  border: 1px solid var(--color-border, rgba(22, 63, 143, 0.14));
  border-radius: 8px;
  background:
    linear-gradient(135deg, var(--color-card, rgba(250, 250, 250, 0.94)), var(--color-card-hover, rgba(237, 249, 252, 0.84))),
    var(--color-card, #fafafa);
  box-shadow:
    0 14px 34px var(--color-shadow, rgba(22, 63, 143, 0.08)),
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
  grid-area: duration;
  min-height: 0;
  padding: 20px;
}

.tag-panel {
  grid-area: tags;
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
  width: 100%;
  height: 100%;
  object-fit: cover;
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
  margin-top: 8px;
}

.accuracy-summary {
  margin: 10px 0 0;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.line-chart line {
  stroke: rgba(95, 143, 195, 0.32);
  stroke-width: 1;
}

.line-chart .chart-tick line {
  stroke: rgba(95, 143, 195, 0.18);
}

.line-chart .chart-axis {
  stroke: rgba(95, 143, 195, 0.4);
}

.line-chart polyline {
  fill: none;
  stroke: #163f8f;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.line-chart .chart-point-dot {
  fill: #163f8f;
  stroke: none;
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

.path-list .path-meta {
  color: rgba(22, 63, 143, 0.6);
  font-weight: 700;
  line-height: 1.45;
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
  padding: 0;
  list-style: none;
  color: #163f8f;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.8;
}

.suggestion-panel li {
  display: flex;
  align-items: flex-start;
  gap: 9px;
}

.suggestion-panel li::before {
  content: "";
  width: 7px;
  height: 7px;
  margin-top: 8px;
  border-radius: 50%;
  background: #163f8f;
  flex-shrink: 0;
}

.suggestion-panel li + li {
  margin-top: 8px;
}

.feedback-summary {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.feedback-chart-row {
  margin-top: 14px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 14px;
  align-items: start;
}

.feedback-bar {
  min-width: 200px;
  padding: 10px 8px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.7);
}

.mini-donut {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(201, 220, 233, 0.62);
}

.feedback-chart-row .feedback-summary {
  margin-top: 0;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.feedback-summary div {
  min-height: 74px;
  padding: 12px 8px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-top: 3px solid transparent;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.7);
  display: grid;
  place-items: center;
  text-align: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.feedback-summary div:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(22, 63, 143, 0.1);
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
