<template>
  <main class="classroom-page">
    <header class="classroom-header">
      <button class="soft-btn" type="button" @click="backToPath">
        <ArrowLeft :size="18" />
        返回路径
      </button>
      <div>
        <p>Interactive Classroom</p>
        <h1>{{ node.title || '互动课堂' }}</h1>
      </div>
      <span class="lesson-clock">{{ estimatedMinutes }} min</span>
    </header>

    <section class="classroom-shell">
      <aside class="lesson-rail">
        <div
          v-for="(segment, index) in lessonSegments"
          :key="segment.id"
          class="lesson-step"
          :class="{ active: index === activeSegmentIndex, done: index < activeSegmentIndex }"
          @click="activeSegmentIndex = index"
        >
          <span>{{ index + 1 }}</span>
          <div>
            <strong>{{ segment.title }}</strong>
            <small>{{ segment.intent }}</small>
          </div>
        </div>
      </aside>

      <section class="teaching-stage">
        <div class="lecture-player classroom-player" :class="[{ speaking: isSpeaking }, `scene-${activeSegment.type}`]">
          <div class="player-meta">
            <span>小知讲堂</span>
            <strong>{{ activeSegmentIndex + 1 }} / {{ lessonSegments.length }}</strong>
            <em>{{ activeStageLabel }}</em>
            <small>{{ classroomTimelineLabel }}</small>
            <button class="voice-btn" type="button" :disabled="audioLoading" @click="toggleLectureAudio">
              <Pause v-if="isSpeaking" :size="18" />
              <Play v-else :size="18" />
              {{ audioLoading ? '生成声音中...' : isSpeaking ? '暂停讲解' : '播放讲解' }}
            </button>
          </div>

          <section class="classroom-screen">
            <div class="screen-backdrop" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div class="cinema-scene">
              <article class="lesson-canvas">
                <div class="scene-copy">
                  <span class="segment-kicker">{{ activeSegmentKicker }}</span>
                  <h2>{{ activeScreenTitle }}</h2>
                  <p class="scene-lead">{{ activeTeachingLead }}</p>
                  <ul class="scene-lines">
                    <li v-for="line in activeTeachingLines" :key="line">{{ line }}</li>
                  </ul>
                </div>

                <div class="concept-lane">
                  <span
                    v-for="(point, index) in visibleBoardItems"
                    :key="`${point}-${index}`"
                    class="concept-pill"
                  >
                    <small>{{ String(index + 1).padStart(2, '0') }}</small>
                    {{ point }}
                  </span>
                </div>

                <div class="scene-example">
                  <span>{{ activeSegment.type === 'resource' ? '资料证据' : '课堂例子' }}</span>
                  <strong>{{ activeSceneExample }}</strong>
                </div>
              </article>

              <aside class="teacher-layer">
                <span class="lecture-label">
                  <Volume2 :size="16" />
                  {{ audioLoading ? '生成声音中' : isSpeaking ? '正在讲解' : '等待播放' }}
                </span>
                <img :src="petImage" alt="小知" />
                <div class="voice-bars" aria-hidden="true">
                  <i v-for="bar in 5" :key="bar"></i>
                </div>
                <p>{{ activeTakeaway }}</p>
              </aside>
            </div>
          </section>

          <div class="caption-bar">
            <strong>小知</strong>
            <span>{{ activeSegment.script }}</span>
          </div>

          <VideoGlowProgress
            class="classroom-progress"
            :current-time="classroomCurrentTime"
            :duration="classroomDuration"
            :is-playing="isSpeaking"
            :segments="classroomProgressSegments"
            :markers="classroomProgressMarkers"
            :can-play="Boolean(activeSegment?.script) && !audioLoading"
            @toggle-play="toggleLectureAudio"
            @seek="seekClassroom"
          />
        </div>

        <section class="dialog-panel classroom-dialog-panel">
          <div class="section-head">
            <span>课堂对话</span>
            <small>{{ messages.length }} 条</small>
          </div>
          <div class="dialog-messages">
            <article v-for="message in messages" :key="message.id" :class="message.role">
              <strong>{{ message.role === 'teacher' ? '小知' : '我' }}</strong>
              <p>{{ message.content }}</p>
            </article>
          </div>
          <form class="dialog-input" @submit.prevent="sendLearnerMessage">
            <input v-model.trim="learnerInput" placeholder="提问，或用自己的话讲一遍..." />
            <button type="submit" :disabled="!learnerInput">发送</button>
          </form>
        </section>

        <div v-if="showCheckpoint" class="checkpoint-card">
          <span><MessageCircle :size="16" /> 课堂追问</span>
          <h3>{{ activeQuestion.prompt }}</h3>
          <div class="checkpoint-options">
            <button
              v-for="option in activeQuestion.options"
              :key="option"
              type="button"
              :class="{ selected: selectedAnswer === option }"
              @click="selectedAnswer = option"
            >
              {{ option }}
            </button>
          </div>
          <p v-if="selectedAnswer" class="checkpoint-feedback">
            {{ checkpointFeedback }}
          </p>
        </div>

        <div class="stage-actions">
          <button class="soft-btn" type="button" :disabled="activeSegmentIndex === 0" @click="prevSegment">
            上一步
          </button>
          <button class="primary-btn" type="button" @click="nextSegment">
            {{ activeSegmentIndex === lessonSegments.length - 1 ? '完成本节总结' : '我懂了，继续' }}
          </button>
        </div>
      </section>

      <section class="dialog-panel classroom-dialog-panel">
        <div class="section-head">
          <span>课堂对话</span>
          <small>{{ messages.length }} 条</small>
        </div>
        <div class="dialog-messages">
          <article v-for="message in messages" :key="message.id" :class="message.role">
            <strong>{{ message.role === 'teacher' ? '小知' : '我' }}</strong>
            <p>{{ message.content }}</p>
          </article>
        </div>
        <form class="dialog-input" @submit.prevent="sendLearnerMessage">
          <input v-model.trim="learnerInput" placeholder="提问，或用自己的话讲一遍..." />
          <button type="submit" :disabled="!learnerInput">发送</button>
        </form>
      </section>

      <aside class="resource-shelf">
        <section class="personal-panel">
          <div class="section-head">
            <span>本节策略</span>
            <small>{{ classroomSourceLabel }}</small>
          </div>
          <p>{{ personalCue.detail }}</p>
          <div class="strategy-tags">
            <span v-for="tag in personalCue.tags" :key="tag">{{ tag }}</span>
          </div>
        </section>

        <section>
          <div class="section-head">
            <span>当前素材</span>
            <small>{{ activeResourceCards.length }} 份</small>
          </div>
          <div v-if="activeResourceCards.length" class="resource-list">
            <article v-for="resource in activeResourceCards" :key="resource.id || resource.title" class="resource-card">
              <div class="resource-card__top">
                <span>{{ resource.typeLabel || resource.fileType || '资料' }}</span>
                <div class="resource-card__actions">
                  <button
                    type="button"
                    title="预览"
                    :disabled="!canPreviewClassroomResource(resource)"
                    @click="previewClassroomResource(resource)"
                  >
                    <Eye :size="13" />
                    <span>预览</span>
                  </button>
                  <button
                    type="button"
                    :title="isClassroomResourceSaved(resource) ? '已保存' : '保存'"
                    @click="saveClassroomResource(resource)"
                  >
                    <Save :size="13" />
                    <span>{{ isClassroomResourceSaved(resource) ? '已存' : '保存' }}</span>
                  </button>
                  <button
                    type="button"
                    title="下载"
                    :disabled="!canDownloadClassroomResource(resource)"
                    @click="downloadClassroomResource(resource)"
                  >
                    <Download :size="13" />
                    <span>下载</span>
                  </button>
                </div>
              </div>
              <strong>{{ resource.title }}</strong>
              <p>{{ resourceBrief(resource) }}</p>
            </article>
          </div>
          <p v-else class="empty-copy">当前节点还没有生成资料，课堂会先按路径节点讲解。</p>
        </section>

        <section class="feynman-panel" :class="{ unlocked: feynmanUnlocked }">
          <div class="section-head">
            <span>费曼讲述</span>
            <small>{{ feynmanUnlocked ? '已开启' : '稍后开启' }}</small>
          </div>
          <p>
            {{ feynmanUnlocked
              ? '用自己的话讲一遍当前知识点，小知会根据你的表达找薄弱点。'
              : '先完成前面的概念铺垫，再让你反过来讲给小知听。' }}
          </p>
          <textarea
            v-model.trim="feynmanAnswer"
            :disabled="!feynmanUnlocked"
            placeholder="比如：我认为补码的作用是..."
          ></textarea>
          <button type="button" :disabled="!feynmanUnlocked || !feynmanAnswer" @click="reviewFeynmanAnswer">
            让小知追问
          </button>
          <p v-if="feynmanFeedback" class="feynman-feedback">{{ feynmanFeedback }}</p>
        </section>

        <section class="dialog-panel">
          <div class="section-head">
            <span>课堂对话</span>
            <small>{{ messages.length }} 条</small>
          </div>
          <div class="dialog-messages">
            <article v-for="message in messages" :key="message.id" :class="message.role">
              <strong>{{ message.role === 'teacher' ? '小知' : '我' }}</strong>
              <p>{{ message.content }}</p>
            </article>
          </div>
          <form class="dialog-input" @submit.prevent="sendLearnerMessage">
            <input v-model.trim="learnerInput" placeholder="提问，或用自己的话讲一遍..." />
            <button type="submit" :disabled="!learnerInput">发送</button>
          </form>
        </section>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Download, Eye, MessageCircle, Pause, Play, Save, Volume2 } from 'lucide-vue-next'
