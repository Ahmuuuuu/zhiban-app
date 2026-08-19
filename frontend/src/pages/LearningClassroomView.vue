<template>
  <main class="classroom-page">
    <header class="classroom-header">
      <button class="back-button" type="button" @click="backToPath">
        <ArrowLeft :size="18" /><span>返回路径</span>
      </button>
      <div class="classroom-heading">
        <p>Interactive Classroom</p>
        <h1>{{ node.title || '互动课堂' }}</h1>
      </div>
      <div class="generation-status" :class="{ loading: classroomLoading, error: classroomError }">
        <i class="status-dot" aria-hidden="true"></i>
        {{ classroomLoading ? '课堂生成中' : classroomError ? '课堂未生成' : '智能体已生成' }}
      </div>
    </header>

    <section class="classroom-layout">
      <section v-if="lessonSegments.length" class="lesson-workspace" aria-label="课堂内容">
        <nav class="module-nav" aria-label="课堂模块">
          <button
            v-for="(segment, index) in lessonSegments"
            :key="segment.id"
            class="module-tab"
            :class="{ active: index === activeSegmentIndex, done: index < activeSegmentIndex }"
            type="button"
            @click="selectSegment(index)"
          >
            <span class="module-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="module-tab-copy"><strong>{{ segment.title }}</strong><small>{{ segment.intent }}</small></span>
          </button>
        </nav>

        <article class="module-panel">
          <header class="module-panel-header">
            <div>
              <span class="module-kicker">模块 {{ activeSegmentIndex + 1 }} / {{ lessonSegments.length }}</span>
              <h2>{{ activeSegment.title }}</h2>
              <p v-if="activeSegment.subtitle" class="module-subtitle">{{ activeSegment.subtitle }}</p>
            </div>
            <div class="module-panel-actions">
              <button
                class="narration-button"
                type="button"
                :disabled="Boolean(narrationLoadingSegmentId)"
                :title="narrationTitle"
                :aria-label="narrationTitle"
                @click="toggleSegmentNarration()"
              >
                <LoaderCircle v-if="narrationLoadingSegmentId === activeSegment?.id" :size="18" class="spinning" />
                <Pause v-else-if="narrationSegmentId === activeSegment?.id && narrationPlaying" :size="18" fill="currentColor" />
                <Play v-else-if="narrationSegmentId === activeSegment?.id" :size="18" fill="currentColor" />
                <Volume2 v-else :size="18" />
              </button>
              <span class="interaction-badge">{{ interactionLabel }}</span>
            </div>
          </header>

          <div class="module-content">
            <section class="speech-block content-block">
              <span class="content-label">讲解</span><p>{{ activeSegment.script }}</p>
            </section>
            <section v-if="activeSegment.points.length" class="points-block content-block">
              <span class="content-label">抓住这几点</span>
              <ul><li v-for="point in activeSegment.points" :key="point">{{ point }}</li></ul>
            </section>
            <section v-if="activeSegment.id === 'exercise'" class="exercise-block content-block">
              <div class="exercise-heading">
                <span class="content-label">随堂练习</span>
              </div>
              <div v-if="classroomQuizLoading" class="exercise-state">正在生成练习题...</div>
              <div v-else-if="activeExerciseQuestion" class="exercise-card">
                <p class="exercise-stem">{{ activeExerciseQuestion.stem }}</p>
                <div v-if="activeExerciseQuestion.options.length" class="exercise-options">
                  <button
                    v-for="option in activeExerciseQuestion.options"
                    :key="option.key"
                    type="button"
                    :class="{ selected: isExerciseOptionSelected(option.key) }"
                    @click="toggleExerciseOption(option.key)"
                  >
                    <strong>{{ option.key }}</strong><span>{{ option.text }}</span>
                  </button>
                </div>
                <textarea v-else v-model.trim="exerciseTextAnswer" class="exercise-text-answer" maxlength="240" placeholder="输入你的答案"></textarea>
                <div v-if="exerciseChecked" class="exercise-result" :class="{ wrong: !exerciseCorrect }">
                  <strong>{{ exerciseCorrect ? '回答正确' : '回答错误' }}</strong>
                  <span v-if="!exerciseCorrect && activeExerciseQuestion.answer">正确答案：{{ activeExerciseQuestion.answer }}</span>
                  <p v-if="activeExerciseQuestion.explanation">{{ activeExerciseQuestion.explanation }}</p>
                </div>
                <footer class="exercise-actions">
                  <button type="button" class="exercise-check-button" :disabled="!exerciseHasAnswer || exerciseChecked" @click="checkExercise">{{ exerciseChecked ? '已判断' : '判断对错' }}</button>
                  <button type="button" class="exercise-open-button" @click="openFullQuiz">进入完整练习</button>
                </footer>
              </div>
              <div v-else class="exercise-state exercise-state-error">
                {{ classroomQuizError || '练习题尚未生成，暂不展示题目。' }}
                <button type="button" @click="loadClassroomQuiz">重新生成题目</button>
              </div>
            </section>
            <section v-else-if="activeSegment.example" class="example-block content-block">
              <span class="content-label">例子</span><p>{{ activeSegment.example }}</p>
            </section>
            <section v-if="activeSegment.id === 'feynman'" class="lesson-summary content-block">
              <div class="summary-heading"><span class="content-label">本节总结</span><span>学完带走</span></div>
              <p>{{ learningSummary }}</p>
              <ul v-if="keyTakeaways.length"><li v-for="item in keyTakeaways" :key="item">{{ item }}</li></ul>
            </section>
          </div>

          <footer class="module-footer">
            <button class="secondary-button" type="button" :disabled="activeSegmentIndex === 0" @click="prevSegment">上一个模块</button>
            <button class="primary-button" type="button" @click="nextSegment">
              {{ activeSegmentIndex === lessonSegments.length - 1 ? '开始右侧反讲' : '进入下一个模块' }}
            </button>
          </footer>
        </article>
      </section>

      <section v-else class="lesson-workspace lesson-generation-state" aria-live="polite">
        <div v-if="classroomLoading" class="classroom-waiting-panel">
          <header class="classroom-waiting-head">
            <span class="waiting-kicker"><LoaderCircle :size="16" class="spinning" /> 小知正在备课</span>
            <h2>正在生成课堂内容</h2>
            <p>这组内容会每 10 秒切换一次，课堂完成后自动收起。</p>
          </header>
          <div class="waiting-progress" aria-hidden="true"><i v-for="(_, index) in transitionSlides" :key="index" :class="{ active: index === transitionSlideIndex }"></i><span></span></div>
          <div v-if="transitionLoading" class="waiting-skeletons"><i></i><i></i><i></i></div>
          <Transition v-else name="waiting-slide" mode="out-in">
            <article :key="activeTransitionSlide.key" class="waiting-slide">
              <div class="waiting-section-heading">
                <Newspaper v-if="activeTransitionSlide.kind === 'news'" :size="18" />
                <Lightbulb v-else :size="18" />
                <span>{{ activeTransitionSlide.eyebrow }}</span>
              </div>
              <h3>{{ activeTransitionSlide.title }}</h3>
              <p>{{ activeTransitionSlide.content }}</p>
              <a v-if="activeTransitionSlide.url" :href="activeTransitionSlide.url" target="_blank" rel="noopener noreferrer" class="waiting-source-link">
                {{ activeTransitionSlide.meta || '打开公开来源' }} <ExternalLink :size="14" />
              </a>
              <span v-else class="waiting-slide-meta">{{ activeTransitionSlide.meta }}</span>
            </article>
          </Transition>
          <footer class="waiting-rotation-status"><span>{{ transitionSlideIndex + 1 }} / {{ transitionSlides.length }}</span><span>10 秒后切换</span></footer>
        </div>
        <div v-else class="lesson-generation-state-inner">
          <strong>{{ classroomError ? '课堂内容未生成完成' : '等待课堂内容' }}</strong>
          <p>{{ classroomError || '请等待智能体返回完整的四个模块。' }}</p>
          <button v-if="classroomError" class="retry-generation-button" type="button" :disabled="classroomLoading" @click="loadClassroomLesson(true)">
            重新生成课堂
          </button>
        </div>
      </section>

      <aside class="classroom-sidebar" aria-label="课堂辅助区域">
        <section class="resource-workbench content-block">
          <div class="resource-card-head">
            <span class="content-label"><FileText :size="15" /> 学习资源</span>
            <span class="resource-count">{{ resourceList.length }} 份</span>
          </div>
          <p class="resource-workbench-intro">资料会按当前节点生成，完成后可以直接在这里预览。</p>
          <div v-if="resourceList.length" class="resource-items">
            <article v-for="resource in resourceList" :key="resourceKey(resource)" class="resource-item">
              <div class="resource-item-copy">
                <span>{{ fileTypeLabel(resource) }}</span>
                <strong>{{ resourceTitle(resource) }}</strong>
                <p>{{ resourceBrief(resource) }}</p>
              </div>
              <button type="button" class="resource-open-button" :disabled="resourcePreviewLoading" @click="previewClassroomResource(resource)">
                <Eye :size="15" /> 预览
              </button>
            </article>
          </div>
          <div v-else class="resource-empty-state">当前节点还没有资源，点击下方按钮开始生成。</div>
          <p v-if="resourceGenerationStatus" class="resource-generation-status" aria-live="polite">
            {{ resourceGenerationStatus }}
          </p>
          <p v-if="resourceGenerationError" class="resource-generation-error">{{ resourceGenerationError }}</p>
          <button v-if="missingClassroomResourceTypes.length" class="resource-generate-button" type="button" :disabled="resourceGenerationLoading" @click="generateClassroomResources">
            {{ resourceGenerationLoading ? '正在生成...' : resourceList.length ? '继续生成缺少的资源' : '生成学习资料' }}
          </button>
        </section>

        <section class="dialog-panel" aria-label="课堂对话">
          <header class="dialog-header">
            <div><span class="dialog-eyebrow">小知助教</span><h2>课堂对话</h2></div>
            <span class="message-count">{{ messages.length }} 条</span>
          </header>
          <div ref="dialogMessagesEl" class="dialog-messages" @click.capture="handleRenderedMarkdownClick">
            <div v-if="!messages.length" class="dialog-empty">{{ lessonSegments.length ? '进入模块后，可以随时问小知。' : '课堂内容生成完成后，这里才会开始对话。' }}</div>
            <article v-for="message in messages" :key="message.id" class="message" :class="message.role">
              <span class="message-author">{{ message.role === 'teacher' ? '小知' : '我' }}</span>
              <div v-if="message.role === 'teacher'" class="markdown-body" v-html="renderMarkdown(message.content)"></div>
              <p v-else>{{ message.content }}</p>
            </article>
          </div>
          <form class="dialog-input" @submit.prevent="sendLearnerMessage">
            <input v-model.trim="learnerInput" :disabled="streamingTeacher || !lessonSegments.length" :placeholder="dialogPlaceholder" aria-label="输入课堂问题" />
            <button type="submit" :disabled="!learnerInput || streamingTeacher || !lessonSegments.length">{{ streamingTeacher ? '...' : '发送' }}</button>
          </form>
        </section>
      </aside>
    </section>

    <Teleport to="body">
      <section v-if="previewItem" class="resource-preview-overlay" @click.self="closeClassroomPreview">
        <article class="resource-preview-panel" role="dialog" aria-modal="true" :aria-label="previewItem.title">
          <header>
            <div><span>{{ previewItem.typeLabel }}</span><h2>{{ previewItem.title }}</h2></div>
            <div class="resource-preview-header-actions">
              <button v-if="previewItem.downloadUrl" type="button" class="resource-preview-download" @click="downloadClassroomResource(previewItem)"><Download :size="16" /> 下载</button>
              <button type="button" aria-label="关闭预览" @click="closeClassroomPreview"><X :size="20" /></button>
            </div>
          </header>
          <div class="resource-preview-body" :class="{ 'resource-preview-body--ppt': isPptResource(previewItem), 'resource-preview-body--mindmap': isMindmapResource(previewItem) }">
            <div v-if="resourcePreviewLoading" class="resource-preview-loading">正在加载预览...</div>
            <img v-else-if="isImageResource(previewItem) && previewItem.previewUrl" :src="previewItem.previewUrl" :alt="previewItem.title" />
            <PptPreview
              v-else-if="(isPptResource(previewItem) || isHtmlResource(previewItem)) && previewItem.slides?.length"
              v-model:slides="previewItem.slides"
              :title="previewItem.title"
              :editable="false"
              :annotatable="false"
              :annotations="[]"
            />
            <div v-else-if="isHtmlResource(previewItem) && previewItem.previewUrl" class="resource-html-placeholder">
              <strong>{{ previewItem.title }}</strong><a :href="previewItem.previewUrl" target="_blank" rel="noopener noreferrer">打开学习资料</a>
            </div>
            <MindmapPreview v-else-if="isMindmapResource(previewItem) && previewItem.content" :content="previewItem.content" :title="previewItem.title" />
            <AnnotatedTextPreview v-else-if="previewItem.content" :content="previewItem.content" :annotations="[]" :annotatable="false" />
            <pre v-else>暂无可预览内容，可以下载原文件查看。</pre>
          </div>
          <footer v-if="previewItem.downloadUrl">
            <button type="button" @click="downloadClassroomResource(previewItem)"><Download :size="16" /> 下载原文件</button>
          </footer>
        </article>
      </section>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Download, ExternalLink, Eye, FileText, Lightbulb, LoaderCircle, Newspaper, Pause, Play, Volume2, X } from 'lucide-vue-next'
