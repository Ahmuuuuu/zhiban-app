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
                    <div
                      v-for="resource in node._resources"
                      :key="resource.id"
                      class="branch-resource-row"
                    >
                      <button
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
                      <button
                        v-if="canPreviewResource(resource)"
                        class="branch-mini-action"
                        type="button"
                        @click="previewNodeResource(resource)"
                      >
                        预览
                      </button>
                    </div>
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
                      <router-link class="branch-action primary" :to="pathQuizLink(node._quiz, node)">
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

                    <div v-if="canPreviewResource(resource) || resource.downloadUrl" class="file-actions">
                      <button v-if="canPreviewResource(resource)" type="button" @click.stop="previewNodeResource(resource)">
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
                    <router-link class="quiz-action-btn" :to="pathQuizLink(nodeQuizData, selectedNode)">
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
            <div class="resource-preview-tools">
              <button
                v-if="canNarrateResource(previewResource)"
                class="resource-preview-icon-btn"
                type="button"
                :title="isNarrationPlaying(previewResource) ? '暂停朗读' : '朗读资源'"
                :disabled="isNarrationLoading(previewResource)"
                @click="toggleNarration(previewResource)"
              >
                <PauseCircle v-if="isNarrationPlaying(previewResource)" :size="17" />
                <Volume2 v-else :size="17" />
              </button>
              <button type="button" aria-label="关闭预览" @click="closeResourcePreview">&times;</button>
            </div>
          </header>

          <div class="resource-preview-body">
            <div v-if="previewLoading" class="resources-loading">
              正在加载预览...
            </div>
            <img
              v-else-if="isImageResource(previewResource) && previewResource.previewUrl"
              :src="previewResource.previewUrl"
              :alt="previewResource.title"
            />
            <PptPreview
              v-else-if="isPptResource(previewResource) && previewResource.slides?.length"
              :slides="previewResource.slides"
              :title="previewResource.title"
            />
            <MindmapPreview
              v-else-if="isMindmapResource(previewResource) && previewResource.content"
              :content="previewResource.content"
              :title="previewResource.title"
            />
            <article
              v-else-if="previewResource.content"
              class="resource-markdown markdown-body"
              v-html="renderMarkdown(previewResource.content)"
            ></article>
            <pre v-else>{{ previewResource.content || '暂无可预览内容，可以下载原文件查看。' }}</pre>
          </div>

          <footer v-if="previewResource.downloadUrl">
            <button v-if="previewResource.downloadUrl" type="button" @click="downloadNodeResource(previewResource)">下载原文件</button>
          </footer>
        </article>
      </section>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { AlertCircle, Check, LockKeyhole, Presentation, GitBranch, FileImage, FileText, PauseCircle, Volume2 } from 'lucide-vue-next'