import { generateNodeClassroom, narrateClassroomText } from '../api/learningPath'
import { downloadWithToken, resolveApiUrl } from '../api/config'
import VideoGlowProgress from '../components/ppt_video/video/VideoGlowProgress.vue'
import petImage from '../assets/pic/study-pet-reference-cutout.png'
import { saveGeneratedResourceRef } from '../utils/savedResources'

const CLASSROOM_LAUNCH_KEY = 'zhiban_classroom_launch'
const PATH_CACHE_KEY = 'zhiban_path_state'

const route = useRoute()
const router = useRouter()

const launchPayload = ref(null)
const classroomLesson = ref(null)
const classroomResources = ref([])
const classroomLoading = ref(false)
const classroomError = ref('')
const profileSnapshot = ref({})
const activeSegmentIndex = ref(0)
const selectedAnswer = ref('')
const learnerInput = ref('')
const feynmanAnswer = ref('')
const feynmanFeedback = ref('')
const messages = ref([])
const isSpeaking = ref(false)
const speechProgress = ref(0)
const audioLoading = ref(false)
const audioError = ref('')
const audioUrls = ref({})
const audioDurations = ref({})
const savedClassroomResourceIds = ref(new Set())
let lectureAudio = null

const readJson = (storage, key) => {
  try {
    if (!storage) return null
    const raw = storage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const readStoredProfileSnapshot = () => {
  const keys = [
    'user',
    'userInfo',
    'zhiban_user',
    'zhiban_user_profile',
    'zhiban_portrait',
    'zhiban_learning_profile',
    'portrait',
    'user_portrait'
  ]
  const merged = {}
  for (const key of keys) {
    const value = readJson(localStorage, key)
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(merged, value.data && typeof value.data === 'object' ? value.data : value)
    }
  }
  for (const key of ['major', 'grade', 'username']) {
    const value = localStorage.getItem(key)
    if (value && !merged[key]) merged[key] = value
  }
  return merged
}

const flattenText = value => {
  if (!value) return ''
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (Array.isArray(value)) return value.map(flattenText).join(' ')
  if (typeof value === 'object') return Object.values(value).map(flattenText).join(' ')
  return ''
}

const normalizeNodeFromCache = () => {
  const cached = readJson(localStorage, PATH_CACHE_KEY)
  const nodeId = String(route.params.nodeId || route.query.nodeId || '')
  const node = (cached?.nodes || []).find(item => String(item.id || item.node_id || item.nodeId) === nodeId)
  if (!node) return null
  return {
    pathId: cached.pathId || cached.path_id || route.params.pathId || '',
    pathTitle: cached.goal || cached.title || '学习路径',
    node,
    resources: node._resources || node.resources || [],
    quiz: node._quiz || node.quiz || null,
    sessionId: node.sessionId || node.session_id || ''
  }
}

const normalizeNodeFromRoute = () => ({
  pathId: route.params.pathId || '',
  pathTitle: '学习路径',
  node: {
    id: route.params.nodeId || '',
    title: route.query.title || '互动课堂',
    summary: route.query.summary || '从学习路径进入课堂，围绕当前节点完成讲解、追问和总结。'
  },
  resources: []
})

const node = computed(() => launchPayload.value?.node || {})
const resourceList = computed(() => {
  const localResources = Array.isArray(launchPayload.value?.resources) ? launchPayload.value.resources : []
  const merged = []
  const seen = new Set()
  for (const item of [...localResources, ...classroomResources.value]) {
    if (!item || typeof item !== 'object') continue
    const key = String(item.id || item.resourceId || item.title || '').trim()
    if (key && seen.has(key)) continue
    if (key) seen.add(key)
    merged.push(item)
  }
  return merged
})
const quiz = computed(() => launchPayload.value?.quiz || null)
const estimatedMinutes = computed(() => Number(node.value.estimatedMinutes || node.value.estimated_minutes || 15))
const profileText = computed(() => [
  flattenText(profileSnapshot.value),
  flattenText(launchPayload.value?.diagnosis),
  flattenText(node.value?.weakPoints || node.value?.weak_points),
  flattenText(classroomLesson.value?.personal_summary)
].join(' '))

const personalCue = computed(() => {
  const text = profileText.value
  const tags = []
  let summary = '按当前节点动态讲解'
  let detail = '课堂会根据当前节点、已有资料和测验情况调整讲解顺序，先讲主线，再用问题确认理解。'

  if (/视觉|图像|图表|结构|思维导图|脑图/.test(text)) {
    tags.push('图像化')
    summary = '偏图像化讲解'
    detail = '你更适合先看结构关系，所以课堂会先给出板书主线，再把资料和题目挂到对应概念上。'
  }
  if (/刷题|考试|期末|考研|薄弱|错题|正确率|掌握/.test(text)) {
    tags.push('考点优先')
    summary = tags.length > 1 ? `${summary} · 考点优先` : '考点优先讲解'
    detail = '系统会减少铺垫废话，把容易出题、容易混淆的点提前抛出来，用短问题检查是否真的理解。'
  }
  if (/实操|项目|动手|代码|实验|部署|开发/.test(text)) {
    tags.push('实操迁移')
    summary = tags.length > 1 ? `${summary} · 实操迁移` : '实操迁移讲解'
    detail = '课堂会尽量把抽象概念落到操作、实验或工程类比上，避免只停留在教材定义。'
  }
  if (/内向|紧张|不敢问|慢热|焦虑|压力/.test(text)) {
    tags.push('低压力追问')
    detail = '追问会从小问题开始，不会一上来要求完整表达；讲不清楚的地方会被拆成更小的提示。'
  }
  if (/大一|大二|新手|基础|入门/.test(text)) {
    tags.push('基础补缝')
  }

  if (!tags.length) tags.push('节点驱动', '资料佐证')
  return { summary, detail, tags: tags.slice(0, 4) }
})

const classroomSourceLabel = computed(() => {
  if (classroomLoading.value) return '生成中'
  if (classroomLesson.value?.segments?.length) return '智能体生成'
  if (classroomError.value) return '本地降级'
  return '本地课堂'
})

const splitKeywords = value => String(value || '')
  .split(/[，,、/|；;()\s]+/)
  .map(item => item.trim())
  .filter(Boolean)
  .slice(0, 5)

const normalizeSegment = (segment, index) => {
  const fallbackIds = ['lead-in', 'concept', 'resource-link', 'checkpoint', 'feynman']
  const question = segment?.question && typeof segment.question === 'object' ? segment.question : null
  const script = String(segment?.teacher_speech || segment?.script || '')
  const points = Array.isArray(segment?.points) ? segment.points.map(item => String(item || '').trim()).filter(Boolean) : []
  const boardItems = Array.isArray(segment?.board_items)
    ? segment.board_items.map(item => String(item || '').trim()).filter(Boolean)
    : points
  const resourceRefs = Array.isArray(segment?.resource_refs)
    ? segment.resource_refs
        .filter(item => item && typeof item === 'object')
        .map(item => ({
          title: String(item.title || '').trim(),
          type: String(item.type || '资料').trim(),
          how_to_use: String(item.how_to_use || '支撑本幕讲解').trim()
        }))
        .filter(item => item.title)
    : []
  const id = String(segment?.id || fallbackIds[index] || `segment-${index + 1}`)
  const type = String(segment?.type || segment?.id || fallbackIds[index] || 'scene')
  const normalizedQuestion = question
    ? {
        prompt: String(question.prompt || ''),
        options: Array.isArray(question.options) ? question.options.map(item => String(item || '').trim()).filter(Boolean) : [],
        answer: String(question.answer || ''),
        feedback: String(question.feedback || '')
      }
    : null

  if (id === 'resource-link' || type === 'resource') {
    const title = node.value.title || '当前知识点'
    return {
      id,
      type: 'resource',
      title: '证据查找',
      subtitle: '用资料查证刚才的概念',
      intent: '用资料核对',
      script: `现在暂停推进新知识，只做一次查证：请在右侧资料中找到能解释「${title}」的定义、步骤或例题，再回头判断刚才的板书是否站得住。`,
      boardTitle: '查证路径',
      boardItems: ['找定义', '找步骤', '找例题', '回看结构'],
      points: [
        `在资料中定位「${title}」的定义`,
        '找一段可复现的步骤或公式',
        '用例题检查板书是否能解释'
      ],
      visualHint: '资料是证据来源，主画面只保留查证任务。',
      example: `例如先找资料中能解释「${title}」定义或步骤的一段，再对照板书复述。`,
      resourceRefs,
      durationSeconds: Number(segment?.duration_seconds || 22),
      question: normalizedQuestion || {
        prompt: '看资料时最应该先验证什么？',
        options: ['定义和步骤', '文件有多长', '只看封面'],
        answer: '定义和步骤',
        feedback: '对，资料要回到本节概念和步骤。'
      }
    }
  }

  return {
    id,
    type,
    title: String(segment?.title || `课堂环节 ${index + 1}`),
    subtitle: String(segment?.subtitle || ''),
    intent: String(segment?.intent || '继续学习'),
    script,
    boardTitle: String(segment?.board_title || '课堂板书'),
    boardItems,
    points,
    visualHint: String(segment?.visual_hint || ''),
    example: String(segment?.example || ''),
    resourceRefs,
    durationSeconds: Number(segment?.duration_seconds || 0),
    question: normalizedQuestion
  }
}

const remoteSegments = computed(() => {
  const segments = classroomLesson.value?.segments
  if (!Array.isArray(segments) || segments.length < 3) return []
  return segments.map(normalizeSegment).filter(item => item.script && item.points.length)
})

const buildLessonSegments = () => {
  const title = node.value.title || '当前节点'
  const summary = node.value.summary || node.value.description || `理解 ${title} 的核心概念和典型应用。`
  const keywords = splitKeywords(summary)
  const points = keywords.length ? keywords : [title, '关键概念', '典型应用']
  const hasQuiz = !!quiz.value
  const hasResources = resourceList.value.length > 0
  const cue = personalCue.value
  const cueText = cue.tags.length ? `这节课会按「${cue.tags.join('、')}」的方式推进。` : ''

  return [
    {
      id: 'lead-in',
      type: 'hook',
      title: '情境导入',
      subtitle: '先把知识点放进真实学习任务',
      intent: '先知道为什么学',
      script: `我们先把「${title}」放进真实学习任务里看：它不是孤立概念，而是后面做题、看资料和解释原理的入口。${cueText}先问清它解决什么问题，再进入细节。`,
      boardTitle: '问题入口',
      boardItems: [summary, cue.summary, '先建立问题意识'],
      points: [summary, cue.summary, '先建立问题意识'],
      visualHint: '从问题出发，比直接背定义更稳。',
      example: `遇到「${title}」相关题，先判断它想考什么。`,
      resourceRefs: [],
      durationSeconds: 18
    },
    {
      id: 'concept',
      type: 'concept',
      title: '核心概念',
      subtitle: '拆开主干关系',
      intent: '拆开关键点',
      script: `这一段先抓主干：${points.slice(0, 3).join('、')}。你不用先背定义，先理解它们之间的关系。遇到教材里看起来很散的句子，就把它们压回“是什么、为什么、怎么用”三件事。`,
      boardTitle: '概念主线',
      boardItems: points,
      points,
      visualHint: '把散句压回“是什么、为什么、怎么用”。',
      example: `用一句话解释「${title}」和前后知识的关系。`,
      resourceRefs: [],
      durationSeconds: 24
    },
    {
      id: 'resource-link',
      type: 'resource',
      title: '证据查找',
      subtitle: hasResources ? '用资料查证刚才的概念' : '先按节点推进',
      intent: hasResources ? '用资料核对' : '按节点继续讲',
      script: hasResources
        ? `现在暂停推进新知识，只做一次查证：从右侧素材里挑一份最能解释「${title}」的资料，找定义、步骤或例题，再回头核对板书。`
        : `当前节点还没有资料，先用路径节点信息讲清「${title}」的主线，后续资料生成后再用来查证定义、步骤和例题。`,
      boardTitle: '查证路径',
      boardItems: hasResources
        ? ['找定义', '找步骤', '找例题', '回看结构']
        : ['抓主线', '补资料', '再验证'],
      points: hasResources
        ? [`在资料中定位「${title}」的定义`, '找一段可复现的步骤或公式', '用例题检查板书是否能解释']
        : [`先用节点描述建立「${title}」的主线`, '资料生成后再查证细节'],
      visualHint: '资料是证据来源，主画面只保留查证任务。',
      example: `例如先找资料中能解释「${title}」定义或步骤的一段，再对照板书复述。`,
      resourceRefs: resourceList.value.slice(0, 3).map(item => ({
        title: item.title,
        type: item.typeLabel || item.fileType || '资料',
        how_to_use: '验证当前板书'
      })),
      durationSeconds: 22
    },
    {
      id: 'checkpoint',
      type: 'quiz',
      title: '课堂追问',
      subtitle: '先用短问确认理解',
      intent: hasQuiz ? '用题目校验理解' : '用短问校验理解',
      script: hasQuiz
        ? `这里不直接把整套题甩给你，而是先抛一个小问题确认方向。正式检测仍保留在学习路径里，课堂只负责提前暴露「${title}」的薄弱点。`
        : `没有题库时，课堂会先用概念追问判断你是否真的理解「${title}」。`,
      boardTitle: '即时检查',
      boardItems: ['先小问，再练习', '错了不惩罚', '只定位薄弱点'],
      points: ['先小问，再练习', '错了不惩罚，只定位薄弱点'],
      visualHint: '问题在课堂中间自然弹出，不打断主线。',
      example: `如果你说不清「${title}」的用途，就回到第一条板书。`,
      resourceRefs: [],
      durationSeconds: 18
    },
    {
      id: 'feynman',
      type: 'feynman',
      title: '反向讲解',
      subtitle: '换你当老师',
      intent: '费曼学习法',
      script: `最后换你当老师：用自己的话把「${title}」讲给小知听。你可以只讲三句话：它是什么，它为什么重要，它在题目或场景里怎么用。讲不清楚的地方，就是下一轮学习要补的地方。`,
      boardTitle: '三句话反讲',
      boardItems: ['它是什么', '为什么重要', '怎么用'],
      points: ['你讲一遍', '小知追问', '沉淀薄弱点'],
      visualHint: '讲不清楚不是失败，是系统找到下一步补强点。',
      example: `你可以这样开头：${title} 主要解决……`,
      resourceRefs: [],
      durationSeconds: 20
    }
  ]
}

const lessonSegments = computed(() => remoteSegments.value.length ? remoteSegments.value : buildLessonSegments())
const activeSegment = computed(() => lessonSegments.value[activeSegmentIndex.value] || lessonSegments.value[0])
const splitTeachingLines = value => String(value || '')
  .replace(/\s+/g, ' ')
  .split(/[。！？!?；;]+|\.\s+/)
  .map(item => item.replace(/^[，,。；;\s]+|[，,。；;\s]+$/g, '').trim())
  .filter(item => item.length >= 8)

const activeConceptItems = computed(() => {
  const concept = lessonSegments.value.find(item => item.id === 'concept' || item.type === 'concept')
  const items = concept?.boardItems?.length ? concept.boardItems : concept?.points || []
  return items.map(item => String(item || '').trim()).filter(Boolean).slice(0, 5)
})

const activeTeachingLines = computed(() => {
  const segment = activeSegment.value || {}
  if (segment.type === 'resource' || segment.id === 'resource-link') {
    return [
      '从右侧素材里找一条定义、步骤或公式。',
      '把这条证据对回刚才的板书，再尝试自己复述。'
    ]
  }
  const fromPoints = (segment.points?.length ? segment.points : segment.boardItems || [])
    .map(item => String(item || '').trim())
    .filter(item => item.length >= 4)
  if (fromPoints.length >= 2) return fromPoints.slice(0, 3)
  const fromVisual = splitTeachingLines(segment.visualHint)
  if (fromVisual.length) return fromVisual.slice(0, 2)
  return splitTeachingLines(segment.script).slice(0, 2)
})

const activeStageLabel = computed(() => {
  const segment = activeSegment.value || {}
  if (segment.type === 'resource' || segment.id === 'resource-link') return '资料查证'
  if (/quiz|checkpoint/.test(segment.type || segment.id || '')) return '课堂追问'
  if (/feynman/.test(segment.type || segment.id || '')) return '费曼回讲'
  return segment.intent || segment.title || '课堂讲解'
})

const activeSegmentKicker = computed(() => {
  const segment = activeSegment.value || {}
  if (segment.type === 'resource' || segment.id === 'resource-link') return '资料证据'
  if (/quiz|checkpoint/.test(segment.type || segment.id || '')) return '即时检查'
  if (/feynman/.test(segment.type || segment.id || '')) return '换你当老师'
  return segment.boardTitle || '课堂板书'
})

const activeScreenTitle = computed(() => {
  const segment = activeSegment.value || {}
  if (segment.type === 'resource' || segment.id === 'resource-link') return '验证当前板书'
  if (/quiz|checkpoint/.test(segment.type || segment.id || '')) return '用问题校准理解'
  if (/feynman/.test(segment.type || segment.id || '')) return '三句话讲给小知'
  return segment.title || activeStageLabel.value
})

const activeTeachingLead = computed(() => {
  const segment = activeSegment.value || {}
  if (segment.type === 'resource' || segment.id === 'resource-link') {
    return '这一幕只做一件事：用资料证明刚才讲过的关键点。'
  }
  return segment.subtitle
    || activeTeachingLines.value[0]
    || segment.visualHint
    || '跟着这一幕先抓主线，再进入细节。'
})

const activeTakeaway = computed(() => {
  const segment = activeSegment.value || {}
  if (segment.type === 'resource' || segment.id === 'resource-link') {
    return '看资料不是堆文件，是找证据。'
  }
  const candidates = [
    segment.visualHint,
    segment.question?.prompt,
    segment.points?.[0],
    segment.boardItems?.[0]
  ]
  return candidates.map(item => String(item || '').trim()).find(Boolean) || '把散句压回“是什么、为什么、怎么用”。'
})
const activeSceneExample = computed(() => {
  if (activeSegment.value?.type === 'resource' || activeSegment.value?.id === 'resource-link') {
    const title = node.value.title || activeSegment.value?.title || '当前知识点'
    return `在右侧素材中找一句能解释「${title}」的内容，再用自己的话讲出来。`
  }
  if (activeSegment.value?.resourceRefs?.length) {
    const ref = activeSegment.value.resourceRefs[0]
    return `${ref.title}：${ref.how_to_use || '用来验证本幕讲解'}`
  }
  return activeSegment.value?.example || activeSegment.value?.question?.prompt || '先用一个例子确认自己是否真正理解。'
})
const segmentAudioKey = (segment = activeSegment.value, index = activeSegmentIndex.value) =>
  `${route.params.pathId || launchPayload.value?.pathId || 'path'}:${route.params.nodeId || node.value.id || 'node'}:${index}:${segment?.id || 'segment'}`
const currentAudioKey = computed(() => segmentAudioKey(activeSegment.value, activeSegmentIndex.value))
const visibleBoardItems = computed(() => {
  if (activeSegment.value?.type === 'resource' || activeSegment.value?.id === 'resource-link') {
    return ['定位证据', '对照板书', '补齐步骤', '找反例', '复述结论']
  }
  const items = activeSegment.value?.boardItems?.length ? activeSegment.value.boardItems : activeSegment.value?.points || []
  return items.slice(0, 5)
})
const feynmanUnlocked = computed(() => activeSegmentIndex.value >= lessonSegments.value.length - 1)

const estimateSegmentSeconds = segment => {
  if (Number(segment?.durationSeconds) > 0) return Number(segment.durationSeconds)
  const textLength = String(segment?.script || '').length
  return Math.round(Math.max(6, Math.min(24, (textLength * 180) / 1000)))
}

const segmentDurations = computed(() =>
  lessonSegments.value.map((segment, index) => audioDurations.value[segmentAudioKey(segment, index)] || estimateSegmentSeconds(segment))
)
const classroomDuration = computed(() => segmentDurations.value.reduce((sum, item) => sum + item, 0))
const elapsedBeforeActiveSegment = computed(() =>
  segmentDurations.value.slice(0, activeSegmentIndex.value).reduce((sum, item) => sum + item, 0)
)
const activeSegmentDuration = computed(() => segmentDurations.value[activeSegmentIndex.value] || 8)
const classroomCurrentTime = computed(() => {
  const localProgress = Math.min(1, Math.max(0, speechProgress.value / 100))
  return elapsedBeforeActiveSegment.value + activeSegmentDuration.value * localProgress
})

const formatClassroomTime = seconds => {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

const classroomTimelineLabel = computed(() =>
  `${formatClassroomTime(classroomCurrentTime.value)} / ${formatClassroomTime(classroomDuration.value)}`
)

const classroomProgressSegments = computed(() => {
  const duration = classroomDuration.value || 1
  let cursor = 0
  return lessonSegments.value.map((segment, index) => {
    const start = cursor
    const segmentDuration = segmentDurations.value[index] || 1
    cursor += segmentDuration
    return {
      id: segment.id || `segment-${index}`,
      start,
      end: cursor,
      left: (start / duration) * 100,
      width: (segmentDuration / duration) * 100,
      locked: false
    }
  })
})

const classroomProgressMarkers = computed(() =>
  classroomProgressSegments.value.map((segment, index) => ({
    id: `${segment.id}-marker`,
    label: lessonSegments.value[index]?.title || `环节 ${index + 1}`,
    time: segment.start,
    percent: segment.left,
    locked: false
  }))
)

const activeQuestion = computed(() => {
  if (activeSegment.value?.question?.prompt) {
    return {
      prompt: activeSegment.value.question.prompt,
      options: activeSegment.value.question.options?.length
        ? activeSegment.value.question.options
        : ['我能讲清楚', '我有点模糊', '我需要例子'],
      answer: activeSegment.value.question.answer,
      feedback: activeSegment.value.question.feedback
    }
  }
  if (!['concept', 'checkpoint'].includes(activeSegment.value?.id)) return null
  const title = node.value.title || '这个知识点'
  return {
    prompt: `如果让你快速判断自己是否理解「${title}」，最该先说清楚什么？`,
    options: [
      '概念之间的关系',
      '把定义逐字背下来',
      '先跳过，直接刷题'
    ]
  }
})

const showCheckpoint = computed(() => {
  const type = activeSegment.value?.type || activeSegment.value?.id || ''
  return Boolean(activeQuestion.value && /quiz|checkpoint|feynman/.test(type))
})

const checkpointFeedback = computed(() => {
  if (!selectedAnswer.value) return ''
  if (activeQuestion.value?.answer && selectedAnswer.value === activeQuestion.value.answer) {
    return activeQuestion.value.feedback || '对，这个回答抓住了本段的关键。'
  }
  if (activeQuestion.value?.answer && selectedAnswer.value !== activeQuestion.value.answer) {
    return `这个选项也能暴露思路，但本段更希望你先抓「${activeQuestion.value.answer}」。`
  }
  if (selectedAnswer.value === '概念之间的关系') return '对，这类节点先抓关系，再用题目验证细节。'
  if (selectedAnswer.value === '把定义逐字背下来') return '定义有用，但如果只背定义，遇到变式题会很吃力。'
  return '刷题可以暴露问题，但完全跳过概念会让错题变成随机猜。'
})

const activeResourceCards = computed(() => {
  const refs = activeSegment.value?.resourceRefs || []
  const matched = []
  const used = new Set()
  for (const ref of refs) {
    const refTitle = String(ref.title || '').trim()
    const resource = resourceList.value.find(item => String(item.title || '').trim() === refTitle) || ref
    const key = String(resource.id || resource.title || refTitle)
    if (key && used.has(key)) continue
    used.add(key)
    matched.push({
      ...resource,
      title: resource.title || refTitle,
      typeLabel: resource.typeLabel || resource.type || '资料',
      summary: resource.summary || resource.content || ref.how_to_use || ''
    })
  }
  if (matched.length) return matched.slice(0, 3)
  return resourceList.value.slice(0, 2)
})

const resourceBrief = resource => {
  const candidates = [
    resource.summary,
    resource.description,
    resource.abstract,
    resource.content,
    resource.text,
    resource.how_to_use
  ]
  const content = candidates
    .map(item => String(item || '').replace(/\s+/g, ' ').trim())
    .find(Boolean)
  return content ? content.slice(0, 120) : '暂无可展示摘录，课堂会优先使用节点知识继续讲解。'
}

const classroomResourceId = resource => String(
  resource?.resourceId ||
  resource?.resource_id ||
  resource?.sourceId ||
  resource?.fileId ||
  resource?.file_id ||
  resource?.id ||
  resource?.title ||
  ''
).trim()

const classroomResourcePreviewUrl = resource => resolveApiUrl(
  resource?.previewUrl ||
  resource?.preview_url ||
  resource?.fileUrl ||
  resource?.file_url ||
  resource?.url ||
  resource?.downloadUrl ||
  resource?.download_url ||
  ''
)

const classroomResourceDownloadUrl = resource => resolveApiUrl(
  resource?.downloadUrl ||
  resource?.download_url ||
  resource?.fileUrl ||
  resource?.file_url ||
  resource?.url ||
  resource?.previewUrl ||
  resource?.preview_url ||
  ''
)

const classroomResourceType = resource => resource?.fileType || resource?.file_type || resource?.type || resource?.typeLabel || 'file'

const canPreviewClassroomResource = resource => Boolean(classroomResourcePreviewUrl(resource) || resource?.content || resource?.summary)

const canDownloadClassroomResource = resource => Boolean(classroomResourceDownloadUrl(resource))

const isClassroomResourceSaved = resource => savedClassroomResourceIds.value.has(classroomResourceId(resource))

const previewClassroomResource = resource => {
  const url = classroomResourcePreviewUrl(resource)
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }
  if (resource?.content || resource?.summary) {
    window.alert(resource.content || resource.summary)
  }
}

const saveClassroomResource = resource => {
  const sourceId = classroomResourceId(resource)
  if (!sourceId) return
  saveGeneratedResourceRef({
    sourceId,
    kind: resource?.resourceKind || resource?.kind || 'resource',
    fileType: classroomResourceType(resource),
    category: 'reference',
    title: resource?.title || '课堂学习资源',
    filename: resource?.filename || resource?.file_name || resource?.title || '课堂学习资源',
    content: resource?.content || resource?.summary || resource?.description || '',
    coverUrl: resource?.coverUrl || resource?.cover_url || '',
    previewUrl: classroomResourcePreviewUrl(resource),
    downloadUrl: classroomResourceDownloadUrl(resource),
    annotations: Array.isArray(resource?.annotations) ? resource.annotations : [],
    visibility: 'private'
  })
  savedClassroomResourceIds.value = new Set([...savedClassroomResourceIds.value, sourceId])
}

const downloadClassroomResource = async resource => {
  const url = classroomResourceDownloadUrl(resource)
  if (!url) return
  try {
    await downloadWithToken(url, resource?.filename || resource?.file_name || resource?.title || '课堂学习资源')
  } catch (err) {
    console.error('[LearningClassroom] download resource failed:', err)
    window.alert(err?.message || '下载失败，请稍后再试。')
  }
}

const loadClassroomLesson = async () => {
  const pathId = String(launchPayload.value?.pathId || route.params.pathId || '')
  const nodeId = String(node.value.id || node.value.node_id || node.value.nodeId || route.params.nodeId || '')
  if (!/^\d+$/.test(pathId) || !/^\d+$/.test(nodeId)) return

  classroomLoading.value = true
  classroomError.value = ''
  try {
    const result = await generateNodeClassroom(pathId, nodeId, {
      node: node.value,
      resources: resourceList.value,
      quiz: quiz.value
    })
    const data = result?.data?.data || result?.data || result
    classroomLesson.value = data?.lesson || null
    classroomResources.value = Array.isArray(data?.resources)
      ? data.resources.map((item, index) => ({
          id: `remote-${index}`,
          title: item.title || `课堂资料 ${index + 1}`,
          typeLabel: item.type || '资料',
          summary: item.summary || ''
        }))
      : []
    if (classroomLesson.value?.personal_summary) {
      pushTeacher(classroomLesson.value.personal_summary)
    }
  } catch (err) {
    classroomError.value = err?.response?.data?.detail || err?.message || '课堂内容生成失败'
  } finally {
    classroomLoading.value = false
  }
}

const pushTeacher = content => {
  messages.value.push({
    id: `teacher-${Date.now()}-${messages.value.length}`,
    role: 'teacher',
    content
  })
}

const pushLearner = content => {
  messages.value.push({
    id: `learner-${Date.now()}-${messages.value.length}`,
    role: 'learner',
    content
  })
}

const stopLectureAudio = () => {
  isSpeaking.value = false
  if (lectureAudio) {
    lectureAudio.pause()
    lectureAudio.ontimeupdate = null
    lectureAudio.onloadedmetadata = null
    lectureAudio.onended = null
    lectureAudio.onerror = null
    lectureAudio = null
  }
}

const getClassroomAudioUrl = async () => {
  const text = activeSegment.value?.script || ''
  if (!text) return ''
  const key = currentAudioKey.value
  if (audioUrls.value[key]) return audioUrls.value[key]

  audioLoading.value = true
  audioError.value = ''
  try {
    const result = await narrateClassroomText({
      text,
      voice: 'zh-CN-XiaoxiaoNeural',
      rate: '+0%'
    })
    const payload = result?.data?.data || result?.data || result
    const url = resolveApiUrl(payload?.audio_url || payload?.url || '')
    if (!url) throw new Error('未返回音频地址')
    audioUrls.value = { ...audioUrls.value, [key]: url }
    return url
  } catch (err) {
    audioError.value = err?.response?.data?.detail || err?.message || '小知语音生成失败'
    pushTeacher(audioError.value)
    return ''
  } finally {
    audioLoading.value = false
  }
}

const toggleLectureAudio = async () => {
  if (isSpeaking.value) {
    stopLectureAudio()
    return
  }
  const requestedKey = currentAudioKey.value
  const url = await getClassroomAudioUrl()
  if (!url || requestedKey !== currentAudioKey.value) {
    return
  }

  stopLectureAudio()
  const key = requestedKey
  const audio = new Audio(url)
  lectureAudio = audio
  audio.onloadedmetadata = () => {
    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      audioDurations.value = { ...audioDurations.value, [key]: Math.round(audio.duration) }
    }
  }
  audio.ontimeupdate = () => {
    const duration = audio.duration || activeSegmentDuration.value || 1
    speechProgress.value = Math.min(100, Math.max(0, (audio.currentTime / duration) * 100))
  }
  audio.onended = () => {
    speechProgress.value = 100
    isSpeaking.value = false
  }
  audio.onerror = () => {
    isSpeaking.value = false
    audioError.value = '音频播放失败'
  }
  try {
    await audio.play()
    isSpeaking.value = true
  } catch (err) {
    isSpeaking.value = false
    audioError.value = err?.message || '浏览器阻止了音频播放'
  }
}