import { generateNodeClassroom, generatePathNodeQuiz, generatePathNodeResourcesStream, getClassroomTransition, narrateClassroomText, streamClassroomChatMessage } from '../api/learningPath'
import { downloadWithToken, resolveApiUrl } from '../api/config'
import { getGeneratedResource } from '../api/resource'
import { renderMarkdown, handleRenderedMarkdownClick } from '../utils/markdown'
import { parseQuizQuestions, upsertQuizSet } from '../utils/quizBank'
import AnnotatedTextPreview from '../components/AnnotatedTextPreview.vue'
import MindmapPreview from '../components/MindmapPreview.vue'
import PptPreview from '../components/PptPreview.vue'

const CLASSROOM_LAUNCH_KEY = 'zhiban_classroom_launch'
const PATH_CACHE_KEY = 'zhiban_path_state'
const SEGMENT_IDS = ['lead-in', 'concept', 'exercise', 'feynman']
const CLASSROOM_RESOURCE_TYPES = ['document', 'ppt', 'mindmap']
const route = useRoute()
const router = useRouter()

const launchPayload = ref(null)
const classroomLesson = ref(null)
const classroomResources = ref([])
const generatedQuiz = ref(null)
const classroomLoading = ref(false)
const classroomError = ref('')
const transitionLoading = ref(false)
const transitionContent = ref({ news: [], activities: [], topic: '', profile_focus: '' })
const transitionSlideIndex = ref(0)
const resourceGenerationLoading = ref(false)
const resourceGenerationStatus = ref('')
const resourceGenerationError = ref('')
const activeSegmentIndex = ref(0)
const learnerInput = ref('')
const messages = ref([])
const streamingTeacher = ref(false)
const dialogMessagesEl = ref(null)
const previewItem = ref(null)
const resourcePreviewLoading = ref(false)
const classroomQuizQuestions = ref([])
const classroomQuizLoading = ref(false)
const classroomQuizError = ref('')
const exerciseSelected = ref([])
const exerciseTextAnswer = ref('')
const exerciseChecked = ref(false)
const exerciseCorrect = ref(false)
const narrationLoadingSegmentId = ref('')
const narrationSegmentId = ref('')
const narrationPlaying = ref(false)
let classroomNarrationAudio = null
let narrationRequestId = 0
let transitionRotationTimer = null

