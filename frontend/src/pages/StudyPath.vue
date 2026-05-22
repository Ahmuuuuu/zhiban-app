<template>
  <main class="study-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">Study Path</p>
        <h1>学习路径</h1>
        <p>跟着当前节点往前走，完成一步后路线会自动延伸出新的学习任务。</p>
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
            <template v-if="generating">生成中…</template>
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
                    <router-link class="quiz-action-btn" :to="`/question-bank/${nodeQuizData.id}?from=path`">
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
                  class="complete-btn"
                  type="button"
                  :disabled="selectedNode.status === 'done' || selectedNode.status === 'locked'"
                  @click="completeNode(selectedNode.id)"
                >
                  {{ selectedNode.status === 'done' ? '已完成' : selectedNode.status === 'locked' ? '未解锁' : '标记完成' }}
                </button>

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
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { AlertCircle, Check, LockKeyhole, Presentation, GitBranch, FileImage, FileText } from 'lucide-vue-next'
import {
  getCurrentLearningPath, completeLearningPathNode, generateLearningPath,
  generatePathNodeResources, generatePathNodeQuiz, downloadWithToken, resolveApiUrl
} from '../api/apis'
import { upsertQuizSet } from '../utils/quizBank'

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
  // 有可能路径整体包在 path / learning_path 字段下
  const path = raw.path || raw.learning_path || raw.learningPath || raw
  // 节点字段名可能有多种命名
  const nodes = path.nodes || path.node_list || path.nodeList || path.learning_nodes || path.learningNodes || []

  if (!Array.isArray(nodes)) {
    console.warn('[StudyPath] 未找到节点数组，后端返回结构：', { data, raw, path, nodes })
  }

  return {
    pathId: String(path.id || path.path_id || path.pathId || raw.id || raw.path_id || raw.pathId || ''),
    goal: path.goal || path.title || path.topic || '学习路径',
    stage: path.stage || path.status || '进行中',
    cursor: path.cursor ?? path.current_index ?? path.currentIndex ?? (Array.isArray(nodes) ? nodes.length : 0),
    diagnosis: {
      weakPoints: path.diagnosis?.weak_points || path.diagnosis?.weakPoints || path.diagnosis?.weak_point || [],
      latestScore: path.diagnosis?.latest_score ?? path.diagnosis?.latestScore ?? path.diagnosis?.score ?? 0,
      recommendation: path.diagnosis?.recommendation || path.diagnosis?.suggestion || ''
    },
    nodes: (Array.isArray(nodes) ? nodes : []).map(n => ({
      id: String(n.id || n.node_id || n.nodeId || ''),
      title: n.title || n.name || n.topic || '',
      type: n.type || n.node_type || n.nodeType || 'read',
      summary: n.summary || n.description || n.desc || n.intro || '',
      description: n.description || n.detail || n.content || n.summary || '',
      estimatedMinutes: n.estimated_minutes ?? n.estimatedMinutes ?? n.duration ?? n.estimated_time ?? 15,
      rule: n.rule || n.completion_rule || n.completionRule || n.condition || '',
      status: normalizeStatus(n.status || n.state),
      resources: (() => {
        const rawResources = n.resources || n.node_resources || n.learning_resources || n.learningResources || []
        return Array.isArray(rawResources) ? rawResources : []
      })(),
      quiz: n.quiz || n.node_quiz || null,
      quizId: n.quiz_id || n.quizId || null,
      sessionId: n.session_id || n.sessionId || ''
    }))
  }
}

const fetchCurrentPath = async () => {
  loading.value = true
  error.value = ''
  try {
    const result = await getCurrentLearningPath()
    console.log('[StudyPath] API 返回原始数据：', result)
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
    loading.value = false
  }
}

