<template>
  <main class="study-panel">
    <header class="panel-header">
      <div class="header-title-row">
        <router-link class="home-pill" to="/">返回首页</router-link>
        <div>
        <p class="eyebrow">Study Path</p>
          <h1>学习路径</h1>
          <p>跟着当前节点往前走，完成一步后路线会自动延伸出新的学习任务。</p>
        </div>
      </div>

      <button v-if="pathState" class="reset-btn" type="button" @click="resetPath">
        重置路径
      </button>
    </header>

    <template v-if="loading">
      <section class="path-summary">
        <article v-for="i in 3" :key="i" class="skeleton-card">
          <span></span>
          <strong></strong>
        </article>
      </section>
      <section class="path-layout">
        <div class="path-track-skeleton" />
        <aside class="diagnosis-panel">
          <div class="skeleton-block" />
          <div class="skeleton-block" />
          <div class="skeleton-block" />
        </aside>
      </section>
    </template>

    <div v-else-if="error" class="notice">
      <AlertCircle :size="18" />
      <span>{{ error }}</span>
      <button class="retry-btn" type="button" @click="fetchCurrentPath">重试</button>
    </div>

    <template v-else-if="!pathState">
      <section class="empty-path">
        <h2>还没有学习路径</h2>
        <p>告诉我你想学什么，我来为你规划一条学习路径。</p>
        <form class="generate-form" @submit.prevent="generateNewPath">
          <input
            v-model="topicInput"
            class="topic-input"
            type="text"
            placeholder="例如：Python 入门、高考数学复习、雅思写作..."
            :disabled="generating"
          />
          <button class="generate-btn" type="submit" :disabled="!topicInput.trim() || generating">
            <template v-if="generating">生成中...</template>
            <template v-else>生成学习路径</template>
          </button>
        </form>
      </section>
    </template>

    <template v-else>
      <section class="path-summary">
        <article>
          <span>当前目标</span>
          <strong>{{ pathState.goal }}</strong>
        </article>
        <article>
          <span>学习阶段</span>
          <strong>{{ pathState.stage }}</strong>
        </article>
        <article>
          <span>下一步</span>
          <strong>{{ currentNode?.title || '等待生成' }}</strong>
        </article>
      </section>

      <section class="path-layout">
        <div class="path-track" :style="{ '--progress': `${progressPercent}%` }">
          <article
            v-for="(node, index) in visibleNodes"
            :key="node.id"
            class="path-node"
            :class="[`is-${node.status}`, { 'is-new': node.id === newestNodeId }]"
            @click="openNode(node)"
          >
            <div class="node-pin">
              <Check v-if="node.status === 'done'" :size="18" />
              <LockKeyhole v-else-if="node.status === 'locked'" :size="16" />
              <span v-else>{{ index + 1 }}</span>
            </div>

            <div class="node-card">
              <div class="node-card__top">
                <span>{{ statusLabel(node.status) }}</span>
                <small>{{ node.estimatedMinutes }} 分钟</small>
              </div>
              <h2>{{ node.title }}</h2>
              <p>{{ node.summary }}</p>
            </div>

            <div class="node-branches" @click.stop>
              <section class="node-branch">
                <div class="branch-line"></div>
                <article class="branch-card">
                  <div class="branch-head">
                    <FileText :size="16" />
                    <strong>学习资料</strong>
                  </div>

                  <div v-if="node._resLoading" class="branch-loading">加载中...</div>

                  <template v-else-if="node._resources?.length">
                    <button
                      v-for="resource in node._resources"
                      :key="resource.id"
                      class="branch-resource"
                      type="button"
                      @click="previewNodeResource(resource)"
                    >
                      <span class="branch-resource__icon">
                        <FileImage v-if="isImageResource(resource)" :size="15" />
                        <Presentation v-else-if="isPptResource(resource)" :size="15" />
                        <GitBranch v-else-if="isMindmapResource(resource)" :size="15" />
                        <FileText v-else :size="15" />
                      </span>
                      <span>{{ resource.title }}</span>
                    </button>
                  </template>

                  <button
                    v-else
                    class="branch-action"
                    type="button"
                    :disabled="node.status === 'locked'"
                    @click="ensureNodeResources(node, 'resources')"
                  >
                    生成资料
                  </button>

                  <div class="branch-divider"></div>

                  <div class="branch-head">
                    <Check :size="16" />
                    <strong>学习检测</strong>
                  </div>

                  <div v-if="node._quizLoading" class="branch-loading">加载中...</div>

                  <template v-else-if="node._quiz">
                    <div class="branch-quiz">
                      <span>{{ node._quiz.questionCount || 0 }} 道题</span>
                      <router-link class="branch-action primary" :to="`/question-bank/${node._quiz.id}?from=path&nodeId=${node.id}`">
                        开始检测
                      </router-link>
                    </div>
                  </template>

                  <button
                    v-else
                    class="branch-action"
                    type="button"
                    :disabled="node.status === 'locked'"
                    @click="ensureNodeResources(node, 'quiz')"
                  >
                    生成检测
                  </button>
                </article>
              </section>
            </div>
          </article>
        </div>

        <aside class="diagnosis-panel">
          <h2>轻量诊断</h2>
          <div class="diagnosis-block">
            <span>薄弱点</span>
            <strong>{{ pathState.diagnosis.weakPoints.join(' / ') }}</strong>
          </div>
          <div class="diagnosis-block">
            <span>最近成绩</span>
            <strong>{{ pathState.diagnosis.latestScore }} 分</strong>
          </div>
          <p>{{ pathState.diagnosis.recommendation }}</p>
        </aside>
      </section>
    </template>

    <Teleport to="body">
      <Transition name="overlay-fade">
        <section v-if="selectedNode" class="node-overlay" @click.self="closeNodeCard">
          <article class="flip-card" :class="{ flipped: cardFlipped }">
            <div class="flip-face flip-back">
              <span>{{ typeLabel(selectedNode.type) }}</span>
            </div>

            <div class="flip-face flip-front">
              <button class="close-card" type="button" aria-label="关闭任务卡" @click="closeNodeCard">&times;</button>
              <span class="task-type">{{ typeLabel(selectedNode.type) }}</span>
              <h2>{{ selectedNode.title }}</h2>
              <p>{{ selectedNode.description || selectedNode.summary }}</p>

              <dl>
                <div>
                  <dt>预计用时</dt>
                  <dd>{{ selectedNode.estimatedMinutes }} 分钟</dd>
                </div>
                <div>
                  <dt>完成条件</dt>
                  <dd>{{ selectedNode.rule }}</dd>
                </div>
              </dl>

              <div v-if="showResources" class="node-resources-section">
                <h3 class="resources-heading">学习资料</h3>

                <div v-if="resourcesLoading" class="resources-loading">
                  正在生成学习资料...
                </div>

                <template v-else-if="nodeResources.length > 0 || nodeQuizData">
                  <div
                    v-for="resource in nodeResources"
                    :key="resource.id"
                    class="resource-item"
                  >
                    <div class="file-head">
                      <span class="file-icon">
                        <FileImage v-if="isImageResource(resource)" :size="18" />
                        <Presentation v-else-if="isPptResource(resource)" :size="18" />
                        <GitBranch v-else-if="isMindmapResource(resource)" :size="18" />
                        <FileText v-else :size="18" />
                      </span>
                      <div class="file-title">
                        <strong>{{ resource.title }}</strong>
                        <span>{{ resource.typeLabel }}</span>
                      </div>
                    </div>

                    <div v-if="isImageResource(resource) && resource.previewUrl" class="file-image-preview">
                      <img
                        :src="resource.previewUrl"
                        :alt="resource.title"
                        loading="lazy"
                        @error="e => e.target.style.display = 'none'"
                      />
                    </div>

                    <div v-if="resource.previewUrl || resource.downloadUrl" class="file-actions">
                      <button v-if="resource.previewUrl" type="button" @click.stop="previewNodeResource(resource)">
                        预览
                      </button>
                      <button v-if="resource.downloadUrl" type="button" @click.stop="downloadNodeResource(resource)">
                        下载
                      </button>
                    </div>
                  </div>

                  <div v-if="nodeQuizData" class="resource-item quiz-item">
                    <div class="file-head">
                      <span class="file-icon check-icon">✓</span>
                      <div class="file-title">
                        <strong>{{ nodeQuizData.title || '巩固练习' }}</strong>
                        <span>{{ nodeQuizData.questionCount || 0 }} 道题</span>
                      </div>
                    </div>
                    <router-link class="quiz-action-btn" :to="`/question-bank/${nodeQuizData.id}?from=path&nodeId=${selectedNode.id}`">
                      开始练习
                    </router-link>
                  </div>
                </template>

                <div v-else class="resources-empty">
                  暂无学习资料
                </div>
              </div>

              <div class="card-actions">
                <button
                  class="start-btn"
                  type="button"
                  :disabled="selectedNode.status === 'locked' || resourcesLoading"
                  @click="loadNodeResources"
                >
                  <template v-if="resourcesLoading">生成中...</template>
                  <template v-else-if="showResources">收起资料</template>
                  <template v-else>开始学习</template>
                </button>
              </div>
            </div>
          </article>
        </section>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <section v-if="previewResource" class="resource-preview-overlay" @click.self="closeResourcePreview">
        <article class="resource-preview-panel">
          <header>
            <div>
              <span>{{ previewResource.typeLabel }}</span>
              <h2>{{ previewResource.title }}</h2>
            </div>
            <button type="button" aria-label="关闭预览" @click="closeResourcePreview">&times;</button>
          </header>

          <div class="resource-preview-body">
            <img
              v-if="isImageResource(previewResource) && previewResource.previewUrl"
              :src="previewResource.previewUrl"
              :alt="previewResource.title"
            />
            <MindmapPreview
              v-else-if="isMindmapResource(previewResource) && previewResource.content"
              :content="previewResource.content"
              :title="previewResource.title"
            />
            <pre v-else>{{ previewResource.content || '暂无可预览内容，可以下载原文件查看。' }}</pre>
          </div>

          <footer v-if="previewResource.downloadUrl">
            <button type="button" @click="downloadNodeResource(previewResource)">下载原文件</button>
          </footer>
        </article>
      </section>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { AlertCircle, Check, LockKeyhole, Presentation, GitBranch, FileImage, FileText } from 'lucide-vue-next'