import {
  getCurrentLearningPath, generateLearningPath,
  generatePathNodeResources, generatePathNodeQuiz, downloadWithToken, getGeneratedResource, resolveApiUrl
} from '../api/apis'
import { upsertQuizSet, getQuizSet } from '../utils/quizBank'
import MindmapPreview from '../components/MindmapPreview.vue'
import PptPreview from '../components/PptPreview.vue'
import { useResourceNarration } from '../composables/useResourceNarration'

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
const generationRunId = ref(0)
const showResources = ref(false)
const nodeResources = ref([])
const resourcesLoading = ref(false)
const nodeQuizData = ref(null)
const nodeSessionId = ref('')
const previewResource = ref(null)
const previewLoading = ref(false)
const {
  canNarrateResource,
  toggleNarration,
  isNarrationLoading,
  isNarrationPlaying,
  stopCurrentAudio
} = useResourceNarration()

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
    open: 'available',
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
    setPathState(normalizePath(result))
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
  const subject = topicInput.value.trim()
  const runId = generationRunId.value + 1
  generationRunId.value = runId
  generating.value = true
  error.value = ''

  const generatePromise = generateLearningPath({ subject })
    .then(result => ({ type: 'generated', result }))
    .catch(err => ({ type: 'error', err }))

  const currentPromise = waitForGeneratedPath(runId, subject)

  try {
    console.log('[StudyPath] generate path payload:', { subject })
    const firstResult = await Promise.race([generatePromise, currentPromise])
    if (runId !== generationRunId.value) return

    if (firstResult?.type === 'current') {
      topicInput.value = ''
      generatePromise.then(done => {
        if (runId !== generationRunId.value || done?.type !== 'generated') return
        const generatedPath = normalizePath(done.result)
        if (generatedPath?.nodes?.length) setPathState(generatedPath)
      })
      return
    }

    if (firstResult?.type === 'generated') {
      console.log('[StudyPath] generated path:', firstResult.result)
      const generatedPath = normalizePath(firstResult.result)
      if (generatedPath?.nodes?.length) {
        setPathState(generatedPath)
      } else {
        await recoverGeneratedPathFromCurrent()
      }
      topicInput.value = ''
      refreshGeneratedPathInBackground()
      return
    }

    throw firstResult?.err || new Error('生成学习路径失败')
  } catch (err) {
    const recovered = await recoverGeneratedPathFromCurrent()
    if (recovered) {
      topicInput.value = ''
      return
    }

    error.value = err?.response?.data?.detail || err?.message || '生成学习路径失败，请稍后再试。'
  } finally {
    if (runId === generationRunId.value) generating.value = false
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

const pathQuizLink = (quiz, node) => {
  const query = new URLSearchParams({
    from: 'path',
    nodeId: String(node?.id || '')
  })
  const sessionId = quiz?.sessionId || quiz?.session_id || node?.sessionId || node?.session_id || ''
  if (sessionId) query.set('sessionId', String(sessionId))
  return `/question-bank/${quiz?.id}?${query.toString()}`
}

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

const isPptResource = r => /ppt|powerpoint|presentation|slide/.test(String(r?.type || r?.fileType || r?.title || r?.filename || '').toLowerCase())

const isMindmapResource = r => String(r?.type || r?.fileType || r?.title || r?.filename || '').toLowerCase().includes('mind')

const canPreviewResource = resource => {
  return Boolean(resource?.previewUrl || resource?.content || resource?.id || resource?.downloadUrl)
}

const escapeHtml = value => {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const isImageResourceUrl = url => /\.(png|jpe?g|webp|gif|bmp|svg)(?:[?#].*)?$/i.test(String(url || ''))

const parsePptSlidesFromContent = content => {
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
        notes: slide.notes || slide.speaker_notes || ''
      }))
    }
  } catch {
    // fall through to plain-text parsing
  }

  const blocks = text
    .replace(/^```(?:json|markdown|md)?\s*/i, '')
    .replace(/```$/i, '')
    .split(/\n\s*---+\s*\n|(?=\n\s*#{1,3}\s+)/)
    .map(block => block.trim())
    .filter(Boolean)

  return blocks.map((block, index) => {
    const lines = block.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
    const titleLine = lines.find(line => /^#{1,3}\s+/.test(line)) || lines[0] || `第 ${index + 1} 页`
    const title = titleLine.replace(/^#{1,3}\s+/, '').replace(/^第?\s*\d+\s*[页章、.：:-]?\s*/, '').trim()
    const body = lines
      .filter(line => line !== titleLine)
      .map(line => line.replace(/^[-*•]\s+/, '').trim())
      .filter(Boolean)
      .join('\n')

    return {
      index,
      title: title || `第 ${index + 1} 页`,
      text: body,
      notes: ''
    }
  }).filter(slide => slide.title || slide.text)
}

const renderInlineMarkdown = value => {
  let text = escapeHtml(value)

  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  text = text.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
  text = text.replace(/_([^_\n]+)_/g, '<em>$1</em>')
  text = text.replace(/!\[([^\]]*)\]\(((?:https?:\/\/|\/)[^\s)]+)\)/g, (_, label, url) => {
    const href = escapeHtml(resolveApiUrl(url))
    return `<a class="md-image-link" href="${href}" target="_blank" rel="noopener noreferrer"><img class="md-generated-image" src="${href}" alt="${label}" loading="lazy" /></a>`
  })
  text = text.replace(/\[([^\]]+)\]\(((?:https?:\/\/|mailto:|\/)[^\s)]+)\)/g, (_, label, url) => {
    const href = escapeHtml(resolveApiUrl(url))

    if (!/^mailto:/i.test(url) && isImageResourceUrl(url)) {
      return `<a class="md-image-link" href="${href}" target="_blank" rel="noopener noreferrer"><img class="md-generated-image" src="${href}" alt="${label}" loading="lazy" /></a>`
    }

    return `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`
  })

  return text
}

const isTableSeparator = line => /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line)