const generateNewPath = async () => {
  if (!topicInput.value.trim() || generating.value) return
  generating.value = true
  error.value = ''
  try {
    console.log('[StudyPath] 生成路径，发送数据：', { subject: topicInput.value.trim() })
    const result = await generateLearningPath({ subject: topicInput.value.trim() })
    console.log('[StudyPath] 生成路径返回：', result)
    pathState.value = normalizePath(result)
    savePathToCache(pathState.value)
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

const normalizeNodeResources = resources =>
  (Array.isArray(resources) ? resources : []).map((r, i) => {
    const fileType = r.file_type || r.fileType || r.resource_type || r.resourceType || r.type || 'file'
    return {
      id: r.id || r.resource_id || r.resourceId || r.file_id || r.fileId || `res-${i}`,
      title: r.title || r.filename || r.file_name || r.name || `学习资料 ${i + 1}`,
      filename: r.filename || r.file_name || r.name || '',
      type: fileType,
      fileType,
      typeLabel: fileTypeLabel(fileType),
      content: r.content || r.preview || r.text || '',
      previewUrl: resolveApiUrl(r.preview_url || r.previewUrl || r.preview || ''),
      downloadUrl: resolveApiUrl(r.download_url || r.downloadUrl || r.url || ''),
    }
  })

const openNode = async node => {
  selectedNode.value = node
  cardFlipped.value = false
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
    nodeResources.value = normalizeNodeResources(selectedNode.value.resources)
    nodeQuizData.value = selectedNode.value.quiz || null
    nodeSessionId.value = selectedNode.value.sessionId || ''
    showResources.value = true
    return
  }

  const pathId = pathState.value?.pathId
  if (!pathId) return

  resourcesLoading.value = true
  try {
    const res = await generatePathNodeResources(pathId, selectedNode.value.id)
    const data = res?.data?.data || res?.data || res || {}
    const items = data.resources || data.files || data.items || []
    nodeResources.value = normalizeNodeResources(items)

    try {
      const quizRes = await generatePathNodeQuiz(pathId, selectedNode.value.id)
      console.log('[StudyPath] generatePathNodeQuiz 原始响应：', quizRes)
      const quizData = quizRes?.data?.data || quizRes?.data || quizRes || {}
      nodeSessionId.value = quizData.session_id || quizData.sessionId || ''
      // 尝试多种可能的题目字段名
      const rawQuestions =
        quizData.questions ||
        quizData.question_list ||
        quizData.questionList ||
        quizData.items ||
        quizData.exam_questions ||
        []
      const questions = Array.isArray(rawQuestions) ? rawQuestions : []
      if (questions.length || quizData.content) {
        // 把整个响应作为 content 传给 upsertQuizSet，
        // 让 parseQuizQuestions 来自动规范化题目字段名（stem/options/answer/explanation）
        const quiz = upsertQuizSet({
          sourceId: `${pathId}-${selectedNode.value.id}`,
          title: `${selectedNode.value.title} - 巩固练习`,
          content: JSON.stringify(questions.length ? { questions } : quizData),
          fileType: 'exercise',
          sessionId: nodeSessionId.value
        })
        console.log('[StudyPath] upsertQuizSet 结果：', quiz)
        if (quiz) nodeQuizData.value = quiz
      } else {
        console.warn('[StudyPath] 后端未返回题目数据，quizData:', quizData)
      }
    } catch (err) {
      console.warn('[StudyPath] 生成练习题失败（可选步骤）：', err)
    }

    showResources.value = true
  } catch (err) {
    console.error('[StudyPath] 生成学习资源失败：', err)
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
    console.error('[StudyPath] 下载资源失败：', err)
    window.alert('下载失败，请确认登录状态和后端服务是否正常。')
  }
}

const previewNodeResource = resource => {
  if (resource.previewUrl) {
    window.open(resource.previewUrl, '_blank', 'noopener,noreferrer')
  }
}

const completeNode = async nodeId => {
  try {
    await completeLearningPathNode(nodeId, nodeSessionId.value)
    await fetchCurrentPath()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || '标记完成失败'
  }
}

const resetPath = () => {
  pathState.value = null
  selectedNode.value = null
  newestNodeId.value = ''
  showResources.value = false
  nodeResources.value = []
  nodeQuizData.value = null
  nodeSessionId.value = ''
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

/* ── Inline node resources (inside overlay) ── */

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

/* ── Loading skeleton ── */

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

/* ── Notice ── */

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

/* ── Empty / generate state ── */

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