import {
  getCurrentLearningPath, generateLearningPath,
  generatePathNodeResources, generatePathNodeQuiz, downloadWithToken, resolveApiUrl
} from '../api/apis'
import { upsertQuizSet, getQuizSet } from '../utils/quizBank'
import MindmapPreview from '../components/MindmapPreview.vue'

const PATH_CACHE_KEY = 'zhiban_path_state'

const savePathToCache = state => {
  try { localStorage.setItem(PATH_CACHE_KEY, JSON.stringify(state)) } catch { /* ignore */ }
}
const loadPathFromCache = () => {
  try { const raw = localStorage.getItem(PATH_CACHE_KEY); return raw ? JSON.parse(raw) : null } catch { return null }
}
const clearPathCache = () => { localStorage.removeItem(PATH_CACHE_KEY) }

const selectedNode = ref(null)
const cardFlipped = ref(false)
const newestNodeId = ref('')
const loading = ref(true)
const error = ref('')
const pathState = ref(null)
const topicInput = ref('')
const generating = ref(false)
const showResources = ref(false)
const nodeResources = ref([])
const resourcesLoading = ref(false)
const nodeQuizData = ref(null)
const nodeSessionId = ref('')
const previewResource = ref(null)

const normalizeStatus = s => {
  const map = {
    in_progress: 'current',
    'in-progress': 'current',
    active: 'current',
    completed: 'done',
    finish: 'done',
    finished: 'done',
    pending: 'locked',
    todo: 'locked',
    available: 'available',
    unlocked: 'available',
  }
  return map[s] || s || 'locked'
}