const seekClassroom = time => {
  const targetTime = Math.max(0, Number(time) || 0)
  const segments = classroomProgressSegments.value
  const index = segments.findIndex(segment => targetTime >= segment.start && targetTime < segment.end)
  const nextIndex = index >= 0 ? index : Math.max(0, segments.length - 1)
  stopLectureAudio()
  selectedAnswer.value = ''
  activeSegmentIndex.value = nextIndex
  speechProgress.value = 0
}

const prevSegment = () => {
  selectedAnswer.value = ''
  stopLectureAudio()
  activeSegmentIndex.value = Math.max(0, activeSegmentIndex.value - 1)
  pushTeacher(`我们回到「${activeSegment.value.title}」，重新看这一段。`)
}

const nextSegment = () => {
  selectedAnswer.value = ''
  stopLectureAudio()
  if (activeSegmentIndex.value < lessonSegments.value.length - 1) {
    activeSegmentIndex.value += 1
    pushTeacher(`接下来进入「${activeSegment.value.title}」。${activeSegment.value.intent}。`)
    return
  }
  pushTeacher('这一节的课堂流程完成了。建议你用费曼讲述再讲一遍，然后回到路径完成检测。')
}

const reviewFeynmanAnswer = () => {
  const text = feynmanAnswer.value
  const title = node.value.title || '当前知识点'
  if (text.length < 24) {
    feynmanFeedback.value = `讲得还太短。试着补一句：${title} 解决了什么问题，以及它和前后知识点有什么关系。`
  } else {
    feynmanFeedback.value = '表达已经能看出你的理解了。下一步可以补一个例子，说明这个知识点在题目里怎么用。'
  }
  pushLearner(text)
  pushTeacher(feynmanFeedback.value)
  feynmanAnswer.value = ''
}