const readJson = (storage, key) => {
  try { const raw = storage?.getItem(key); return raw ? JSON.parse(raw) : null } catch { return null }
}
const node = computed(() => launchPayload.value?.node || {})
const pathId = computed(() => String(launchPayload.value?.pathId || route.params.pathId || ''))
const nodeId = computed(() => String(node.value.id || node.value.node_id || node.value.nodeId || route.params.nodeId || ''))
const resources = computed(() => Array.isArray(launchPayload.value?.resources) ? launchPayload.value.resources : [])
const resourceKey = resource => String(resource?.resourceId || resource?.resource_id || resource?.id || resource?.title || '').trim()
const resourceType = resource => [
  resource?.type,
  resource?.fileType,
  resource?.file_type,
  resource?.resource_type,
  resource?.typeLabel,
  resource?.filename,
  resource?.name,
  resource?.title
].filter(Boolean).join(' ').toLowerCase()
const quiz = computed(() => generatedQuiz.value || launchPayload.value?.quiz || null)
const transitionSlides = computed(() => {
  const activities = Array.isArray(transitionContent.value.activities) ? transitionContent.value.activities : []
  const news = Array.isArray(transitionContent.value.news) ? transitionContent.value.news : []
  const activitySlides = activities.map((item, index) => ({
    key: `activity-${index}`,
    kind: 'activity',
    eyebrow: '本节预想',
    title: String(item?.title || '整理一个问题'),
    content: String(item?.content || ''),
    meta: transitionContent.value.topic || node.value.title || '当前知识点'
  })).filter(item => item.content)
  const newsSlides = news.map((item, index) => ({
    key: `news-${item?.url || index}`,
    kind: 'news',
    eyebrow: '近日关注',
    title: String(item?.title || '近期公开资讯'),
    content: String(item?.summary || '打开来源查看详情。'),
    url: String(item?.url || ''),
    meta: String(item?.published_at || item?.source || '公开来源')
  })).filter(item => item.url)
  const slides = [...activitySlides, ...newsSlides]
  return slides.length ? slides : [{
    key: 'fallback', kind: 'activity', eyebrow: '本节预想',
    title: `先找出“${node.value.title || '当前知识点'}”的核心问题`,
    content: '先写下你最不确定的一个术语或步骤。课堂生成后，优先用核心概念和随堂练习核对它。',
    meta: '当前节点'
  }]
})
const activeTransitionSlide = computed(() => transitionSlides.value[transitionSlideIndex.value % transitionSlides.value.length])
const isQuizResource = resource => {
  if (!resource || typeof resource !== 'object') return false
  if (Array.isArray(resource.questions) || Array.isArray(resource.question_list) || Array.isArray(resource.questionList)) return true
  return /exercise|quiz|question|练习题|测验题|题目/.test(resourceType(resource))
}
const classroomResourceKind = resource => {
  const type = resourceType(resource)
  if (/mind|思维导图|脑图/.test(type)) return 'mindmap'
  if (/ppt|powerpoint|presentation|slide/.test(type)) return 'ppt'
  if (/document|doc|pdf|markdown|\.md\b|\.txt\b|文档/.test(type) || !type) return 'document'
  return ''
}
const isFailedResource = resource => {
  const content = resource?.content ?? resource?.preview ?? resource?.summary ?? ''
  const text = typeof content === 'string' ? content : JSON.stringify(content || '')
  return /^\s*\[(?:生成失败|generation failed|failed to generate)\b/i.test(text) ||
    /read operation timed out|incomplete chunked read|peer closed connection/i.test(text)
}
const resourceList = computed(() => {
  const byType = new Map()
  for (const item of [...resources.value, ...classroomResources.value]) {
    const type = classroomResourceKind(item)
    if (!item || isQuizResource(item) || isFailedResource(item) || !CLASSROOM_RESOURCE_TYPES.includes(type) || byType.has(type)) continue
    byType.set(type, item)
  }
  return CLASSROOM_RESOURCE_TYPES.map(type => byType.get(type)).filter(Boolean)
})
const missingClassroomResourceTypes = computed(() => CLASSROOM_RESOURCE_TYPES.filter(type => !resourceList.value.some(resource => classroomResourceKind(resource) === type)))
const clip = (value, limit) => {
  const text = String(value ?? '').replace(/\s+/g, ' ').trim()
  return text.length > limit ? `${text.slice(0, limit - 1).trim()}…` : text
}
const listValue = (value, limit, itemLimit) => {
  if (!Array.isArray(value)) return []
  const seen = new Set()
  return value.map(item => clip(item, itemLimit)).filter(item => item && !seen.has(item) && seen.add(item)).slice(0, limit)
}

const normalizeNodeFromCache = () => {
  const cached = readJson(localStorage, PATH_CACHE_KEY)
  const id = String(route.params.nodeId || route.query.nodeId || '')
  const found = (cached?.nodes || []).find(item => String(item.id || item.node_id || item.nodeId) === id)
  if (!found) return null
  return { pathId: cached.pathId || cached.path_id || route.params.pathId || '', node: found, resources: found._resources || found.resources || [], quiz: found._quiz || found.quiz || null }
}
const normalizeNodeFromRoute = () => ({
  pathId: route.params.pathId || '',
  node: { id: route.params.nodeId || '', title: route.query.title || '互动课堂', summary: route.query.summary || '围绕当前知识点完成理解、提问和总结。' },
  resources: [], quiz: null
})

const interactionFor = segment => {
  const raw = String(segment?.interaction || '')
  if (['reflect', 'open', 'exercise', 'feynman'].includes(raw)) return raw
  if (segment?.id === 'exercise' || segment?.type === 'exercise') return 'exercise'
  if (segment?.id === 'concept' || segment?.type === 'concept') return 'open'
  if (segment?.id === 'feynman' || segment?.type === 'feynman') return 'feynman'
  return 'reflect'
}
const normalizeSegment = (raw, index) => {
  const id = String(raw?.id || SEGMENT_IDS[index] || '')
  const question = raw?.question && typeof raw.question === 'object' ? raw.question : {}
  const contentPoints = [
    ...(Array.isArray(raw?.points) ? raw.points : []),
    ...(Array.isArray(raw?.board_items) ? raw.board_items : [])
  ]
  const normalizedPoints = listValue(contentPoints, 5, 70)
  return {
    id, type: String(raw?.type || ''), title: clip(raw?.title, 28), subtitle: clip(raw?.subtitle, 42), intent: clip(raw?.intent, 20),
    script: clip(raw?.teacher_speech || raw?.script, 240),
    points: normalizedPoints,
    example: clip(raw?.example || raw?.visual_hint, 100), interaction: interactionFor({ ...raw, id, type: raw?.type }),
    resourceRefs: Array.isArray(raw?.resource_refs) ? raw.resource_refs.filter(item => item && typeof item === 'object').slice(0, 3) : [],
    question: { prompt: clip(question.prompt, 120), options: listValue(question.options, 4, 42), answer: clip(question.answer, 42), feedback: clip(question.feedback, 100) }
  }
}
const lessonSegments = computed(() => {
  const remote = classroomLesson.value?.segments
  if (!Array.isArray(remote) || remote.length < SEGMENT_IDS.length) return []
  const byId = new Map(remote.map(item => [String(item?.id || ''), item]))
  if (SEGMENT_IDS.some(id => !byId.has(id))) return []
  return SEGMENT_IDS.map((id, index) => normalizeSegment(byId.get(id), index))
})
const activeSegment = computed(() => lessonSegments.value[activeSegmentIndex.value] || lessonSegments.value[0])
const activeExerciseQuestion = computed(() => classroomQuizQuestions.value[0] || null)
const exerciseHasAnswer = computed(() => activeExerciseQuestion.value?.options?.length
  ? exerciseSelected.value.length > 0
  : Boolean(String(exerciseTextAnswer.value || '').trim()))
const learningSummary = computed(() => clip(classroomLesson.value?.learning_summary, 180))
const keyTakeaways = computed(() => listValue(classroomLesson.value?.key_takeaways, 4, 48))
const interactionLabel = computed(() => ({ reflect: '想一想', open: '开放回答', exercise: '随堂练习', feynman: '右侧反讲' }[activeSegment.value?.interaction] || '课堂内容'))
const dialogPlaceholder = computed(() => activeSegment.value?.interaction === 'feynman' ? '把这个知识点讲给小知听...' : activeSegment.value?.interaction === 'open' ? '用自己的话回答当前问题...' : activeSegment.value?.interaction === 'exercise' ? '可以在这里追问这道题...' : '提问，或补充你的想法...')
const narrationTitle = computed(() => {
  const segmentId = activeSegment.value?.id
  if (narrationLoadingSegmentId.value === segmentId) return '正在生成本幕语音'
  if (narrationSegmentId.value !== segmentId) return '朗读本幕讲解和要点'
  return narrationPlaying.value ? '暂停朗读' : '继续朗读'
})
const isLessonReady = lesson => {
  const segments = lesson?.segments
  if (!Array.isArray(segments) || segments.length !== SEGMENT_IDS.length) return false
  const summary = String(lesson?.learning_summary || '').trim()
  const takeaways = Array.isArray(lesson?.key_takeaways) ? lesson.key_takeaways.filter(item => String(item || '').trim()) : []
  if (summary.length < 20 || takeaways.length < 2) return false
  const byId = new Map(segments.map(item => [String(item?.id || ''), item]))
  return SEGMENT_IDS.every(id => {
    const segment = byId.get(id)
    const script = String(segment?.teacher_speech || segment?.script || '').trim()
    const points = [...(Array.isArray(segment?.points) ? segment.points : []), ...(Array.isArray(segment?.board_items) ? segment.board_items : [])].filter(item => String(item || '').trim())
    const prompt = String(segment?.question?.prompt || '').trim()
    return Boolean(segment && segment.title && script.length >= 30 && points.length >= 2 && prompt.length >= 6)
  })
}

const extractQuizQuestions = payload => {
  const rawQuestions = payload?.questions || payload?.question_list || payload?.questionList || payload?.items || payload?.exam_questions
  if (Array.isArray(rawQuestions) && rawQuestions.length) {
    return parseQuizQuestions(JSON.stringify({ questions: rawQuestions }))
  }
  const content = typeof payload?.content === 'string' ? payload.content : ''
  return content ? parseQuizQuestions(content) : []
}

const resetExerciseState = () => {
  exerciseSelected.value = []
  exerciseTextAnswer.value = ''
  exerciseChecked.value = false
  exerciseCorrect.value = false
}

const narrationTextForSegment = segment => {
  if (!segment) return ''
  const parts = []
  if (segment.script) parts.push(`讲解。${segment.script}`)
  if (segment.points?.length) {
    const points = segment.points.map((point, index) => `第${index + 1}点，${point}`).join('。')
    parts.push(`抓住这几点。${points}`)
  }
  return clip(parts.join('。'), 500)
}
const clearSegmentNarration = () => {
  narrationRequestId += 1
  if (classroomNarrationAudio) {
    classroomNarrationAudio.pause()
    classroomNarrationAudio.currentTime = 0
    classroomNarrationAudio.onended = null
    classroomNarrationAudio.onerror = null
    classroomNarrationAudio.src = ''
    classroomNarrationAudio = null
  }
  narrationLoadingSegmentId.value = ''
  narrationSegmentId.value = ''
  narrationPlaying.value = false
}
const toggleSegmentNarration = async () => {
  const segment = activeSegment.value
  const segmentId = String(segment?.id || '')
  if (!segmentId || narrationLoadingSegmentId.value) return

  if (narrationSegmentId.value === segmentId && classroomNarrationAudio) {
    if (classroomNarrationAudio.paused) {
      try {
        await classroomNarrationAudio.play()
        narrationPlaying.value = true
      } catch (error) {
        console.warn('[LearningClassroom] resume segment narration failed:', error)
      }
    } else {
      classroomNarrationAudio.pause()
      narrationPlaying.value = false
    }
    return
  }

  const text = narrationTextForSegment(segment)
  if (!text) return
  clearSegmentNarration()
  const requestId = ++narrationRequestId
  narrationLoadingSegmentId.value = segmentId
  try {
    const result = await narrateClassroomText({ text })
    const data = result?.data?.data || result?.data || result || {}
    const audioUrl = resolveApiUrl(data?.audio_url || data?.audioUrl || '')
    if (!audioUrl) throw new Error('旁白音频地址为空')
    if (requestId !== narrationRequestId) return

    const audio = new Audio(audioUrl)
    classroomNarrationAudio = audio
    narrationSegmentId.value = segmentId
    audio.onended = () => {
      if (classroomNarrationAudio === audio) {
        classroomNarrationAudio = null
        narrationSegmentId.value = ''
        narrationPlaying.value = false
      }
    }
    audio.onerror = () => {
      if (classroomNarrationAudio === audio) {
        classroomNarrationAudio = null
        narrationSegmentId.value = ''
        narrationPlaying.value = false
      }
    }
    await audio.play()
    if (requestId === narrationRequestId) narrationPlaying.value = true
  } catch (error) {
    if (requestId === narrationRequestId) {
      narrationSegmentId.value = ''
      narrationPlaying.value = false
      console.warn('[LearningClassroom] segment narration failed:', error)
      window.alert(error?.response?.data?.detail || error?.message || '本幕语音生成失败，请稍后再试。')
    }
  } finally {
    if (requestId === narrationRequestId) narrationLoadingSegmentId.value = ''
  }
}

const loadClassroomQuiz = async () => {
  classroomQuizLoading.value = true
  classroomQuizError.value = ''
  classroomQuizQuestions.value = []
  resetExerciseState()
  try {
    let payload = quiz.value
    let questions = extractQuizQuestions(payload)
    if (!questions.length) {
      const result = await generatePathNodeQuiz(pathId.value, nodeId.value)
      payload = result?.data?.data || result?.data || result || {}
      if (payload.blocked) throw new Error(payload.reason || '当前节点暂时不能生成练习题')
      questions = extractQuizQuestions(payload)
      if (questions.length) generatedQuiz.value = payload
    }
    if (!questions.length) throw new Error('没有生成可展示的练习题，请稍后重试')
    classroomQuizQuestions.value = questions.slice(0, 8)
  } catch (error) {
    classroomQuizError.value = error?.response?.data?.detail || error?.message || '练习题生成失败'
  } finally {
    classroomQuizLoading.value = false
  }
}

const isExerciseOptionSelected = key => exerciseSelected.value.includes(key)
const toggleExerciseOption = key => {
  if (exerciseChecked.value) return
  const question = activeExerciseQuestion.value
  if (!question) return
  if (question.multi) {
    exerciseSelected.value = exerciseSelected.value.includes(key)
      ? exerciseSelected.value.filter(item => item !== key)
      : [...exerciseSelected.value, key]
  } else {
    exerciseSelected.value = [key]
  }
}
const normalizeExerciseAnswer = value => String(value ?? '')
  .toUpperCase()
  .replace(/[，、\s]+/g, ',')
  .replace(/[^A-Z0-9一二三四五六七八九十,]/g, '')
  .split(',')
  .filter(Boolean)
  .sort()
  .join(',')
const checkExercise = () => {
  const question = activeExerciseQuestion.value
  if (!question || !exerciseHasAnswer.value) return
  const actual = question.options?.length ? exerciseSelected.value.join(',') : exerciseTextAnswer.value
  const expected = normalizeExerciseAnswer(question.answer)
  exerciseCorrect.value = Boolean(expected) && normalizeExerciseAnswer(actual) === expected
  exerciseChecked.value = true
}
const openFullQuiz = () => {
  if (!classroomQuizQuestions.value.length) return
  const session = upsertQuizSet({
    id: `classroom-${pathId.value}-${nodeId.value}`,
    title: `${node.value.title || '当前节点'} - 随堂练习`,
    sessionId: quiz.value?.session_id || quiz.value?.sessionId || '',
    questions: classroomQuizQuestions.value,
  })
  if (!session) return
  router.push({ name: 'quizRunner', params: { quizId: session.id }, query: { from: 'path', pathId: pathId.value, nodeId: nodeId.value, sessionId: session.sessionId || '' } })
}

const loadClassroomLesson = async (forceRegenerate = false) => {
  if (!/^\d+$/.test(pathId.value) || !/^\d+$/.test(nodeId.value)) return
  classroomLoading.value = true
  classroomError.value = ''
  classroomLesson.value = null
  activeSegmentIndex.value = 0
  try {
    const result = await generateNodeClassroom(
      pathId.value,
      nodeId.value,
      { node: node.value, resources: resources.value, quiz: quiz.value, force_regenerate: forceRegenerate },
      { timeout: 480000 }
    )
    const data = result?.data?.data || result?.data || result
    const lesson = data?.lesson || null
    if (!isLessonReady(lesson)) throw new Error('智能体尚未生成完整课堂，暂不展示内容')
    classroomLesson.value = lesson
    // 资源流可能先于课堂接口返回，逐项合并避免旧快照覆盖已完成的资源卡片。
    for (const resource of (Array.isArray(data?.resources) ? data.resources : [])) appendGeneratedResource(resource)
    void loadClassroomQuiz()
  } catch (error) {
    classroomError.value = error?.response?.data?.detail || error?.message || '课堂内容生成失败'
  } finally { classroomLoading.value = false }
}
const loadClassroomTransition = async () => {
  if (!/^\d+$/.test(pathId.value) || !/^\d+$/.test(nodeId.value)) return
  transitionLoading.value = true
  try {
    const result = await getClassroomTransition(pathId.value, nodeId.value)
    const data = result?.data?.data || result?.data || result
    transitionContent.value = {
      news: Array.isArray(data?.news) ? data.news.slice(0, 3) : [],
      activities: Array.isArray(data?.activities) ? data.activities.slice(0, 3) : [],
      topic: String(data?.topic || ''),
      profile_focus: String(data?.profile_focus || '')
    }
    transitionSlideIndex.value = 0
  } catch {
    // 过渡内容不影响课堂主流程；搜索不可用时显示本地学习方案。
  } finally { transitionLoading.value = false }
}
const appendGeneratedResource = data => {
  const resource = {
    id: data?.resource_id || data?.resourceId || `generated-${Date.now()}`,
    resourceId: data?.resource_id || data?.resourceId || '',
    title: data?.title || data?.topic || `课堂资料 ${classroomResources.value.length + 1}`,
    type: data?.resource_type || data?.resourceType || data?.file_type || data?.fileType || '',
    resource_type: data?.resource_type || data?.resourceType || '',
    fileType: data?.file_type || data?.fileType || data?.resource_type || '',
    summary: data?.summary || data?.content || data?.preview || data?.text || '',
    content: data?.content || data?.preview || data?.text || '',
    downloadUrl: data?.download_url || data?.downloadUrl || data?.file_url || data?.fileUrl || data?.url || '',
    previewUrl: data?.preview_url || data?.previewUrl || data?.file_url || data?.fileUrl || data?.url || '',
    filename: data?.filename || data?.file_name || data?.title || '课堂学习资料'
  }
  const existingIndex = classroomResources.value.findIndex(item => {
    const sameId = resource.resourceId && String(resourceKey(item)) === String(resource.resourceId)
    const sameType = classroomResourceKind(item) === classroomResourceKind(resource)
    return sameId || (sameType && Boolean(classroomResourceKind(resource)))
  })
  if (existingIndex < 0) {
    classroomResources.value = [...classroomResources.value, resource]
  } else if (resource.resourceId || resource.previewUrl || resource.downloadUrl) {
    const next = [...classroomResources.value]
    next[existingIndex] = { ...next[existingIndex], ...resource }
    classroomResources.value = next
  }
}
const generateClassroomResources = async (options = {}) => {
  if (resourceGenerationLoading.value || !/^\d+$/.test(pathId.value) || !/^\d+$/.test(nodeId.value)) return
  const background = Boolean(options?.background)
  resourceGenerationLoading.value = true
  resourceGenerationStatus.value = '正在准备节点资源...'
  resourceGenerationError.value = ''
  let streamError = null
  try {
    await generatePathNodeResourcesStream(
      pathId.value,
      nodeId.value,
      appendGeneratedResource,
      data => { resourceGenerationStatus.value = data?.msg || data?.message || '正在生成学习资料...' },
      () => { resourceGenerationStatus.value = '学习资料生成完成，正在整理预览...' },
      error => { streamError = error || new Error('学习资料生成失败') },
      { resource_types: CLASSROOM_RESOURCE_TYPES, background }
    )
    if (streamError) throw streamError
    resourceGenerationStatus.value = `生成完成，共 ${resourceList.value.length} 份资源`
  } catch (error) {
    resourceGenerationError.value = error?.response?.data?.detail || error?.message || '资源生成失败，请稍后重试'
    resourceGenerationStatus.value = ''
  } finally {
    resourceGenerationLoading.value = false
  }
}
const resourceBrief = resource => {
  const candidates = [resource?.summary, resource?.description, resource?.abstract, resource?.content, resource?.text, resource?.how_to_use]
  const value = candidates.find(item => typeof item === 'string' && item.trim())
  if (value) return clip(value, 110)
  const topic = resource?.summary?.topic || resource?.content?.topic || resource?.content?.root?.topic
  return topic ? `围绕“${topic}”展开的结构化思维导图。` : '点击查看当前节点的学习资料。'
}
const resourceTitle = resource => String(resource?.title || resource?.topic || resource?.filename || resource?.name || '学习资料').trim()
const classroomResourceId = resource => Number(resource?.resourceId || resource?.resource_id || (/^\d+$/.test(String(resource?.id || '')) ? resource.id : 0))
const fileTypeLabel = resource => {
  const type = resourceType(resource)
  if (/ppt|powerpoint|presentation|slide/.test(type)) return 'PPT 课件'
  if (/mind/.test(type)) return '思维导图'
  if (/exercise|quiz|question/.test(type)) return '练习题'
  if (/image|png|jpg|jpeg|webp/.test(type)) return '图片资料'
  if (/html|video/.test(type)) return '学习视频'
  return '学习文档'
}
const isPptResource = resource => /ppt|powerpoint|presentation|slide/.test(resourceType(resource))
const isMindmapResource = resource => /mind/.test(resourceType(resource))
const isImageResource = resource => /image|png|jpg|jpeg|webp/.test(resourceType(resource))
const isHtmlResource = resource => /html|video/.test(resourceType(resource))
const resourceUrl = (resource, fields) => {
  const value = fields.map(field => resource?.[field]).find(Boolean) || ''
  return value ? resolveApiUrl(value) : ''
}
const parsePreviewSlides = content => {
  const text = String(content || '').trim()
  if (!text) return []
  try {
    const parsed = JSON.parse(text)
    const list = Array.isArray(parsed) ? parsed : parsed.slides || parsed.pages || parsed.items || []
    if (Array.isArray(list) && list.length) {
      return list.map((slide, index) => ({
        index,
        title: slide.title || slide.heading || `第 ${index + 1} 页`,
        text: slide.text || slide.content || slide.body || '',
        notes: slide.notes || slide.speaker_notes || '',
        ...(slide.layout ? { layout: slide.layout } : {}),
        ...(slide.theme ? { theme: slide.theme } : {}),
        ...(slide.visual ? { visual: slide.visual } : {})
      }))
    }
  } catch { /* PPT markdown is handled below. */ }
  return text
    .replace(/^```(?:json|markdown|md)?\s*/i, '')
    .replace(/```$/i, '')
    .split(/\n\s*---+\s*\n|(?=\n\s*#{1,3}\s+)/)
    .map(block => block.trim())
    .filter(Boolean)
    .map((block, index) => {
      const lines = block.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
      const titleLine = lines.find(line => /^#{1,3}\s+/.test(line)) || lines[0] || `第 ${index + 1} 页`
      return { index, title: titleLine.replace(/^#{1,3}\s+/, ''), text: lines.filter(line => line !== titleLine).join('\n'), notes: '' }
    })
}
const buildPreviewItem = (resource, detail = {}) => {
  const merged = { ...resource, ...detail }
  const rawContent = detail?.content ?? detail?.preview ?? detail?.text ?? resource?.content ?? ''
  const content = typeof rawContent === 'string' ? rawContent.trim() : rawContent
  const type = detail?.resource_type || detail?.resourceType || detail?.file_type || detail?.fileType || resource?.type || resource?.fileType || resource?.typeLabel || ''
  const id = classroomResourceId(merged)
  const slides = Array.isArray(detail?.slides) && detail.slides.length
    ? detail.slides
    : Array.isArray(resource?.slides) && resource.slides.length
      ? resource.slides
      : (isPptResource({ ...merged, type, content }) || isHtmlResource({ ...merged, type, content }) ? parsePreviewSlides(content) : [])
  return {
    ...merged,
    id: merged.id || id,
    resourceId: merged.resourceId || merged.resource_id || id,
    title: resourceTitle(merged),
    type,
    typeLabel: fileTypeLabel({ ...merged, type }),
    content,
    previewUrl: resourceUrl(merged, ['previewUrl', 'preview_url', 'fileUrl', 'file_url', 'url']),
    downloadUrl: resourceUrl(merged, ['downloadUrl', 'download_url', 'fileUrl', 'file_url', 'url']) || (id ? resolveApiUrl(`/resource/${id}/download`) : ''),
    slides
  }
}
const previewClassroomResource = async resource => {
  if (!resource || resourcePreviewLoading.value) return
  previewItem.value = buildPreviewItem(resource)
  const id = classroomResourceId(resource)
  if (!id) return
  resourcePreviewLoading.value = true
  try {
    const result = await getGeneratedResource(id)
    const detail = result?.data?.data || result?.data || result || {}
    previewItem.value = buildPreviewItem(resource, detail)
  } catch (error) {
    console.warn('[LearningClassroom] load resource preview failed:', error)
    previewItem.value = { ...previewItem.value, content: previewItem.value?.content || '预览加载失败，可以下载原文件查看。' }
  } finally {
    resourcePreviewLoading.value = false
  }
}
const closeClassroomPreview = () => { previewItem.value = null; resourcePreviewLoading.value = false }
const downloadClassroomResource = async resource => {
  if (!resource?.downloadUrl) return
  try { await downloadWithToken(resource.downloadUrl, resource.title || '学习资料') }
  catch (error) { window.alert(error?.message || '下载失败，请稍后再试。') }
}
const trimMessages = () => { if (messages.value.length > 40) messages.value.splice(0, messages.value.length - 40) }
const pushTeacher = content => { const text = clip(content, 500); if (text) { messages.value.push({ id: `teacher-${Date.now()}-${messages.value.length}`, role: 'teacher', content: text }); trimMessages() } }
const pushLearner = content => { const text = String(content || '').trim(); if (text) { messages.value.push({ id: `learner-${Date.now()}-${messages.value.length}`, role: 'learner', content: text }); trimMessages() } }
const announceSegmentPrompt = segment => {
  if (segment?.id === 'exercise') return
  const prompt = String(segment?.question?.prompt || '').trim()
  if (!prompt) return
  const message = segment.id === 'feynman'
    ? `请到右侧对话框完成反讲：${prompt}`
    : `想一想：${prompt} 你可以直接在右侧回答。`
  pushTeacher(message)
}

const streamTeacherReply = async ({ text, scenario = 'free', segment = activeSegment.value }) => {
  if (streamingTeacher.value) return
  const message = { id: `teacher-${Date.now()}-${messages.value.length}`, role: 'teacher', content: '正在思考...' }
  messages.value.push(message); trimMessages(); streamingTeacher.value = true
  let hasChunk = false
  try {
    await streamClassroomChatMessage({ path_id: Number(pathId.value), node_id: Number(nodeId.value), scenario, text, segment: { id: segment?.id, title: segment?.title, script: segment?.script, points: segment?.points, example: segment?.example, question: segment?.question } }, {
      onChunk: chunk => { if (chunk) { message.content = hasChunk ? `${message.content}${chunk}` : chunk; hasChunk = true } }
    })
    if (!hasChunk) message.content = '小知暂时没有生成回答，请稍后重试。'
  } catch (error) { message.content = error?.message || '小知暂时没有回应，请稍后再试。' }
  finally { streamingTeacher.value = false }
}
const sendLearnerMessage = () => {
  const text = learnerInput.value.trim(); if (!text || streamingTeacher.value || !lessonSegments.value.length) return
  learnerInput.value = ''; pushLearner(text)
  const interaction = activeSegment.value?.interaction
  void streamTeacherReply({ text, scenario: interaction === 'feynman' ? 'feynman' : interaction === 'open' ? 'open' : 'free', segment: activeSegment.value })
}
const selectSegment = index => { if (!streamingTeacher.value) { activeSegmentIndex.value = index; if (lessonSegments.value[index]?.id === 'exercise') resetExerciseState() } }
const prevSegment = () => { if (activeSegmentIndex.value > 0) activeSegmentIndex.value -= 1 }
const nextSegment = () => { if (activeSegmentIndex.value < lessonSegments.value.length - 1) activeSegmentIndex.value += 1 }
const backToPath = () => router.push({ name: 'learningPath' })

const stopTransitionRotation = () => {
  if (transitionRotationTimer !== null) window.clearInterval(transitionRotationTimer)
  transitionRotationTimer = null
}
const startTransitionRotation = () => {
  stopTransitionRotation()
  if (!classroomLoading.value || transitionSlides.value.length < 2) return
  transitionRotationTimer = window.setInterval(() => {
    transitionSlideIndex.value = (transitionSlideIndex.value + 1) % transitionSlides.value.length
  }, 10000)
}

onMounted(() => {
  document.body.classList.add('classroom-active')
  launchPayload.value = readJson(sessionStorage, CLASSROOM_LAUNCH_KEY) || normalizeNodeFromCache() || normalizeNodeFromRoute()
  // 课堂请求先发起，等待页的检索随后并行；两者互不等待，课堂结果优先展示。
  void loadClassroomLesson()
  void loadClassroomTransition()
  queueMicrotask(() => { void generateClassroomResources({ background: true }) })
})
onBeforeUnmount(() => { stopTransitionRotation(); clearSegmentNarration(); document.body.classList.remove('classroom-active') })
watch(activeSegmentIndex, index => { clearSegmentNarration(); const segment = lessonSegments.value[index]; if (segment) { if (segment.id === 'exercise') resetExerciseState(); announceSegmentPrompt(segment) } })
watch(lessonSegments, segments => { if (activeSegmentIndex.value >= segments.length) activeSegmentIndex.value = Math.max(0, segments.length - 1) })
watch(classroomLoading, loading => {
  if (loading) {
    startTransitionRotation()
  } else {
    stopTransitionRotation()
  }
}, { immediate: true })
watch(transitionSlides, () => { transitionSlideIndex.value = 0; startTransitionRotation() })
watch(messages, () => nextTick(() => { if (dialogMessagesEl.value) dialogMessagesEl.value.scrollTop = dialogMessagesEl.value.scrollHeight }), { deep: true })
</script>

<style scoped>
:global(body.classroom-active .study-pet--floating) { display: none; }
.classroom-page { --ink:#123f7a; --muted:#6d91b6; --line:#d4e5f5; --blue:#1d5caf; box-sizing:border-box; height:calc(100vh - 64px); min-height:560px; display:flex; flex-direction:column; gap:16px; padding:18px clamp(18px,4vw,64px) 24px; overflow:hidden; color:var(--ink); background:#f4f9fe; }
.classroom-header,.classroom-layout { width:min(1500px,100%); margin:0 auto; }
.classroom-header { display:flex; align-items:center; gap:16px; flex:0 0 auto; }
button { font:inherit; }
.back-button,.secondary-button,.primary-button,.module-tab,.question-options button,.dialog-input button { border:0; cursor:pointer; }
.back-button,.secondary-button { display:inline-flex; align-items:center; gap:7px; min-height:42px; padding:0 16px; border:1px solid var(--line); border-radius:12px; color:var(--ink); background:#fff; font-weight:800; }
.back-button:hover,.secondary-button:hover:not(:disabled) { background:#eaf4ff; }
.classroom-heading { min-width:0; }.classroom-heading p,.dialog-eyebrow,.module-kicker { margin:0; color:#5790c7; font-size:13px; font-weight:900; }
.classroom-heading h1 { max-width:720px; margin:2px 0 0; overflow:hidden; color:#0d4388; font-size:clamp(22px,2.1vw,31px); line-height:1.2; text-overflow:ellipsis; white-space:nowrap; }
.generation-status { display:inline-flex; align-items:center; gap:8px; margin-left:auto; padding:9px 13px; border:1px solid #cce5d4; border-radius:999px; color:#3b8c60; background:#f3fff7; font-size:13px; font-weight:800; white-space:nowrap; }.generation-status.loading{border-color:#c9def7;color:#3973b4;background:#f1f8ff}.generation-status.error{border-color:#f1d4b7;color:#a7662c;background:#fff8ef}.status-dot{width:8px;height:8px;border-radius:50%;background:currentColor}
.classroom-layout { display:grid; grid-template-columns:minmax(0,1fr) minmax(310px,360px); gap:16px; flex:1 1 auto; min-height:0; }.lesson-workspace{display:flex;flex-direction:column;gap:12px;min-width:0;min-height:0}.classroom-sidebar{display:flex;flex-direction:column;gap:12px;min-width:0;min-height:0}
.module-nav{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;flex:0 0 auto;padding:6px;border:1px solid var(--line);border-radius:14px;background:#fff}.module-tab{display:flex;align-items:center;gap:8px;min-width:0;min-height:54px;padding:8px 10px;border-radius:10px;color:var(--muted);text-align:left;background:transparent}.module-tab:hover{background:#f1f7fd}.module-tab.active{color:var(--ink);background:#eaf4ff}.module-number{display:grid;place-items:center;width:26px;height:26px;flex:0 0 auto;border-radius:50%;color:#4c83bc;background:#e7f1fb;font-size:11px;font-weight:900}.module-tab.active .module-number,.module-tab.done .module-number{color:#fff;background:var(--blue)}.module-tab-copy{min-width:0}.module-tab strong,.module-tab small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.module-tab strong{color:inherit;font-size:14px}.module-tab small{margin-top:3px;color:#8aa8c5;font-size:11px}
.module-panel,.dialog-panel{min-height:0;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.94);box-shadow:0 12px 28px rgba(38,93,150,.07)}.module-panel{display:flex;flex-direction:column;overflow:hidden}.module-panel-header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:24px 28px 18px;border-bottom:1px solid #e5eff8}.module-panel-header h2{margin:6px 0 0;color:#114b91;font-size:clamp(25px,3vw,38px);line-height:1.18}.module-subtitle{max-width:600px;margin:7px 0 0;color:var(--muted);font-size:15px}.module-panel-actions{display:flex;align-items:center;gap:8px;flex:0 0 auto}.narration-button{display:grid;place-items:center;width:38px;height:38px;flex:0 0 38px;padding:0;border:1px solid #c9e1f5;border-radius:50%;color:#2869ab;background:#fff;cursor:pointer}.narration-button:hover:not(:disabled){color:#fff;border-color:#2869ab;background:#2869ab}.narration-button:disabled{cursor:wait;opacity:.7}.spinning{animation:classroom-spin 1s linear infinite}.interaction-badge{flex:0 0 auto;padding:7px 11px;border:1px solid #c9e1f5;border-radius:999px;color:#3d78b8;background:#f0f8ff;font-size:12px;font-weight:900}@keyframes classroom-spin{to{transform:rotate(360deg)}}
.module-content{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(220px,.7fr);align-content:start;gap:14px;padding:22px 28px;overflow:auto}.content-block{min-width:0;padding:17px 18px;border:1px solid #e1edf7;border-radius:12px;background:#fbfdff}.speech-block{grid-row:span 2;min-height:170px;background:#f5faff}.content-label{display:block;margin-bottom:9px;color:#5b91c3;font-size:12px;font-weight:900}.speech-block p,.example-block p,.question-block>p{margin:0;color:#234e82;font-size:16px;line-height:1.85;overflow-wrap:anywhere}.points-block ul{display:grid;gap:9px;margin:0;padding:0;list-style:none}.points-block li{position:relative;padding-left:16px;color:#315e91;font-size:14px;line-height:1.55;overflow-wrap:anywhere}.points-block li:before{position:absolute;top:.65em;left:0;width:6px;height:6px;border-radius:50%;background:#4b93d5;content:''}.example-block{background:#fffaf0;border-color:#f1dfb8}.example-block .content-label{color:#b37a30}.example-block p{color:#805b2c;font-size:14px}.question-block{grid-column:1/-1;background:#fffaf0;border-color:#f1dfb8}.question-heading{display:flex;align-items:center;justify-content:space-between;color:#b37a30}.question-heading .content-label{margin:0;color:inherit}.question-block>p{margin-top:10px;color:#805b2c;font-weight:800}.question-options{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.question-options button{min-height:36px;padding:0 13px;border:1px solid #e6c979;border-radius:9px;color:#8d652d;background:#fff;font-size:13px}.question-options button:hover,.question-options button.selected{color:#fff;background:#b67b2c;border-color:#b67b2c}.question-hint{display:block;margin-top:12px;color:#aa8452;font-size:12px}
.resource-preview-card{background:#f7fbff;border-color:#cfe3f5}.resource-card-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.resource-card-head .content-label{display:inline-flex;align-items:center;gap:6px;margin-bottom:0}.resource-preview-card strong{display:block;margin-top:13px;color:#174b91;font-size:15px;line-height:1.45;overflow-wrap:anywhere}.resource-preview-card p{display:-webkit-box;margin:6px 0 0;overflow:hidden;color:#6383a4;font-size:13px;line-height:1.55;overflow-wrap:anywhere;-webkit-box-orient:vertical;-webkit-line-clamp:2}.resource-open-button{display:inline-flex;align-items:center;gap:5px;min-height:30px;padding:0 10px;border:1px solid #b9d7f0;border-radius:8px;color:#2160a8;background:#fff;font-size:12px;font-weight:900;cursor:pointer}.resource-open-button:hover:not(:disabled){border-color:#2160a8;color:#fff;background:#2160a8}.resource-open-button:disabled{cursor:wait;opacity:.65}
.resource-workbench{flex:0 0 auto;background:#f7fbff;border-color:#cfe3f5}.resource-card-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.resource-card-head .content-label{display:inline-flex;align-items:center;gap:6px;margin-bottom:0}.resource-count{color:#7b9bb9;font-size:12px;font-weight:800}.resource-workbench-intro{margin:10px 0 12px;color:#6383a4;font-size:12px;line-height:1.5}.resource-items{display:grid;gap:8px;max-height:260px;overflow:auto}.resource-item{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px;border:1px solid #dcebf6;border-radius:9px;background:#fff}.resource-item-copy{min-width:0}.resource-item-copy>span{display:block;color:#6c99be;font-size:11px;font-weight:900}.resource-item-copy strong{display:block;margin-top:3px;overflow:hidden;color:#174b91;font-size:13px;line-height:1.4;text-overflow:ellipsis;white-space:nowrap}.resource-item-copy p{display:-webkit-box;margin:3px 0 0;overflow:hidden;color:#7595b1;font-size:11px;line-height:1.4;-webkit-box-orient:vertical;-webkit-line-clamp:2}.resource-empty-state{padding:14px 10px;border:1px dashed #b9d7ee;border-radius:9px;color:#6f92b1;background:#fff;font-size:12px;line-height:1.5}.resource-generation-status{margin:10px 0 0;padding:8px 10px;border-radius:8px;color:#3973b4;background:#edf7ff;font-size:12px;line-height:1.45}.resource-generation-error{margin:10px 0 0;color:#a7662c;font-size:12px;line-height:1.45}.resource-generate-button{display:flex;align-items:center;justify-content:center;width:100%;min-height:36px;margin-top:12px;border:0;border-radius:9px;color:#fff;background:#2572d8;font-size:13px;font-weight:900;cursor:pointer}.resource-generate-button:hover:not(:disabled){background:#185bb5}.resource-generate-button:disabled{cursor:wait;opacity:.6}
.generation-note{margin:0;padding:10px 28px;border-bottom:1px solid #dbeaf7;color:#4e87bb;background:#f2f8ff;font-size:13px;font-weight:700}
.module-footer{display:flex;justify-content:flex-end;gap:10px;margin-top:auto;padding:14px 28px 20px;border-top:1px solid #e5eff8}.primary-button{min-height:42px;padding:0 18px;border-radius:10px;color:#fff;background:var(--blue);font-weight:900}.primary-button:hover{background:#174b96}.secondary-button:disabled{cursor:not-allowed;opacity:.45}
.dialog-panel{display:flex;flex:1 1 auto;flex-direction:column;overflow:hidden}.dialog-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:20px 18px 15px;border-bottom:1px solid #e5eff8}.dialog-header h2{margin:3px 0 0;color:#174b91;font-size:20px}.message-count{color:#7e9fbe;font-size:12px;font-weight:800}.dialog-messages{display:flex;flex-direction:column;gap:12px;flex:1 1 auto;min-height:0;padding:16px;overflow-y:auto;background:#f8fbfe}.dialog-empty{margin:auto 0;color:#8aa9c4;font-size:13px;text-align:center}.message{max-width:92%;padding:10px 12px;border:1px solid #dbeaf7;border-radius:11px;color:#275686;background:#fff;overflow-wrap:anywhere}.message.learner{align-self:flex-end;border-color:#5aaec1;color:#fff;background:#55aebb}.message-author{display:block;margin-bottom:5px;color:#5d91c0;font-size:11px;font-weight:900}.message.learner .message-author{color:rgba(255,255,255,.82)}.message p{margin:0;line-height:1.6}.message :deep(.markdown-body){font-size:13px;line-height:1.6}.message :deep(.markdown-body>:first-child){margin-top:0}.message :deep(.markdown-body>:last-child){margin-bottom:0}.message :deep(.markdown-body p){margin:0 0 6px}.message :deep(.markdown-body ul),.message :deep(.markdown-body ol){margin:4px 0;padding-left:17px}.message :deep(.markdown-body pre){max-width:100%;overflow:auto}.message :deep(.markdown-body a){color:#2f6fe4;text-decoration:underline}.dialog-input{display:flex;gap:8px;padding:12px;border-top:1px solid #e5eff8;background:#fff}.dialog-input input{min-width:0;flex:1;height:40px;padding:0 11px;border:1px solid #d5e5f3;border-radius:9px;outline:none;color:var(--ink);background:#f9fcff}.dialog-input input:focus{border-color:#67a3da;box-shadow:0 0 0 3px rgba(79,151,214,.12)}.dialog-input button{width:58px;height:40px;border-radius:9px;color:#fff;background:var(--blue);font-size:13px;font-weight:900}.dialog-input button:disabled{cursor:not-allowed;opacity:.5}
.resource-preview-overlay{position:fixed;inset:0;z-index:1500;display:grid;place-items:center;padding:18px;background:rgba(12,28,58,.32);backdrop-filter:blur(10px)}.resource-preview-panel{display:flex;flex-direction:column;width:min(1120px,100%);height:min(820px,calc(100vh - 36px));border:1px solid #c9deef;border-radius:16px;background:#fff;box-shadow:0 28px 80px rgba(22,63,143,.22);overflow:hidden}.resource-preview-panel header,.resource-preview-panel footer{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:15px 18px;border-bottom:1px solid #deebf5}.resource-preview-panel footer{justify-content:flex-end;border-top:1px solid #deebf5;border-bottom:0}.resource-preview-panel header span{color:#5f8fc3;font-size:12px;font-weight:900}.resource-preview-panel header h2{max-width:760px;margin:3px 0 0;overflow:hidden;color:#174b91;font-size:20px;line-height:1.3;text-overflow:ellipsis;white-space:nowrap}.resource-preview-panel header button{display:grid;place-items:center;width:36px;height:36px;border:1px solid #c9deef;border-radius:9px;color:#174b91;background:#f8fbfe;cursor:pointer}.resource-preview-panel footer button{display:inline-flex;align-items:center;gap:7px;min-height:36px;padding:0 14px;border:0;border-radius:9px;color:#fff;background:var(--blue);font:inherit;font-size:13px;font-weight:900;cursor:pointer}.resource-preview-body{position:relative;min-height:0;flex:1;padding:18px;overflow:auto;background:#fbfdff}.resource-preview-body--ppt{display:grid;padding:10px;overflow:hidden;grid-template-rows:minmax(0,1fr)}.resource-preview-body--mindmap{padding:10px;overflow:hidden}.resource-preview-body--mindmap :deep(.mindmap-preview){height:100%;min-height:0}.resource-preview-body--mindmap :deep(.mindmap-canvas){height:100%;min-height:0}.resource-preview-body img{display:block;max-width:100%;max-height:100%;margin:0 auto;object-fit:contain}.resource-preview-loading{display:grid;place-items:center;min-height:180px;color:#5f8fc3;font-weight:800}.resource-html-placeholder{display:grid;min-height:200px;place-items:center;align-content:center;gap:14px;color:#5f8fc3;text-align:center}.resource-html-placeholder strong{color:#174b91;font-size:18px}.resource-html-placeholder a{display:inline-flex;align-items:center;min-height:36px;padding:0 14px;border-radius:9px;color:#fff;background:var(--blue);font-weight:900;text-decoration:none}.resource-preview-body pre{margin:0;padding:16px;border-radius:10px;color:#174b91;background:#f1f8ff;white-space:pre-wrap;word-break:break-word;font:inherit;line-height:1.8}
.resource-preview-header-actions{display:flex;align-items:center;gap:8px;flex:0 0 auto}.resource-preview-panel header .resource-preview-download{display:inline-flex;align-items:center;justify-content:center;gap:6px;width:auto;min-height:36px;padding:0 10px;border:1px solid var(--blue);border-radius:9px;color:#fff;background:var(--blue);font:inherit;font-size:13px;font-weight:900}
@media(max-width:980px){.classroom-page{height:auto;min-height:calc(100vh - 64px);overflow:visible}.classroom-layout{grid-template-columns:1fr}.dialog-panel{min-height:390px}}
@media(max-width:680px){.classroom-page{gap:10px;padding:12px}.classroom-header{flex-wrap:wrap;gap:10px}.back-button span{display:none}.back-button{width:42px;justify-content:center;padding:0}.classroom-heading{flex:1 1 calc(100% - 60px)}.classroom-heading h1{font-size:22px}.generation-status{order:3;width:100%;justify-content:center;margin-left:0}.module-nav{grid-template-columns:repeat(4,minmax(78px,1fr));overflow-x:auto}.module-tab{min-height:48px;padding:7px}.module-tab-copy small{display:none}.module-panel-header{padding:18px 16px 14px}.module-panel-header h2{font-size:26px}.module-content{grid-template-columns:1fr;padding:14px 16px}.speech-block{grid-row:auto;min-height:0}.question-block{grid-column:auto}.module-footer{padding:12px 16px 16px}.secondary-button,.primary-button{flex:1;padding:0 10px;font-size:13px}.resource-items{max-height:none}.resource-item{align-items:flex-start;flex-direction:column}.resource-open-button{align-self:flex-end}.resource-preview-overlay{padding:10px}.resource-preview-panel{height:calc(100vh - 20px);border-radius:12px}.resource-preview-panel header,.resource-preview-panel footer{padding:12px}.resource-preview-panel header h2{max-width:250px;font-size:17px}.resource-preview-body{padding:12px}}
.lesson-summary{grid-column:1/-1;background:#f2f9ff;border-color:#cfe4f5}.summary-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;color:#6d91b6;font-size:12px;font-weight:800}.summary-heading .content-label{margin:0;color:#3978b4}.lesson-summary>p{margin:0;color:#245385;font-size:14px;line-height:1.7}.lesson-summary ul{display:grid;gap:6px;margin:10px 0 0;padding-left:18px;color:#315e91;font-size:13px;line-height:1.5}
.exercise-block{grid-column:1/-1;background:#fffaf0;border-color:#f1dfb8}.exercise-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;color:#a76f2b;font-size:12px;font-weight:800}.exercise-heading .content-label{margin:0;color:inherit}.exercise-card{max-width:760px;margin-top:2px}.exercise-stem{max-height:76px;margin:0;overflow:auto;color:#805b2c;font-size:16px;font-weight:800;line-height:1.65;overflow-wrap:anywhere}.exercise-options{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;max-height:142px;margin-top:13px;overflow:auto}.exercise-options button{display:flex;align-items:flex-start;gap:8px;min-width:0;min-height:42px;max-height:64px;padding:9px 10px;border:1px solid #e6c979;border-radius:9px;color:#805b2c;background:#fff;text-align:left;cursor:pointer}.exercise-options button:hover,.exercise-options button.selected{border-color:#b67b2c;color:#fff;background:#b67b2c}.exercise-options strong{flex:0 0 auto}.exercise-options span{min-width:0;overflow:hidden;line-height:1.4;text-overflow:ellipsis}.exercise-text-answer{display:block;width:100%;height:72px;margin-top:13px;padding:9px 10px;border:1px solid #e6c979;border-radius:9px;outline:none;resize:none;color:#805b2c;background:#fff;font:inherit;font-size:13px}.exercise-text-answer:focus{border-color:#b67b2c;box-shadow:0 0 0 3px rgba(182,123,44,.12)}.exercise-result{display:grid;gap:4px;margin-top:10px;padding:8px 10px;border-radius:8px;color:#43835d;background:#edf9f0;font-size:12px;line-height:1.45}.exercise-result.wrong{color:#a7662c;background:#fff1e5}.exercise-result p{margin:0;overflow-wrap:anywhere}.exercise-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:13px}.exercise-check-button,.exercise-open-button{min-height:34px;padding:0 12px;border-radius:8px;font-size:12px;font-weight:900;cursor:pointer}.exercise-check-button{border:1px solid #c9954d;color:#8c5f25;background:#fff}.exercise-open-button{border:0;color:#fff;background:#b67b2c}.exercise-check-button:disabled{cursor:not-allowed;opacity:.5}.exercise-open-button:hover{background:#925e1e}.exercise-state{display:grid;gap:9px;margin-top:5px;color:#a27643;font-size:13px;line-height:1.5}.exercise-state-error button{justify-self:start;min-height:32px;padding:0 11px;border:1px solid #d2a15b;border-radius:8px;color:#8c5f25;background:#fff;font:inherit;font-size:12px;font-weight:800;cursor:pointer}
.lesson-generation-state{display:grid;place-items:center;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.94);box-shadow:0 12px 28px rgba(38,93,150,.07)}.lesson-generation-state-inner{max-width:420px;padding:32px;text-align:center}.lesson-generation-state-inner strong{color:#174b91;font-size:18px}.lesson-generation-state-inner p{margin:10px 0 0;color:#7698b7;font-size:13px;line-height:1.7;overflow-wrap:anywhere}.classroom-waiting-panel{width:min(780px,calc(100% - 48px));padding:28px}.classroom-waiting-head h2{margin:8px 0 0;color:#174b91;font-size:25px;line-height:1.25}.classroom-waiting-head p{margin:8px 0 0;color:#6e90b1;font-size:14px;line-height:1.65}.waiting-kicker,.waiting-section-heading{display:inline-flex;align-items:center;gap:7px;color:#4b85ba;font-size:13px;font-weight:900}.waiting-progress{display:flex;align-items:center;gap:8px;margin:22px 0 20px}.waiting-progress i{width:8px;height:8px;border-radius:50%;background:#66a3d5;animation:classroom-wait-pulse 1.2s ease-in-out infinite}.waiting-progress i:nth-child(2){animation-delay:.18s}.waiting-progress i:nth-child(3){animation-delay:.36s}.waiting-progress span{height:2px;flex:1;background:#d7e8f6}@keyframes classroom-wait-pulse{50%{transform:scale(1.5);opacity:.35}}.classroom-waiting-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(220px,.65fr);gap:20px}.waiting-section{min-width:0}.waiting-section-heading{margin-bottom:11px}.waiting-news-list{display:grid;gap:9px}.waiting-news-item{display:block;padding:10px 0;border-top:1px solid #e4eff8;color:inherit;text-decoration:none}.waiting-news-item strong{display:block;overflow:hidden;color:#22558f;font-size:14px;line-height:1.45;text-overflow:ellipsis;white-space:nowrap}.waiting-news-item p{display:-webkit-box;margin:4px 0;overflow:hidden;color:#6d8dab;font-size:12px;line-height:1.5;-webkit-box-orient:vertical;-webkit-line-clamp:2}.waiting-news-item small{display:inline-flex;align-items:center;gap:4px;color:#6090bb;font-size:11px}.waiting-news-item:hover strong{color:#1d6fd0}.waiting-tip-section{padding-left:20px;border-left:1px solid #dcebf7}.waiting-tip-section p,.waiting-empty{margin:0;color:#426e9a;font-size:13px;line-height:1.7}.waiting-tip-topic{display:inline-block;max-width:100%;margin-top:14px;overflow:hidden;color:#5e90bb;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.waiting-skeletons{display:grid;gap:12px}.waiting-skeletons i{display:block;height:38px;border-radius:6px;background:#edf5fb;animation:classroom-skeleton 1.2s ease-in-out infinite}.waiting-skeletons i:nth-child(2){width:84%;animation-delay:.16s}.waiting-skeletons i:nth-child(3){width:68%;animation-delay:.32s}@keyframes classroom-skeleton{50%{opacity:.45}}
.classroom-waiting-panel{width:min(760px,calc(100% - 48px));padding:28px}.waiting-progress{gap:7px}.waiting-progress i{width:7px;height:7px;flex:0 0 auto;background:#c8def1;animation:none}.waiting-progress i.active{background:#3f85c8;transform:scale(1.22)}.waiting-slide{min-height:178px;padding:22px 24px;border:1px solid #dcebf7;border-radius:12px;background:#f8fcff}.waiting-slide h3{margin:8px 0 0;color:#1d508c;font-size:21px;line-height:1.35}.waiting-slide p{max-width:620px;margin:12px 0 0;color:#426e9a;font-size:15px;line-height:1.78;overflow-wrap:anywhere}.waiting-source-link{display:inline-flex;align-items:center;gap:6px;max-width:100%;margin-top:18px;overflow:hidden;color:#276cad;font-size:13px;font-weight:800;text-decoration:none;text-overflow:ellipsis;white-space:nowrap}.waiting-source-link:hover{text-decoration:underline}.waiting-slide-meta{display:inline-block;max-width:100%;margin-top:18px;overflow:hidden;color:#6c95bb;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.waiting-rotation-status{display:flex;justify-content:space-between;gap:12px;margin-top:12px;color:#7d9fbd;font-size:12px}.waiting-slide-enter-active,.waiting-slide-leave-active{transition:opacity .28s ease,transform .28s ease}.waiting-slide-enter-from,.waiting-slide-leave-to{opacity:0;transform:translateY(7px)}
.retry-generation-button{margin-top:18px;min-height:38px;padding:0 18px;border:0;border-radius:9px;background:#1f5da8;color:#fff;font:inherit;font-weight:700;cursor:pointer}.retry-generation-button:disabled{cursor:wait;opacity:.6}
@media(max-width:680px){.module-nav{grid-template-columns:repeat(4,minmax(78px,1fr))}.lesson-summary{grid-column:auto}.classroom-waiting-panel{width:calc(100% - 32px);padding:20px}.classroom-waiting-grid{grid-template-columns:1fr;gap:18px}.waiting-tip-section{padding-top:16px;padding-left:0;border-top:1px solid #dcebf7;border-left:0}}
@media(max-width:680px){.exercise-options{grid-template-columns:1fr;max-height:180px}.exercise-actions{flex-wrap:wrap}.exercise-check-button,.exercise-open-button{flex:1;min-width:120px}}
</style>