const normalizePath = data => {
  // 后端可能有多层包装
  const raw = data?.data || data || {}
  // 路径整体可能包在 path / learning_path 字段里
  const path = raw.path || raw.learning_path || raw.learningPath || raw
  // 节点字段名可能有多种命名
  const nodes = path.nodes || path.node_list || path.nodeList || path.learning_nodes || path.learningNodes || []
  const progressList = raw.progress || path.progress || []
  const progressMap = new Map(
    (Array.isArray(progressList) ? progressList : []).map(p => [
      String(p.node_id || p.nodeId || p.id || ''),
      p
    ])
  )
  const nodeResults = raw.node_results || raw.nodeResults || path.node_results || path.nodeResults || {}

  if (!Array.isArray(nodes)) {
    console.warn('[StudyPath] 未找到节点数组，后端返回结构：', { data, raw, path, nodes })
  }

  return {
    pathId: String(path.id || path.path_id || path.pathId || raw.id || raw.path_id || raw.pathId || ''),
    goal: path.goal || path.title || path.topic || path.subject || raw.subject || '学习路径',
    stage: path.stage || path.status || '进行中',
    cursor: path.cursor ?? path.current_index ?? path.currentIndex ?? (Array.isArray(nodes) ? nodes.length : 0),
    diagnosis: {
      weakPoints: (path.diagnosis?.weak_points || path.diagnosis?.weakPoints || path.diagnosis?.weak_point || [])
        .map(w => {
          if (typeof w === 'string') return w
          if (w && typeof w === 'object') return w.name || w.topic || w.title || w.tag || w.point || w.description || w.content || JSON.stringify(w)
          return String(w)
        })
        .filter(Boolean),
      latestScore: (() => {
        const score = path.diagnosis?.latest_score ?? path.diagnosis?.latestScore ?? path.diagnosis?.score
        if (score != null) return Number(score)
        // 如果后端没有返回总分数，就从 weak_points 的 accuracy 字段取平均值
        const points = path.diagnosis?.weak_points || path.diagnosis?.weakPoints || path.diagnosis?.weak_point || []
        const validScores = points.filter(w => w && typeof w === 'object' && typeof w.accuracy === 'number')
        if (validScores.length) {
          return Math.round((validScores.reduce((sum, w) => sum + w.accuracy, 0) / validScores.length) * 100)
        }
        return 0
      })(),
      recommendation: path.diagnosis?.recommendation || path.diagnosis?.suggestion || ''
    },
    nodes: (Array.isArray(nodes) ? nodes : []).map(n => {
      const nodeId = String(n.id || n.node_id || n.nodeId || '')
      const progress = progressMap.get(nodeId) || {}
      const nodeResult = nodeResults[nodeId] || nodeResults[Number(nodeId)] || {}
      const resourceTypes = n.resource_types || n.resourceTypes || []
      const resourceIds = n.resource_ids || n.resourceIds || nodeResult.resource_ids || nodeResult.resourceIds || []
      return {
      id: nodeId,
      title: n.title || n.name || n.topic || '',
      type: n.type || n.node_type || n.nodeType || 'read',
      summary: n.summary || n.description || n.desc || n.intro || '',
      description: n.description || n.detail || n.content || n.summary || '',
      estimatedMinutes: n.estimated_minutes ?? n.estimatedMinutes ?? n.duration ?? n.estimated_time ?? 15,
      rule: n.rule || n.completion_rule || n.completionRule || n.condition || '',
      status: normalizeStatus(n.status || n.state || progress.status || progress.node_status),
      resourceTypes: Array.isArray(resourceTypes) ? resourceTypes : [],
      resources: (() => {
        const rawResources = n.resources || n.node_resources || n.learning_resources || n.learningResources || []
        if (Array.isArray(rawResources) && rawResources.length) return rawResources
        return Array.isArray(resourceIds)
          ? resourceIds.map((id, index) => ({
            resource_id: id,
            resource_type: Array.isArray(resourceTypes) ? resourceTypes[index] || resourceTypes[0] : 'document',
            topic: n.title || n.name || n.topic || '',
            download_url: `/resource/${id}/download`
          }))
          : []
      })(),
      quiz: n.quiz || n.node_quiz || null,
      quizId: n.quiz_id || n.quizId || null,
      sessionId: n.session_id || n.sessionId || nodeResult.session_id || nodeResult.sessionId || progress.session_id || progress.sessionId || ''
    }
    })
  }
}

const fetchCurrentPath = async (options = {}) => {
  const silent = Boolean(options.silent)
  if (!silent) loading.value = true
  error.value = ''
  try {
    const result = await getCurrentLearningPath()
    console.log('[StudyPath] current path:', result)
    pathState.value = normalizePath(result)
    savePathToCache(pathState.value)
  } catch (err) {
    if (err?.response?.status === 404) {
      const cached = loadPathFromCache()
      if (cached) {
        pathState.value = cached
      } else {
        pathState.value = null
      }
    } else {
      const cached = loadPathFromCache()
      if (cached) {
        pathState.value = cached
        error.value = ''
      } else {
        error.value = err?.response?.data?.detail || err?.message || '加载学习路径失败，请稍后再试。'
      }
    }
  } finally {
    if (!silent) loading.value = false
  }
}