const sendLearnerMessage = () => {
  const text = learnerInput.value
  if (!text) return
  pushLearner(text)
  learnerInput.value = ''
  if (/不会|不懂|没懂|为什么|怎么/.test(text)) {
    pushTeacher(`我们先不急着往后走。围绕「${activeSegment.value.title}」，你可以先抓住板书里的第一条，再看它和第二条的关系。`)
  } else {
    pushTeacher('这个表达可以继续往下压实。你再试着加一个“例子”或“反例”，理解会更稳。')
  }
}

const backToPath = () => {
  router.push({ name: 'learningPath' })
}

onMounted(() => {
  profileSnapshot.value = readStoredProfileSnapshot()
  launchPayload.value = readJson(sessionStorage, CLASSROOM_LAUNCH_KEY) || normalizeNodeFromCache() || normalizeNodeFromRoute()
  pushTeacher(`欢迎来到「${node.value.title || '互动课堂'}」。这节课会按“讲解、资料验证、课堂追问、费曼讲述”的顺序推进。`)
  void loadClassroomLesson()
})

watch(activeSegmentIndex, () => {
  stopLectureAudio()
  speechProgress.value = 0
  selectedAnswer.value = ''
})

watch(lessonSegments, segments => {
  if (activeSegmentIndex.value >= segments.length) {
    activeSegmentIndex.value = Math.max(0, segments.length - 1)
  }
})