const renderTable = tableLines => {
  const rows = tableLines.map(line => {
    return line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map(cell => renderInlineMarkdown(cell.trim()))
  })

  const header = rows[0] || []
  const body = rows.slice(2)

  return `
    <div class="md-table-wrap">
      <table>
        <thead><tr>${header.map(cell => `<th>${cell}</th>`).join('')}</tr></thead>
        <tbody>${body.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>
      </table>
    </div>
  `
}

const renderMarkdown = content => {
  const text = String(content || '').trim()
  if (!text) return ''

  const lines = text.split(/\r?\n/)
  const html = []
  let paragraph = []
  let listItems = []
  let listType = ''
  let codeLines = []
  let inCodeBlock = false
  let codeLanguage = ''

  const flushParagraph = () => {
    if (!paragraph.length) return
    html.push(`<p>${paragraph.map(renderInlineMarkdown).join('<br>')}</p>`)
    paragraph = []
  }

  const flushList = () => {
    if (!listItems.length) return
    const tag = listType === 'ol' ? 'ol' : 'ul'
    html.push(`<${tag}>${listItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</${tag}>`)
    listItems = []
    listType = ''
  }

  const flushCode = () => {
    const languageLabel = codeLanguage ? `<span>${escapeHtml(codeLanguage)}</span>` : ''
    html.push(`<div class="md-code-block">${languageLabel}<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre></div>`)
    codeLines = []
    codeLanguage = ''
  }

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index]
    const line = rawLine.trim()

    if (line.startsWith('```')) {
      if (inCodeBlock) {
        flushCode()
        inCodeBlock = false
      } else {
        flushParagraph()
        flushList()
        inCodeBlock = true
        codeLanguage = line.replace(/^```/, '').trim()
      }
      continue
    }

    if (inCodeBlock) {
      codeLines.push(rawLine)
      continue
    }

    if (!line) {
      flushParagraph()
      flushList()
      continue
    }

    if (line.includes('|') && lines[index + 1] && isTableSeparator(lines[index + 1])) {
      flushParagraph()
      flushList()
      const tableLines = [rawLine, lines[index + 1]]
      index += 2
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        tableLines.push(lines[index])
        index += 1
      }
      index -= 1
      html.push(renderTable(tableLines))
      continue
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      const level = Math.min(headingMatch[1].length + 2, 6)
      html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`)
      continue
    }

    const blockquoteMatch = line.match(/^>\s?(.+)$/)
    if (blockquoteMatch) {
      flushParagraph()
      flushList()
      html.push(`<blockquote>${renderInlineMarkdown(blockquoteMatch[1])}</blockquote>`)
      continue
    }

    const orderedMatch = line.match(/^\d+\.\s+(.+)$/)
    const unorderedMatch = line.match(/^[-*]\s+(.+)$/)

    if (orderedMatch || unorderedMatch) {
      flushParagraph()
      const currentType = orderedMatch ? 'ol' : 'ul'

      if (listType && listType !== currentType) {
        flushList()
      }

      listType = currentType
      listItems.push((orderedMatch?.[1] || unorderedMatch?.[1] || '').trim())
      continue
    }

    flushList()
    paragraph.push(rawLine)
  }

  if (inCodeBlock) flushCode()
  flushParagraph()
  flushList()

  return html.join('')
}