const generateNewPath = async () => {
  if (!topicInput.value.trim() || generating.value) return
  generating.value = true
  error.value = ''
  try {
    console.log('[StudyPath] generate path payload:', { subject: topicInput.value.trim() })
    const result = await generateLearningPath({ subject: topicInput.value.trim() })
    console.log('[StudyPath] generated path:', result)
    const generatedPath = normalizePath(result)
    pathState.value = generatedPath
    savePathToCache(generatedPath)
    topicInput.value = ''
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || '生成学习路径失败，请稍后再试。'
  } finally {
    generating.value = false
  }
}

const visibleNodes = computed(() => {
  const nodes = pathState.value?.nodes
  return nodes ? nodes.slice(-5) : []
})

const currentNode = computed(() => {
  return pathState.value?.nodes?.find(n => n.status === 'current')
})

const progressPercent = computed(() => {
  const nodes = pathState.value?.nodes
  if (!nodes?.length) return 0
  const total = Math.max(nodes.length - 1, 1)
  const doneCount = nodes.filter(n => n.status === 'done').length
  return Math.min(100, Math.round((doneCount / total) * 100))
})

const statusLabel = status => ({
  done: '已完成',
  current: '当前任务',
  available: '可开始',
  locked: '待解锁'
}[status] || '待开始')

const typeLabel = type => ({
  read: '资料阅读',
  quiz: '练习题',
  review: '错题复盘',
  summary: '学习总结',
  resource: '资源整理',
  chat: 'AI 辅导'
}[type] || '学习任务')

const fileTypeLabel = type => {
  const t = String(type || '').toLowerCase()
  if (t.includes('ppt')) return 'PPT 文件'
  if (t.includes('image')) return '图片'
  if (t.includes('mind')) return '思维导图'
  if (t.includes('txt') || t.includes('document')) return '学习文档'
  if (t.includes('pdf')) return 'PDF 文件'
  return '文件'
}

const isImageResource = r => String(r?.type || r?.fileType || '').toLowerCase().includes('image')

const isPptResource = r => String(r?.type || r?.fileType || r?.title || r?.filename || '').toLowerCase().includes('ppt')

const isMindmapResource = r => String(r?.type || r?.fileType || r?.title || r?.filename || '').toLowerCase().includes('mind')

const normalizeNodeResources = (resources, node = null) =>
  (Array.isArray(resources) ? resources : []).map((item, i) => {
    const r = typeof item === 'object' && item !== null ? item : { resource_id: item }
    const resourceId = r.id || r.resource_id || r.resourceId || r.file_id || r.fileId || ''
    const fallbackType = node?.resourceTypes?.[i] || node?.resourceTypes?.[0] || 'document'
    const fileType = r.file_type || r.fileType || r.resource_type || r.resourceType || r.type || fallbackType
    const title = r.title || r.topic || r.filename || r.file_name || r.name || node?.title || `学习资料 ${i + 1}`
    return {
      id: resourceId || `res-${i}`,
      title,
      filename: r.filename || r.file_name || r.name || `${title}_${fileType}`,
      type: fileType,
      fileType,
      typeLabel: fileTypeLabel(fileType),
      content: r.content || r.preview || r.text || '',
      previewUrl: resolveApiUrl(r.preview_url || r.previewUrl || r.preview || ''),
      downloadUrl: resolveApiUrl(r.download_url || r.downloadUrl || r.url || (resourceId ? `/resource/${resourceId}/download` : '')),
    }
  })

const getResponseData = res => res?.data?.data || res?.data || res || {}

const extractResourceItems = (data, node = null) => {
  const raw = getResponseData(data)
  const directItems =
    raw.resources ||
    raw.files ||
    raw.items ||
    raw.resource_list ||
    raw.resourceList ||
    raw.generated_resources ||
    raw.generatedResources ||
    []

  if (Array.isArray(directItems) && directItems.length) {
    return directItems
  }

  const ids = raw.resource_ids || raw.resourceIds || raw.ids || []
  return Array.isArray(ids)
    ? ids.map((id, index) => ({
      resource_id: id,
      resource_type: node?.resourceTypes?.[index] || node?.resourceTypes?.[0] || 'document',
      topic: node?.title || `学习资料 ${index + 1}`,
      download_url: `/resource/${id}/download`
    }))
    : []
}

const patchNodeState = (node, patch = {}) => {
  if (!node?.id || !pathState.value?.nodes) return

  Object.assign(node, patch)
  let updatedNode = null
  pathState.value = {
    ...pathState.value,
    nodes: pathState.value.nodes.map(item => {
      if (item.id !== node.id) return item
      updatedNode = { ...item, ...patch }
      return updatedNode
    })
  }

  if (updatedNode && selectedNode.value?.id === node.id) {
    selectedNode.value = updatedNode
  }

  savePathToCache(pathState.value)
}


const buildNodeQuiz = (node, quizData = null) => {
  const pathId = pathState.value?.pathId
  if (!pathId || !node?.id) return null

  let existingQuiz = getQuizSet(`quiz-resource-${pathId}-${node.id}`)
  if (existingQuiz?.questions?.[0]?.question && typeof existingQuiz.questions[0].question === 'object') {
    existingQuiz = null
  }
  if (existingQuiz) return existingQuiz

  const data = quizData || node.quiz
  if (!data) return null

  const rawQuestions =
    data.questions ||
    data.question_list ||
    data.questionList ||
    data.items ||
    data.exam_questions ||
    []
  const questions = Array.isArray(rawQuestions) ? rawQuestions.map(q => q.question || q) : []

  if (!questions.length && !data.content && !node.quiz) return null

  return upsertQuizSet({
    sourceId: `${pathId}-${node.id}`,
    title: `${node.title} - 巩固练习`,
    content: JSON.stringify(questions.length ? { questions } : data),
    fileType: 'exercise',
    sessionId: data.session_id || data.sessionId || node.sessionId || ''
  })
}