onBeforeUnmount(stopLectureAudio)
</script>

<style scoped>
.classroom-page {
  min-height: calc(100vh - 78px);
  padding: 14px clamp(18px, 3.8vw, 64px) 20px;
  color: #123f7a;
  background:
    radial-gradient(circle at 16% 12%, rgba(50, 132, 224, 0.12), transparent 28%),
    linear-gradient(180deg, #eef7ff 0%, #f7fbff 100%);
}

.classroom-header,
.classroom-shell {
  max-width: 1760px;
  margin: 0 auto;
}

.classroom-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.classroom-header p,
.section-head small {
  margin: 0;
  color: #5d8fc2;
  font-weight: 800;
}

.classroom-header h1 {
  margin: 2px 0 0;
  font-size: clamp(23px, 2.4vw, 34px);
  color: #0e4387;
}

.lesson-clock {
  margin-left: auto;
  padding: 8px 14px;
  border-radius: 999px;
  background: #e6f2ff;
  color: #0d4690;
  font-weight: 900;
}

.classroom-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(300px, 20vw, 340px);
  grid-template-rows: auto minmax(650px, auto) auto;
  gap: 10px 16px;
  height: auto;
  min-height: min(790px, calc(100vh - 118px));
  max-height: none;
  align-items: start;
}