const normalizeNodeResources = (resources, node = null) =>
  (Array.isArray(resources) ? resources : []).map((item, i) => {
    const r = typeof item === 'object' && item !== null ? item : { resource_id: item }
    const resourceId = r.id || r.resource_id || r.resourceId || r.file_id || r.fileId || ''
    const fallbackType = node?.resourceTypes?.[i] || node?.resourceTypes?.[0] || 'document'
    const fileType = r.file_type || r.fileType || r.resource_type || r.resourceType || r.type || fallbackType
    const title = r.title || r.topic || r.filename || r.file_name || r.name || node?.title || `学习资料 ${i + 1}`
    return {
      id: resourceId || `res-${i}`,
      resourceId,
      title,
      filename: r.filename || r.file_name || r.name || `${title}_${fileType}`,
      type: fileType,
      fileType,
      typeLabel: fileTypeLabel(fileType),
      content: r.content || r.preview || r.text || '',
      slides: Array.isArray(r.slides) ? r.slides : [],
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

const hashText = value => {
  const text = String(value || '')
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0
  }
  return Math.abs(hash).toString(36)
}

const getNodeQuizSourceId = (node, data = null) => {
  const pathId = pathState.value?.pathId
  const raw = data || node?.quiz || {}
  const backendId =
    raw.resource_id ||
    raw.resourceId ||
    raw.quiz_id ||
    raw.quizId ||
    raw.exam_id ||
    raw.examId ||
    raw.session_id ||
    raw.sessionId ||
    node?.quizId ||
    node?.sessionId ||
    ''
  const fallbackFingerprint = hashText(`${node?.title || ''}:${JSON.stringify(raw)}`)
  return backendId
    ? `${pathId}-${node.id}-${backendId}`
    : `${pathId}-${node.id}-${fallbackFingerprint}`
}

const getNodeQuizSet = (node, data = null) => {
  const sourceId = getNodeQuizSourceId(node, data)
  return sourceId ? getQuizSet(`quiz-resource-${sourceId}`) : null
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

const hydratePathForRender = state => {
  if (!state) return null

  let hasCurrentNode = state.nodes?.some(node => node.status === 'current')
  let promotedCurrent = false

  return {
    ...state,
    diagnosis: {
      weakPoints: [],
      latestScore: 0,
      recommendation: '',
      ...(state.diagnosis || {})
    },
    nodes: (state.nodes || []).map((node, index) => {
      const resources = node._resources?.length
        ? node._resources
        : normalizeNodeResources(node.resources || [], node)
      const shouldPromote =
        !hasCurrentNode &&
        !promotedCurrent &&
        (node.status === 'available' || node.status === 'unlocked' || (index === 0 && node.status !== 'locked'))

      if (shouldPromote) {
        promotedCurrent = true
        hasCurrentNode = true
      }

      return {
        ...node,
        status: shouldPromote ? 'current' : node.status,
        resources,
        _resources: resources
      }
    })
  }
}

const setPathState = state => {
  const hydrated = hydratePathForRender(state)
  pathState.value = hydrated
  if (hydrated) savePathToCache(hydrated)
}

const delay = ms => new Promise(resolve => window.setTimeout(resolve, ms))

const recoverGeneratedPathFromCurrent = async () => {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      if (attempt > 0) await delay(900)
      const result = await getCurrentLearningPath()
      const recovered = normalizePath(result)
      if (recovered?.nodes?.length) {
        setPathState(recovered)
        error.value = ''
        return true
      }
    } catch (currentErr) {
      console.warn('[StudyPath] recover current path failed:', currentErr)
    }
  }

  return false
}

const waitForGeneratedPath = async (runId, subject) => {
  for (let attempt = 0; attempt < 90; attempt += 1) {
    if (runId !== generationRunId.value) return { type: 'stale' }

    try {
      if (attempt > 0) await delay(1000)
      const result = await getCurrentLearningPath()
      const currentPath = normalizePath(result)
      const matchesSubject =
        !subject ||
        currentPath.goal?.includes(subject) ||
        currentPath.nodes?.some(node => node.title?.includes(subject) || node.summary?.includes(subject))

      if (currentPath?.nodes?.length && matchesSubject) {
        setPathState(currentPath)
        error.value = ''
        return { type: 'current', result: currentPath }
      }
    } catch (err) {
      console.warn('[StudyPath] wait current path failed:', err)
    }
  }

  return { type: 'timeout' }
}

const refreshGeneratedPathInBackground = async () => {
  try {
    await delay(1200)
    const result = await getCurrentLearningPath()
    const refreshed = normalizePath(result)
    if (refreshed?.nodes?.length) {
      setPathState(refreshed)
    }
  } catch (err) {
    console.warn('[StudyPath] background refresh path failed:', err)
  }
}


const buildNodeQuiz = (node, quizData = null) => {
  const pathId = pathState.value?.pathId
  if (!pathId || !node?.id) return null

  const data = quizData || node.quiz
  if (!data) return null

  let existingQuiz = getNodeQuizSet(node, data)
  if (existingQuiz?.questions?.[0]?.question && typeof existingQuiz.questions[0].question === 'object') {
    existingQuiz = null
  }
  if (existingQuiz) return existingQuiz

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
    sourceId: getNodeQuizSourceId(node, data),
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
    const existingQuiz = pathId ? getNodeQuizSet(selectedNode.value) : null
    if (existingQuiz) {
      nodeQuizData.value = existingQuiz
      nodeSessionId.value = existingQuiz.sessionId || ''
      patchNodeState(selectedNode.value, { _quiz: existingQuiz })
    } else if (selectedNode.value.quiz) {
      const quiz = upsertQuizSet({
        sourceId: getNodeQuizSourceId(selectedNode.value),
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
    const existingQuiz = getNodeQuizSet(selectedNode.value)
    if (existingQuiz) {
      nodeQuizData.value = existingQuiz
      nodeSessionId.value = existingQuiz.sessionId || ''
      patchNodeState(selectedNode.value, { _quiz: existingQuiz })
      console.log('[StudyPath] 从题库加载已有题目：', existingQuiz)
    } else if (selectedNode.value.quiz) {
      const quiz = upsertQuizSet({
        sourceId: getNodeQuizSourceId(selectedNode.value),
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
          sourceId: getNodeQuizSourceId(selectedNode.value, quizData),
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

const getResourceIdFromUrl = url => {
  const match = String(url || '').match(/\/resource\/([^/?#]+)(?:\/download)?/i)
  return match?.[1] || ''
}

const mergePreviewResource = (resource, detail) => {
  const data = getResponseData(detail)
  const resourceId = data.resource_id || data.resourceId || data.id || resource.resourceId || resource.id || ''
  const fileType = data.file_type || data.fileType || data.resource_type || data.resourceType || resource.fileType || resource.type
  const title = data.title || data.topic || data.filename || data.name || resource.title

  const content = data.content || data.preview || data.text || resource.content || ''
  const slides = Array.isArray(data.slides) && data.slides.length
    ? data.slides
    : (isPptResource({ ...resource, type: fileType, fileType, title, filename: data.filename || data.file_name || resource.filename || title })
      ? parsePptSlidesFromContent(content)
      : resource.slides || [])

  return {
    ...resource,
    id: resourceId || resource.id,
    resourceId: resourceId || resource.resourceId,
    title,
    filename: data.filename || data.file_name || resource.filename || title,
    type: fileType,
    fileType,
    typeLabel: fileTypeLabel(fileType),
    content,
    slides,
    narration: data.narration || resource.narration || null,
    previewUrl: resolveApiUrl(data.preview_url || data.previewUrl || data.url || resource.previewUrl || ''),
    downloadUrl: resolveApiUrl(data.download_url || data.downloadUrl || resource.downloadUrl || (resourceId ? `/resource/${resourceId}/download` : ''))
  }
}

const updateResourceInNodes = resource => {
  if (!resource?.id || !pathState.value?.nodes) return

  pathState.value = {
    ...pathState.value,
    nodes: pathState.value.nodes.map(node => ({
      ...node,
      resources: (node.resources || []).map(item => String(item.id || item.resourceId) === String(resource.id) ? resource : item),
      _resources: (node._resources || []).map(item => String(item.id || item.resourceId) === String(resource.id) ? resource : item)
    }))
  }

  if (selectedNode.value) {
    const updatedNode = pathState.value.nodes.find(node => node.id === selectedNode.value.id)
    if (updatedNode) selectedNode.value = updatedNode
  }

  nodeResources.value = nodeResources.value.map(item => String(item.id || item.resourceId) === String(resource.id) ? resource : item)
  savePathToCache(pathState.value)
}

const previewNodeResource = async resource => {
  previewResource.value = resource
  previewLoading.value = false

  const resourceId = resource.resourceId || resource.id || getResourceIdFromUrl(resource.downloadUrl)
  if (!resourceId || resource.slides?.length || (!isPptResource(resource) && (resource.content || resource.previewUrl))) return

  previewLoading.value = true
  try {
    const detail = await getGeneratedResource(resourceId)
    const merged = mergePreviewResource(resource, detail)
    previewResource.value = merged
    updateResourceInNodes(merged)
  } catch (err) {
    console.error('[StudyPath] load resource preview failed:', err)
    previewResource.value = {
      ...resource,
      content: '预览加载失败，可以先下载原文件查看。'
    }
  } finally {
    previewLoading.value = false
  }
}

const closeResourcePreview = () => {
  stopCurrentAudio()
  previewResource.value = null
  previewLoading.value = false
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

const mountStudyPath = async () => {
  await fetchCurrentPath()
  if (window.sessionStorage.getItem('zhiban_path_needs_refresh') === '1') {
    window.sessionStorage.removeItem('zhiban_path_needs_refresh')
    await delay(600)
    await fetchCurrentPath({ silent: true })
  }
}

onMounted(mountStudyPath)
onBeforeUnmount(stopCurrentAudio)
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

.branch-resource-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px;
  align-items: center;
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

.branch-mini-action {
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 999px;
  background: #ffffff;
  color: #163f8f;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
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

.resource-preview-tools {
  display: flex;
  align-items: center;
  gap: 8px;
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

.ppt-preview {
  display: grid;
  gap: 14px;
}

.ppt-slide {
  min-height: 430px;
  padding: 28px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(237, 249, 252, 0.78), rgba(255, 255, 255, 0.96) 42%),
    #ffffff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.ppt-slide__meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.ppt-slide h3 {
  margin: 0;
  color: #163f8f;
  font-size: 30px;
  line-height: 1.25;
}

.ppt-slide__content {
  color: rgba(22, 63, 143, 0.78);
  font-size: 16px;
}

.ppt-slide__notes {
  margin-top: auto;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(201, 220, 233, 0.24);
  color: rgba(22, 63, 143, 0.72);
}

.ppt-slide__notes span {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.ppt-slide__notes p {
  margin: 5px 0 0;
  line-height: 1.65;
}

.ppt-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ppt-controls > button {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 999px;
  background: #fff;
  color: #163f8f;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.resource-preview-panel header .resource-preview-icon-btn {
  font-size: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.resource-preview-panel header .resource-preview-icon-btn:disabled {
  opacity: 0.56;
  cursor: wait;
}

.ppt-controls > button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ppt-dots {
  min-width: 0;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
}

.ppt-dots button {
  width: 9px;
  height: 9px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(95, 143, 195, 0.32);
  cursor: pointer;
}

.ppt-dots button.active {
  background: #163f8f;
}

.resource-markdown {
  color: #163f8f;
  line-height: 1.8;
  font-size: 14px;
}

.markdown-body :deep(p) {
  margin: 0;
}

.markdown-body :deep(p + p),
.markdown-body :deep(p + ul),
.markdown-body :deep(p + ol),
.markdown-body :deep(ul + p),
.markdown-body :deep(ol + p),
.markdown-body :deep(.md-table-wrap + p),
.markdown-body :deep(.md-code-block + p) {
  margin-top: 12px;
}

.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 16px 0 8px;
  padding-left: 10px;
  border-left: 3px solid #5f8fc3;
  color: #163f8f;
  line-height: 1.45;
}

.markdown-body :deep(h3:first-child),
.markdown-body :deep(h4:first-child),
.markdown-body :deep(h5:first-child),
.markdown-body :deep(h6:first-child) {
  margin-top: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 10px 0 0;
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin: 5px 0;
}

.markdown-body :deep(blockquote) {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-left: 3px solid #5f8fc3;
  border-radius: 8px;
  background: rgba(237, 249, 252, 0.68);
}

.markdown-body :deep(code) {
  padding: 2px 5px;
  border-radius: 5px;
  background: rgba(237, 249, 252, 0.85);
  color: #163f8f;
  font-family: Consolas, "SFMono-Regular", monospace;
  font-size: 0.92em;
}

.markdown-body :deep(.md-code-block) {
  margin-top: 12px;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 12px;
  background: rgba(237, 249, 252, 0.58);
  overflow: hidden;
}

.markdown-body :deep(.md-code-block span) {
  display: block;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(201, 220, 233, 0.72);
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.markdown-body :deep(.md-code-block pre) {
  margin: 0;
  padding: 14px;
  background: transparent;
  white-space: pre-wrap;
}

.markdown-body :deep(a) {
  color: #163f8f;
  font-weight: 900;
}

.markdown-body :deep(.md-generated-image) {
  display: block;
  width: min(100%, 420px);
  max-height: 320px;
  object-fit: contain;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 14px;
  background: #fff;
}

.markdown-body :deep(.md-table-wrap) {
  margin-top: 12px;
  overflow-x: auto;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 10px;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  background: rgba(255, 255, 255, 0.56);
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 9px 11px;
  border-bottom: 1px solid rgba(201, 220, 233, 0.56);
  border-right: 1px solid rgba(201, 220, 233, 0.56);
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  background: rgba(237, 249, 252, 0.78);
  font-weight: 900;
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