const ensureNodeResources = async (node, target = 'all') => {
  if (!node || node.status === 'locked') return

  // 优先使用后端预加载的资源
  if (!node._resources && node.resources?.length) {
    patchNodeState(node, { _resources: normalizeNodeResources(node.resources, node) })
  }

  const pathId = pathState.value?.pathId
  const shouldLoadResources = target === 'all' || target === 'resources'
  const shouldLoadQuiz = target === 'all' || target === 'quiz'

  if (shouldLoadResources && !node._resources?.length && pathId) {
    patchNodeState(node, { _resLoading: true })
    try {
      const res = await generatePathNodeResources(pathId, node.id)
      const resources = normalizeNodeResources(extractResourceItems(res, node), node)
      patchNodeState(node, {
        resources,
        _resources: resources,
        _resLoading: false,
        status: node.status === 'available' ? 'current' : node.status
      })
    } catch (err) {
      patchNodeState(node, { _resLoading: false })
      console.error('[StudyPath] generate node resources failed:', err)
      error.value = err?.response?.data?.detail || err?.message || '生成学习资料失败'
    }
  }

  if (shouldLoadQuiz && !node._quiz && pathId) {
    const localQuiz = buildNodeQuiz(node)
    if (localQuiz) {
      patchNodeState(node, { _quiz: localQuiz })
      return
    }

    patchNodeState(node, { _quizLoading: true })
    try {
      const quizRes = await generatePathNodeQuiz(pathId, node.id)
      const quizData = getResponseData(quizRes)
      const quiz = buildNodeQuiz(node, quizData)
      patchNodeState(node, {
        quiz: quizData,
        sessionId: quizData.session_id || quizData.sessionId || node.sessionId || '',
        _quiz: quiz,
        _quizLoading: false
      })
    } catch (err) {
      patchNodeState(node, { _quizLoading: false })
      console.error('[StudyPath] generate node quiz failed:', err)
      error.value = err?.response?.data?.detail || err?.message || '生成学习检测失败'
    }
  }
}

const openNode = async node => {
  selectedNode.value = node
  cardFlipped.value = false
  showResources.value = false
  nodeResources.value = normalizeNodeResources(node._resources?.length ? node._resources : node.resources, node)
  nodeQuizData.value = node._quiz || buildNodeQuiz(node)
  nodeSessionId.value = nodeQuizData.value?.sessionId || node.sessionId || ''
  await nextTick()
  window.requestAnimationFrame(() => {
    cardFlipped.value = true
  })
}

const closeNodeCard = () => {
  cardFlipped.value = false
  showResources.value = false
  window.setTimeout(() => {
    selectedNode.value = null
    nodeSessionId.value = ''
  }, 180)
}

const loadNodeResources = async () => {
  if (!selectedNode.value || selectedNode.value.status === 'locked') return

  if (showResources.value && !resourcesLoading.value) {
    showResources.value = false
    return
  }

  if (nodeResources.value.length > 0 || nodeQuizData.value) {
    showResources.value = true
    return
  }

  if (selectedNode.value.resources?.length > 0) {
    nodeResources.value = normalizeNodeResources(selectedNode.value.resources, selectedNode.value)
    patchNodeState(selectedNode.value, {
      resources: nodeResources.value,
      _resources: nodeResources.value
    })
    // 先查题库缓存，再用节点预载数据
    const pathId = pathState.value?.pathId
    const quizBankId = pathId ? `quiz-resource-${pathId}-${selectedNode.value.id}` : ''
    const existingQuiz = quizBankId ? getQuizSet(quizBankId) : null
    if (existingQuiz) {
      nodeQuizData.value = existingQuiz
      nodeSessionId.value = existingQuiz.sessionId || ''
      patchNodeState(selectedNode.value, { _quiz: existingQuiz })
    } else if (selectedNode.value.quiz) {
      const quiz = upsertQuizSet({
        sourceId: `${pathId}-${selectedNode.value.id}`,
        title: `${selectedNode.value.title} - 巩固练习`,
        content: JSON.stringify(selectedNode.value.quiz),
        fileType: 'exercise',
        sessionId: selectedNode.value.sessionId || ''
      })
      if (quiz) nodeQuizData.value = quiz
      nodeSessionId.value = selectedNode.value.sessionId || ''
      if (quiz) patchNodeState(selectedNode.value, { _quiz: quiz })
    }
    showResources.value = true
    return
  }

  const pathId = pathState.value?.pathId
  if (!pathId) return

  resourcesLoading.value = true
  try {
    const res = await generatePathNodeResources(pathId, selectedNode.value.id)
    nodeResources.value = normalizeNodeResources(extractResourceItems(res, selectedNode.value), selectedNode.value)
    patchNodeState(selectedNode.value, {
      resources: nodeResources.value,
      _resources: nodeResources.value,
      _resLoading: false,
      status: selectedNode.value.status === 'available' ? 'current' : selectedNode.value.status
    })

    // 查题库缓存 -> 节点预载 -> 调生成接口
    const quizBankId = `quiz-resource-${pathId}-${selectedNode.value.id}`
    const existingQuiz = getQuizSet(quizBankId)
    if (existingQuiz) {
      nodeQuizData.value = existingQuiz
      nodeSessionId.value = existingQuiz.sessionId || ''
      patchNodeState(selectedNode.value, { _quiz: existingQuiz })
      console.log('[StudyPath] 从题库加载已有题目：', existingQuiz)
    } else if (selectedNode.value.quiz) {
      const quiz = upsertQuizSet({
        sourceId: `${pathId}-${selectedNode.value.id}`,
        title: `${selectedNode.value.title} - 巩固练习`,
        content: JSON.stringify(selectedNode.value.quiz),
        fileType: 'exercise',
        sessionId: selectedNode.value.sessionId || ''
      })
      if (quiz) nodeQuizData.value = quiz
      nodeSessionId.value = selectedNode.value.sessionId || ''
      if (quiz) patchNodeState(selectedNode.value, { _quiz: quiz })
    } else {
      const quizRes = await generatePathNodeQuiz(pathId, selectedNode.value.id)
      console.log('[StudyPath] generatePathNodeQuiz response:', quizRes)
      const quizData = getResponseData(quizRes)
      nodeSessionId.value = quizData.session_id || quizData.sessionId || ''
      const rawQuestions =
        quizData.questions ||
        quizData.question_list ||
        quizData.questionList ||
        quizData.items ||
        quizData.exam_questions ||
        []
      const questions = Array.isArray(rawQuestions) ? rawQuestions : []
      if (questions.length || quizData.content) {
        const quiz = upsertQuizSet({
          sourceId: `${pathId}-${selectedNode.value.id}`,
          title: `${selectedNode.value.title} - 巩固练习`,
          content: JSON.stringify(questions.length ? { questions } : quizData),
          fileType: 'exercise',
          sessionId: nodeSessionId.value
        })
        console.log('[StudyPath] upsertQuizSet result:', quiz)
        if (quiz) {
          nodeQuizData.value = quiz
          patchNodeState(selectedNode.value, {
            quiz: quizData,
            sessionId: nodeSessionId.value,
            _quiz: quiz
          })
        }
      } else {
        console.warn('[StudyPath] 后端未返回题目数据，quizData:', quizData)
      }
    }

    showResources.value = true
  } catch (err) {
    console.error('[StudyPath] generate learning resources failed:', err)
    error.value = err?.response?.data?.detail || err?.message || '生成学习资料失败'
  } finally {
    resourcesLoading.value = false
  }
}