.lesson-rail,
.teaching-stage,
.resource-shelf section,
.dialog-panel {
  border: 1px solid #cfe1f2;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16px 34px rgba(38, 93, 150, 0.08);
}

.lesson-rail {
  grid-column: 1;
  grid-row: 1;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  min-height: 54px;
  padding: 6px;
  overflow: visible;
  border-radius: 18px;
}

.lesson-step {
  display: flex;
  gap: 7px;
  align-items: center;
  min-width: 0;
  padding: 6px 8px;
  border-radius: 13px;
  cursor: pointer;
  transition: background 160ms ease, transform 160ms ease;
}

.lesson-step:hover {
  transform: translateY(-1px);
  background: #eef7ff;
}

.lesson-step > div {
  min-width: 0;
}

.lesson-step span {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e8f2fc;
  color: #4d83bd;
  font-weight: 900;
}

.lesson-step.active {
  background: #eaf4ff;
}

.lesson-step.active span,
.lesson-step.done span {
  background: #174a99;
  color: white;
}

.lesson-step strong {
  display: -webkit-box;
  overflow: hidden;
  color: #113f7c;
  font-size: 14px;
  line-height: 1.22;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.lesson-step small {
  display: -webkit-box;
  overflow: hidden;
  color: #6f93b8;
  font-size: 12px;
  line-height: 1.3;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.teaching-stage {
  grid-column: 1;
  grid-row: 2;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: min(700px, calc(100vh - 190px));
  padding: 12px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(242, 250, 255, 0.74));
}

.voice-btn {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 15px;
  border: 0;
  border-radius: 999px;
  color: white;
  background: #174a99;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(23, 74, 153, 0.2);
}

.voice-btn:disabled {
  cursor: wait;
}

.lecture-player {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto auto;
  gap: 6px;
  flex: 1 1 auto;
  min-height: 0;
  padding: 0;
  border: 0;
  border-radius: 24px;
  background: transparent;
}

.classroom-player {
  position: relative;
  overflow: hidden;
  box-shadow: none;
}

.classroom-player::before {
  display: none;
}

.player-meta {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 4px 6px;
  border-radius: 16px;
  color: #164b96;
  background: transparent;
}

.player-meta span,
.player-meta strong,
.player-meta em,
.player-meta small {
  line-height: 1;
}

.player-meta span {
  font-size: 13px;
  font-weight: 900;
  color: #5d8fc2;
}

.player-meta strong {
  padding: 6px 9px;
  border-radius: 999px;
  color: white;
  background: #174a99;
  font-size: 13px;
}

.player-meta em {
  min-width: 0;
  overflow: hidden;
  color: #123f7a;
  font-style: normal;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-meta small {
  justify-self: end;
  color: #5d8fc2;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.lecture-player.speaking {
  box-shadow: none;
}

.classroom-screen {
  position: relative;
  display: block;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  border: 1px solid rgba(166, 208, 240, 0.92);
  border-radius: 26px;
  background:
    linear-gradient(110deg, rgba(7, 58, 124, 0.1) 0 46%, transparent 46%),
    radial-gradient(circle at 84% 22%, rgba(94, 183, 232, 0.28), transparent 28%),
    linear-gradient(135deg, rgba(252, 254, 255, 0.98), rgba(222, 242, 255, 0.96));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.78),
    0 22px 48px rgba(33, 90, 153, 0.12);
}

.screen-backdrop {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    repeating-linear-gradient(0deg, transparent 0 23px, rgba(23, 74, 153, 0.045) 24px),
    repeating-linear-gradient(90deg, transparent 0 23px, rgba(23, 74, 153, 0.045) 24px);
}

.screen-backdrop span {
  position: absolute;
  border: 1px solid rgba(23, 74, 153, 0.1);
  background: rgba(255, 255, 255, 0.3);
}

.screen-backdrop span:nth-child(1) {
  width: 160px;
  height: 160px;
  right: -48px;
  top: -42px;
  border-radius: 50%;
}

.screen-backdrop span:nth-child(2) {
  width: 210px;
  height: 42px;
  left: 34px;
  bottom: 112px;
  border-radius: 999px;
  transform: rotate(-12deg);
}

.screen-backdrop span:nth-child(3) {
  width: 110px;
  height: 110px;
  left: 48%;
  top: 20px;
  border-radius: 26px;
  transform: rotate(8deg);
}

.cinema-scene {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px;
  gap: 8px;
  height: 100%;
  min-height: 0;
  padding: 10px;
  overflow: hidden;
}

.lesson-canvas {
  position: relative;
  display: grid;
  grid-template-rows: minmax(0, auto) auto auto;
  align-content: start;
  gap: 8px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: clamp(14px, 1.4vw, 20px);
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.6), rgba(244, 251, 255, 0.38)),
    repeating-linear-gradient(0deg, transparent 0 27px, rgba(26, 84, 145, 0.04) 28px);
  border: 0;
}

.lesson-canvas::after {
  content: "";
  position: absolute;
  right: -42px;
  top: -42px;
  width: 190px;
  height: 190px;
  border: 1px solid rgba(23, 74, 153, 0.08);
  border-radius: 42px;
  transform: rotate(8deg);
  pointer-events: none;
}

.scene-copy {
  position: relative;
  z-index: 1;
  min-width: 0;
  overflow: hidden;
}

.scene-copy h2 {
  display: -webkit-box;
  overflow: hidden;
  margin: 4px 0 6px;
  color: #0b3f83;
  font-size: clamp(28px, 2.35vw, 42px);
  line-height: 1.08;
  letter-spacing: 0;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.scene-lead {
  display: -webkit-box;
  overflow: hidden;
  max-width: 960px;
  margin: 0;
  color: #315f92;
  font-size: clamp(15px, 1.15vw, 18px);
  font-weight: 900;
  line-height: 1.48;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.scene-lines {
  display: grid;
  gap: 5px;
  max-width: 1040px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.scene-lines li {
  position: relative;
  display: -webkit-box;
  overflow: hidden;
  padding-left: 14px;
  color: #416d9b;
  font-weight: 800;
  line-height: 1.38;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.scene-lines li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #1c66bd;
}

.concept-lane {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 6px;
  max-height: 86px;
  overflow: hidden;
}

.concept-pill {
  min-width: 0;
  min-height: 42px;
  padding: 7px 9px;
  border-radius: 10px;
  color: #0e4387;
  background: rgba(255, 255, 255, 0.48);
  border: 1px solid rgba(181, 215, 240, 0.66);
  font-weight: 900;
  line-height: 1.28;
  box-shadow: none;
}

.concept-pill small {
  display: block;
  margin-bottom: 4px;
  color: #5d8fc2;
  font-size: 12px;
}

.scene-example {
  position: relative;
  z-index: 1;
  min-width: 0;
  max-height: 58px;
  overflow: hidden;
  padding: 8px 0 0;
  border-top: 1px solid rgba(111, 164, 216, 0.32);
  border-left: 0;
  border-radius: 0;
  background: transparent;
}

.scene-example span {
  display: block;
  margin-bottom: 4px;
  color: #5d8fc2;
  font-size: 12px;
  font-weight: 900;
}

.scene-example strong {
  display: -webkit-box;
  overflow: hidden;
  color: #123f7a;
  line-height: 1.45;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.teacher-layer {
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(82px, 1fr) auto auto;
  align-items: center;
  justify-items: center;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: 2px 0;
  border-radius: 20px;
  background: transparent;
  border: 0;
}

.teacher-layer img {
  width: min(120px, 88%);
  max-height: 132px;
  object-fit: contain;
  filter: drop-shadow(0 18px 26px rgba(43, 101, 163, 0.18));
}

.teacher-layer p {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: #315f92;
  text-align: center;
  font-weight: 900;
  font-size: 14px;
  line-height: 1.36;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.lecture-label {
  position: static;
  z-index: 3;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  color: #174a99;
  background: rgba(255, 255, 255, 0.84);
  font-weight: 900;
}

.voice-bars {
  position: static;
  z-index: 3;
  display: inline-flex;
  align-items: end;
  gap: 4px;
  height: 34px;
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(23, 74, 153, 0.1);
}

.voice-bars i {
  width: 4px;
  height: 10px;
  border-radius: 999px;
  background: #2f80d5;
  opacity: 0.42;
}

.lecture-player.speaking .voice-bars i {
  animation: voicePulse 720ms ease-in-out infinite;
  opacity: 1;
}

.lecture-player.speaking .voice-bars i:nth-child(2) {
  animation-delay: 90ms;
}

.lecture-player.speaking .voice-bars i:nth-child(3) {
  animation-delay: 180ms;
}

.lecture-player.speaking .voice-bars i:nth-child(4) {
  animation-delay: 270ms;
}

.lecture-player.speaking .voice-bars i:nth-child(5) {
  animation-delay: 360ms;
}

.caption-bar {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 8px;
  min-height: 40px;
  max-height: 46px;
  margin: 0;
  padding: 7px 10px;
  overflow: hidden;
  color: #244e82;
  background: rgba(12, 48, 96, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  border-color: rgba(255, 255, 255, 0.16);
}

.caption-bar strong {
  flex: 0 0 auto;
  color: #9dd5ff;
}

.caption-bar span {
  display: -webkit-box;
  overflow: hidden;
  color: white;
  line-height: 1.35;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.segment-kicker {
  width: fit-content;
  margin-bottom: 7px;
  padding: 5px 9px;
  border-radius: 999px;
  color: #0e4387;
  background: #e6f2ff;
  font-weight: 900;
  font-size: 13px;
}

.classroom-progress {
  position: relative;
  z-index: 1;
  padding: 2px 8px 0;
  border-radius: 999px;
  background: transparent;
}

.checkpoint-card {
  margin-top: 8px;
  padding: 10px;
  border-radius: 18px;
  background: #fff8e8;
  border: 1px solid #f1d8a9;
}

.checkpoint-card h3 {
  margin: 6px 0 10px;
  color: #8a5013;
  font-size: 16px;
}

.checkpoint-card > span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #a35f12;
  font-weight: 900;
}

.checkpoint-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.checkpoint-options button,
.soft-btn,
.primary-btn,
.dialog-input button,
.feynman-panel button {
  border: 0;
  border-radius: 999px;
  font-weight: 900;
  cursor: pointer;
}

.checkpoint-options button {
  padding: 8px 12px;
  color: #805013;
  background: white;
}

.checkpoint-options button.selected {
  color: white;
  background: #c7801e;
}

.checkpoint-feedback {
  margin: 8px 0 0;
  color: #8a5013;
  font-weight: 800;
}

.stage-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex: 0 0 auto;
  margin-top: 2px;
  padding: 0;
  background: transparent;
}

.soft-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: white;
  color: #164b96;
  border: 1px solid #cfe1f2;
}

.primary-btn {
  padding: 10px 22px;
  background: #164b96;
  color: white;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.resource-shelf {
  grid-column: 2;
  grid-row: 1 / span 3;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  max-height: 100%;
  padding-right: 0;
  font-size: 12px;
  overflow-y: hidden;
  overflow-x: hidden;
}

.resource-shelf section {
  flex: 0 0 auto;
  padding: 9px 10px;
  border-radius: 16px;
  box-shadow: none;
}

.resource-shelf .personal-panel {
  display: none;
}

.resource-shelf .dialog-panel {
  display: flex;
  order: 3;
  flex: 1 1 270px;
  min-height: 260px;
}

.resource-shelf .dialog-panel .dialog-messages {
  max-height: none;
}

.resource-shelf .dialog-panel .dialog-input {
  margin-top: 8px;
}

.resource-shelf .dialog-panel .dialog-input input {
  padding: 9px 11px;
  font-size: 12px;
}

.resource-shelf .dialog-panel .dialog-input button {
  padding: 0 14px;
  font-size: 13px;
}

.resource-shelf .dialog-panel .dialog-messages article {
  padding: 8px 10px;
}

.resource-shelf .dialog-panel .dialog-messages p {
  font-size: 13px;
  line-height: 1.45;
}

.resource-shelf .dialog-panel .section-head {
  margin-bottom: 8px;
}

.resource-shelf .dialog-panel .section-head span {
  font-size: 18px;
}

.resource-shelf .dialog-panel .section-head small {
  font-size: 12px;
}

.resource-shelf .feynman-panel {
  order: 2;
  min-height: 0;
}

.resource-shelf > section:not(.personal-panel):not(.feynman-panel):not(.dialog-panel) {
  order: 1;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  font-weight: 900;
  color: #123f7a;
}

.resource-shelf .section-head span {
  font-size: 17px;
  line-height: 1.2;
}

.section-head small {
  overflow: hidden;
  max-width: 96px;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-list {
  display: grid;
  gap: 6px;
}

.resource-card {
  padding: 7px 8px;
  border-radius: 13px;
  background: rgba(244, 249, 255, 0.72);
  border: 1px solid rgba(216, 232, 246, 0.9);
}

.resource-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.resource-card span {
  color: #5d8fc2;
  font-size: 12px;
  font-weight: 800;
}

.resource-card__actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
}

.resource-card__actions button {
  min-width: 0;
  height: 22px;
  padding: 0 5px;
  border: 1px solid rgba(111, 164, 216, 0.32);
  border-radius: 999px;
  color: #164b96;
  background: rgba(255, 255, 255, 0.84);
  font-size: 10px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}

.resource-card__actions button:not(:disabled):hover {
  color: #ffffff;
  background: #164b96;
}

.resource-card strong {
  display: -webkit-box;
  overflow: hidden;
  margin: 2px 0;
  color: #123f7a;
  font-size: 13px;
  line-height: 1.32;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.resource-card p,
.empty-copy,
.feynman-panel p,
.personal-panel p {
  margin: 0;
  color: #6388ad;
  line-height: 1.46;
}

.resource-card p {
  display: -webkit-box;
  overflow: hidden;
  font-size: 12px;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.personal-panel p,
.feynman-panel p {
  display: -webkit-box;
  overflow: hidden;
  font-size: 13px;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.strategy-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 7px;
}

.strategy-tags span {
  padding: 4px 8px;
  border-radius: 999px;
  color: #0d4b93;
  background: #e8f3ff;
  font-size: 12px;
  font-weight: 900;
}

.feynman-panel {
  opacity: 0.76;
}

.feynman-panel.unlocked {
  opacity: 1;
}

.feynman-panel textarea {
  width: 100%;
  min-height: 48px;
  margin-top: 7px;
  padding: 8px 10px;
  resize: vertical;
  border: 1px solid #d1e3f2;
  border-radius: 16px;
  color: #123f7a;
  font-size: 12px;
  background: white;
}

.feynman-panel button {
  width: 100%;
  margin-top: 6px;
  padding: 8px;
  color: white;
  font-size: 13px;
  background: #164b96;
}

.feynman-feedback {
  margin-top: 10px !important;
  color: #0e7b62 !important;
  font-weight: 800;
}

.dialog-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.classroom-dialog-panel {
  grid-column: 1;
  grid-row: 3;
  flex: 0 0 auto;
  padding: 10px 12px;
  border-radius: 18px;
}

.teaching-stage > .classroom-dialog-panel {
  display: none;
}

.classroom-shell > .classroom-dialog-panel {
  display: none;
}

.classroom-dialog-panel .section-head {
  margin-bottom: 6px;
}

.classroom-dialog-panel .dialog-messages {
  max-height: 96px;
}

.classroom-dialog-panel .dialog-messages article {
  max-width: 86%;
  padding: 7px 10px;
}

.classroom-dialog-panel .dialog-messages p {
  display: -webkit-box;
  overflow: hidden;
  line-height: 1.42;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.classroom-dialog-panel .dialog-input {
  margin-top: 7px;
}

.classroom-dialog-panel .dialog-input input {
  padding: 8px 12px;
}

.dialog-messages {
  display: grid;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  overflow: auto;
}

.dialog-messages article {
  width: fit-content;
  max-width: 92%;
  padding: 9px 11px;
  border-radius: 14px;
  background: #eef7ff;
}

.dialog-messages article.learner {
  justify-self: end;
  background: #174a99;
  color: white;
}

.dialog-messages strong,
.dialog-messages p {
  margin: 0;
}

.dialog-messages p {
  margin-top: 3px;
  line-height: 1.5;
}

.dialog-input {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.dialog-input input {
  flex: 1;
  min-width: 0;
  padding: 11px 13px;
  border: 1px solid #d1e3f2;
  border-radius: 999px;
  color: #123f7a;
}

.dialog-input button {
  padding: 0 16px;
  color: white;
  background: #164b96;
}

@media (max-width: 1280px) {
  .classroom-shell {
    grid-template-columns: minmax(0, 1fr) 300px;
    gap: 10px 12px;
  }

  .cinema-scene {
    grid-template-columns: minmax(0, 1fr) 152px;
  }

  .scene-copy h2 {
    font-size: clamp(30px, 3vw, 46px);
  }
}

@media (max-width: 1080px) {
  .classroom-shell {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    height: auto;
    max-height: none;
  }

  .resource-shelf {
    grid-column: auto;
    grid-row: auto;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    max-height: none;
  }

  .resource-shelf .dialog-panel {
    grid-column: 1 / -1;
    min-height: 240px;
  }

  .lecture-player {
    grid-template-columns: 1fr;
  }

  .lesson-rail {
    grid-column: auto;
    grid-row: auto;
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .teaching-stage {
    grid-column: auto;
    grid-row: auto;
  }

  .lesson-step {
    align-items: flex-start;
  }

  .classroom-screen {
    height: auto;
    min-height: 520px;
  }

  .cinema-scene {
    grid-template-columns: 1fr;
  }

  .teacher-layer {
    grid-template-columns: auto auto 1fr;
    grid-template-rows: auto;
    justify-items: start;
    padding: 0 8px;
  }

  .teacher-layer img {
    width: 78px;
    max-height: 82px;
  }

  .teacher-layer p {
    text-align: left;
  }
}

@media (max-width: 720px) {
  .classroom-page {
    padding: 18px 12px;
  }

  .classroom-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .lesson-clock {
    margin-left: 0;
  }

  .lesson-rail {
    grid-template-columns: 1fr;
  }

  .resource-shelf {
    grid-template-columns: 1fr;
  }

  .stage-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .concept-lane {
    grid-template-columns: 1fr;
  }
}

@keyframes voicePulse {
  0%,
  100% {
    height: 8px;
  }

  50% {
    height: 24px;
  }
}

@keyframes orbitSpin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}
</style>