const downloadNodeResource = async resource => {
  if (!resource.downloadUrl) return
  try {
    await downloadWithToken(resource.downloadUrl, resource.filename || `${resource.title || 'resource'}.md`)
  } catch (err) {
    console.error('[StudyPath] download resource failed:', err)
    window.alert('下载失败，请确认登录状态和后端服务是否正常。')
  }
}

const previewNodeResource = resource => {
  previewResource.value = resource
}

const closeResourcePreview = () => {
  previewResource.value = null
}

const resetPath = () => {
  pathState.value = null
  selectedNode.value = null
  newestNodeId.value = ''
  showResources.value = false
  nodeResources.value = []
  nodeQuizData.value = null
  nodeSessionId.value = ''
  previewResource.value = null
  clearPathCache()
}

onMounted(fetchCurrentPath)
</script>

<style scoped>
.study-panel {
  height: 100%;
  min-height: 0;
  padding: 26px 34px 30px;
  color: #163f8f;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.header-title-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.home-pill {
  min-height: 40px;
  padding: 0 18px;
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

.reset-btn,
.generate-btn,
.retry-btn,
.start-btn,
.complete-btn {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid rgba(22, 63, 143, 0.18);
  border-radius: 18px;
  background: #ffffff;
  color: #163f8f;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.retry-btn {
  flex-shrink: 0;
  border-color: rgba(22, 63, 143, 0.3);
}

.path-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.path-summary article,
.diagnosis-panel,
.node-card {
  border: 1px solid rgba(22, 63, 143, 0.14);
  background: rgba(250, 250, 250, 0.78);
  box-shadow: 0 14px 34px rgba(22, 63, 143, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
}

.path-summary article {
  min-height: 82px;
  padding: 14px 16px;
  border-radius: 22px;
  display: grid;
  gap: 6px;
}

.path-summary span,
.diagnosis-block span,
.node-card__top,
.task-type {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.path-summary strong {
  min-width: 0;
  color: #163f8f;
  font-size: 17px;
  line-height: 1.35;
}

.path-layout {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 22px;
  overflow: hidden;
}

.path-track {
  --progress: 0%;
  position: relative;
  min-height: 0;
  padding: 8px 8px 20px 22px;
  overflow-y: auto;
}

.path-track::before,
.path-track::after {
  content: "";
  position: absolute;
  left: 37px;
  top: 32px;
  width: 3px;
  border-radius: 999px;
}

.path-track::before {
  bottom: 34px;
  background: rgba(201, 220, 233, 0.86);
}

.path-track::after {
  height: var(--progress);
  max-height: calc(100% - 64px);
  background: linear-gradient(to bottom, #163f8f, #5f8fc3);
  transition: height 520ms cubic-bezier(0.22, 1, 0.36, 1);
}

.path-node {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
  margin-bottom: 16px;
  cursor: pointer;
}

.path-node.is-new {
  animation: node-grow 620ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.node-pin {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid #c9dce9;
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  box-shadow: 0 10px 22px rgba(22, 63, 143, 0.12);
}

.is-done .node-pin {
  background: #163f8f;
  border-color: #163f8f;
  color: #ffffff;
}

.is-current .node-pin {
  border-color: #163f8f;
  box-shadow: 0 0 0 6px rgba(95, 143, 195, 0.16), 0 10px 22px rgba(22, 63, 143, 0.12);
}

.is-locked {
  opacity: 0.62;
}

.node-card {
  min-height: 126px;
  padding: 16px;
  border-radius: 22px;
  transition: transform 0.22s ease, border-color 0.22s ease, background 0.22s ease;
}

.path-node:hover .node-card,
.is-current .node-card {
  transform: translateY(-2px);
  border-color: rgba(95, 143, 195, 0.52);
  background: rgba(255, 255, 255, 0.88);
}

.node-card__top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.node-card h2 {
  margin: 10px 0 7px;
  color: #163f8f;
  font-size: 18px;
}

.node-card p,
.diagnosis-panel p {
  margin: 0;
  color: rgba(22, 63, 143, 0.68);
  line-height: 1.65;
  font-size: 13px;
}

.diagnosis-panel {
  min-height: 0;
  padding: 18px;
  border-radius: 24px;
  align-self: start;
  display: grid;
  gap: 14px;
}

.diagnosis-panel h2 {
  margin: 0;
  font-size: 20px;
}

.diagnosis-block {
  display: grid;
  gap: 5px;
}

.diagnosis-block strong {
  line-height: 1.4;
}

.node-overlay {
  position: fixed;
  inset: 0;
  z-index: 4200;
  display: grid;
  place-items: center;
  padding: 22px;
  background: rgba(12, 28, 58, 0.28);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  perspective: 1200px;
}

.flip-card {
  position: relative;
  width: min(430px, 100%);
  min-height: 430px;
  transform-style: preserve-3d;
  transform: rotateY(180deg) scale(0.96);
  transition: transform 520ms cubic-bezier(0.22, 1, 0.36, 1);
}

.flip-card.flipped {
  transform: rotateY(0deg) scale(1);
}

.flip-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 28px 80px rgba(22, 63, 143, 0.22);
}

.flip-back {
  transform: rotateY(180deg);
  display: grid;
  place-items: center;
  color: #163f8f;
  font-size: 28px;
  font-weight: 900;
}

.flip-front {
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.close-card {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 38px;
  height: 38px;
  border: 1px solid rgba(201, 220, 233, 0.9);
  border-radius: 16px;
  background: #fafafa;
  color: #163f8f;
  font-size: 24px;
  cursor: pointer;
}

.flip-front h2 {
  margin: 12px 0 0;
  color: #163f8f;
  font-size: 30px;
}

.flip-front p {
  margin: 0;
  color: rgba(22, 63, 143, 0.72);
  line-height: 1.8;
}

.flip-front dl {
  margin: 0;
  display: grid;
  gap: 10px;
}

.flip-front dl div {
  min-height: 48px;
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(237, 249, 252, 0.78);
}

.flip-front dt {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.flip-front dd {
  margin: 4px 0 0;
  color: #163f8f;
  font-weight: 800;
}

.card-actions {
  margin-top: auto;
  display: flex;
  gap: 10px;
}

.start-btn {
  flex: 1;
  background: #163f8f;
  color: #ffffff;
}

.complete-btn {
  flex: 1;
}

.start-btn:disabled,
.complete-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity 0.2s ease;
}

.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
}

@keyframes node-grow {
  from {
    opacity: 0;
    transform: translateY(-12px) scale(0.98);
  }
}

/* 鈹€鈹€ Node branches (inline resources + quiz) 鈹€鈹€ */

.node-branches {
  grid-column: 2;
  margin: -4px 0 4px;
}

.node-branch {
  position: relative;
  padding-top: 18px;
}

.branch-line {
  position: absolute;
  left: 24px;
  top: 0;
  width: 2px;
  height: 18px;
  background: rgba(95, 143, 195, 0.42);
}

.branch-card {
  min-height: 98px;
  padding: 12px;
  border: 1px solid rgba(201, 220, 233, 0.78);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 12px 28px rgba(22, 63, 143, 0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.branch-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #163f8f;
  font-size: 13px;
  font-weight: 900;
}

.branch-resource {
  width: 100%;
  min-height: 34px;
  padding: 6px 8px;
  border: 1px solid rgba(22, 63, 143, 0.12);
  border-radius: 12px;
  background: rgba(237, 249, 252, 0.68);
  color: #163f8f;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.branch-resource span:last-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.branch-resource__icon {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: #c9dce9;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.branch-action {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 999px;
  background: #ffffff;
  color: #163f8f;
  text-decoration: none;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  align-self: flex-start;
}

.branch-action.primary {
  border-color: #163f8f;
  background: #163f8f;
  color: #ffffff;
}

.branch-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.branch-loading {
  min-height: 34px;
  display: flex;
  align-items: center;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.branch-quiz {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: rgba(22, 63, 143, 0.72);
  font-size: 12px;
  font-weight: 900;
}

.branch-divider {
  height: 1px;
  margin: 4px 0;
  background: rgba(201, 220, 233, 0.6);
}

/* 鈹€鈹€ Resource preview overlay 鈹€鈹€ */

.resource-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 4300;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(12, 28, 58, 0.32);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.resource-preview-panel {
  width: min(880px, 100%);
  max-height: min(760px, 90vh);
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 28px 80px rgba(22, 63, 143, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.resource-preview-panel header,
.resource-preview-panel footer {
  padding: 18px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border-bottom: 1px solid rgba(201, 220, 233, 0.7);
}

.resource-preview-panel footer {
  justify-content: flex-end;
  border-top: 1px solid rgba(201, 220, 233, 0.7);
  border-bottom: none;
}

.resource-preview-panel header span {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.resource-preview-panel header h2 {
  margin: 4px 0 0;
  color: #163f8f;
  font-size: 24px;
}

.resource-preview-panel header button {
  width: 38px;
  height: 38px;
  border: 1px solid rgba(201, 220, 233, 0.9);
  border-radius: 14px;
  background: #fafafa;
  color: #163f8f;
  font-size: 24px;
  cursor: pointer;
}

.resource-preview-panel footer button {
  min-height: 36px;
  padding: 0 16px;
  border: none;
  border-radius: 999px;
  background: #163f8f;
  color: #ffffff;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.resource-preview-body {
  min-height: 0;
  padding: 18px;
  overflow: auto;
}

.resource-preview-body img {
  display: block;
  max-width: 100%;
  max-height: 620px;
  margin: 0 auto;
  object-fit: contain;
  border-radius: 18px;
}

.resource-preview-body pre {
  margin: 0;
  padding: 16px;
  border-radius: 18px;
  background: rgba(237, 249, 252, 0.68);
  color: #163f8f;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  font-family: inherit;
}

/* 鈹€鈹€ Inline node resources (inside overlay) 鈹€鈹€ */

.node-resources-section {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.resources-heading {
  margin: 0;
  color: #5f8fc3;
  font-size: 13px;
  font-weight: 900;
}

.resources-loading {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #5f8fc3;
  font-size: 13px;
  font-weight: 800;
}

.resource-item {
  padding: 12px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 16px;
  background: rgba(237, 249, 252, 0.48);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-item .file-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.resource-item .file-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #c9dce9;
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.resource-item .check-icon {
  background: #163f8f;
  color: #fff;
  font-size: 16px;
  font-weight: 900;
}

.resource-item .file-title {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.resource-item .file-title strong {
  color: #163f8f;
  font-size: 14px;
  line-height: 1.3;
  word-break: break-word;
}

.resource-item .file-title span {
  color: rgba(22, 63, 143, 0.62);
  font-size: 11px;
}

.resource-item .file-actions {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}

.resource-item .file-actions button {
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(22, 63, 143, 0.18);
  border-radius: 999px;
  background: #ffffff;
  color: #163f8f;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.resource-item .file-actions button:hover {
  background: #c9dce9;
}

.file-image-preview {
  max-height: 120px;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(237, 249, 252, 0.6);
}

.file-image-preview img {
  max-width: 100%;
  max-height: 120px;
  object-fit: contain;
  border-radius: 6px;
}

.resources-empty {
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(22, 63, 143, 0.48);
  font-size: 13px;
  font-weight: 800;
}

.quiz-item {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.quiz-action-btn {
  min-height: 30px;
  padding: 0 14px;
  border: none;
  border-radius: 999px;
  background: #163f8f;
  color: #ffffff;
  text-decoration: none;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  cursor: pointer;
}

.quiz-action-btn:hover {
  background: #1a4da8;
}

/* 鈹€鈹€ Loading skeleton 鈹€鈹€ */

.skeleton-card,
.skeleton-block {
  background: linear-gradient(90deg, #c9dce9, #fafafa, #c9dce9);
  background-size: 220% 100%;
  animation: shimmer 1.3s ease-in-out infinite;
}

.skeleton-card span {
  display: block;
  width: 50px;
  height: 14px;
  border-radius: 8px;
  background: rgba(201, 220, 233, 0.5);
}

.skeleton-card strong {
  display: block;
  width: 70%;
  height: 22px;
  border-radius: 8px;
  background: rgba(201, 220, 233, 0.5);
}

.path-track-skeleton {
  border-radius: 24px;
  background: rgba(250, 250, 250, 0.48);
  border: 1px solid rgba(22, 63, 143, 0.08);
}

.skeleton-block {
  height: 58px;
  border-radius: 16px;
}

@keyframes shimmer {
  to {
    background-position: -220% 0;
  }
}

/* 鈹€鈹€ Notice 鈹€鈹€ */

.notice {
  min-height: 48px;
  padding: 0 16px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 18px;
  background: #c9dce9;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 鈹€鈹€ Empty / generate state 鈹€鈹€ */

.empty-path {
  min-height: 260px;
  padding: 36px 32px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 24px;
  background: rgba(250, 250, 250, 0.78);
  box-shadow: 0 14px 34px rgba(22, 63, 143, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 14px;
}

.empty-path h2 {
  margin: 0;
  font-size: 24px;
}

.empty-path p {
  margin: 0;
  color: rgba(22, 63, 143, 0.68);
  font-size: 15px;
}

.generate-form {
  display: flex;
  gap: 10px;
  width: 100%;
  max-width: 520px;
}

.topic-input {
  flex: 1;
  min-height: 48px;
  padding: 0 18px;
  border: 1px solid rgba(22, 63, 143, 0.18);
  border-radius: 18px;
  background: #ffffff;
  color: #163f8f;
  font: inherit;
  font-size: 15px;
  outline: none;
}

.topic-input::placeholder {
  color: rgba(95, 143, 195, 0.6);
}

.topic-input:focus {
  border-color: #5f8fc3;
}

.generate-btn {
  min-height: 48px;
  padding: 0 22px;
  border: none;
  border-radius: 18px;
  background: #163f8f;
  color: #ffffff;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
}

.generate-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 980px) {
  .study-panel {
    height: auto;
    min-height: 100%;
    overflow: visible;
  }

  .path-summary,
  .path-layout {
    grid-template-columns: 1fr;
  }

  .path-track {
    overflow: visible;
  }
}

@media (max-width: 640px) {
  .study-panel {
    padding: 20px;
  }

  .panel-header {
    flex-direction: column;
  }

  .generate-form {
    flex-direction: column;
  }

  .flip-card {
    min-height: 460px;
  }
}
</style>


