<template>
  <main class="study-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">Study Path</p>
        <h1>学习路径</h1>
        <p>跟着当前节点往前走，完成一步后路线会自动延伸出新的学习任务。</p>
      </div>

      <button class="reset-btn" type="button" @click="resetPath">
        重置路径
      </button>
    </header>

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

    <Teleport to="body">
      <Transition name="overlay-fade">
        <section v-if="selectedNode" class="node-overlay" @click.self="closeNodeCard">
          <article class="flip-card" :class="{ flipped: cardFlipped }">
            <div class="flip-face flip-back">
              <span>{{ typeLabel(selectedNode.type) }}</span>
            </div>

            <div class="flip-face flip-front">
              <button class="close-card" type="button" aria-label="关闭任务卡" @click="closeNodeCard">×</button>
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
                  :disabled="selectedNode.status === 'locked'"
                  @click="startNode(selectedNode)"
                >
                  开始学习
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
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Check, LockKeyhole } from 'lucide-vue-next'

const STORAGE_KEY = 'zhiban_dynamic_learning_path'

const router = useRouter()
const selectedNode = ref(null)
const cardFlipped = ref(false)
const newestNodeId = ref('')

const nodeLibrary = [
  {
    id: 'understand',
    title: '基础理解',
    type: 'read',
    summary: '先用一份资料把核心概念过一遍。',
    description: '阅读最近保存的学习资料，抓住主题、关键定义和容易混淆的概念。',
    estimatedMinutes: 12,
    rule: '完成一次资料阅读',
    route: '/mine/resources'
  },
  {
    id: 'organize',
    title: '整理资料',
    type: 'resource',
    summary: '把知识点整理成一份可回看的资源。',
    description: '用资源中心或 AI 对话整理成文档、PPT 或思维导图，形成复习抓手。',
    estimatedMinutes: 15,
    rule: '保存 1 个学习资源',
    route: '/chat'
  },
  {
    id: 'practice',
    title: '基础练习',
    type: 'quiz',
    summary: '完成一组基础题，检查理解是否稳。',
    description: '先做一套基础练习题，目标不是速度，而是确认每个概念都能用起来。',
    estimatedMinutes: 18,
    rule: '完成一套题并提交成绩',
    route: '/question-bank'
  },
  {
    id: 'review',
    title: '错题复盘',
    type: 'review',
    summary: '复盘错误原因，补掉薄弱点。',
    description: '对最近练习里的错题进行归因：概念不清、公式不熟，还是审题遗漏。',
    estimatedMinutes: 10,
    rule: '复盘 2 个薄弱点',
    route: '/mine/situation'
  },
  {
    id: 'advance',
    title: '综合提升',
    type: 'quiz',
    summary: '进入综合题，验证能否迁移应用。',
    description: '完成综合练习，把资料阅读、基础题和错题复盘串起来。',
    estimatedMinutes: 20,
    rule: '综合练习达到 80 分',
    route: '/question-bank'
  },
  {
    id: 'summary',
    title: '学习总结',
    type: 'summary',
    summary: '总结本轮学习成果，沉淀下一轮目标。',
    description: '写下本轮掌握的内容、仍不确定的问题，以及下一次学习要优先处理的点。',
    estimatedMinutes: 8,
    rule: '完成一次学习总结',
    route: '/chat'
  }
]

const makeInitialPath = () => ({
  goal: '本周学习巩固',
  stage: '进行中',
  cursor: 3,
  diagnosis: {
    weakPoints: ['概念迁移', '错题复盘'],
    latestScore: 72,
    recommendation: '先完成当前基础练习，再让路线自动进入错题复盘。'
  },
  nodes: nodeLibrary.slice(0, 4).map((node, index) => ({
    ...node,
    status: index === 0 ? 'done' : index === 1 ? 'current' : 'locked'
  }))
})

const readState = () => {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '')
    if (parsed?.nodes?.length) return parsed
  } catch {
    // Fall through to seed state.
  }
  return makeInitialPath()
}

const pathState = ref(readState())

const persist = () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(pathState.value))
}

const visibleNodes = computed(() => pathState.value.nodes.slice(-5))
const currentNode = computed(() => pathState.value.nodes.find(node => node.status === 'current'))
const progressPercent = computed(() => {
  const total = Math.max(pathState.value.nodes.length - 1, 1)
  const doneCount = pathState.value.nodes.filter(node => node.status === 'done').length
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
  window.setTimeout(() => {
    selectedNode.value = null
  }, 180)
}

const appendNextNode = () => {
  const nextTemplate = nodeLibrary[pathState.value.cursor]
  if (!nextTemplate) return

  const nextNode = {
    ...nextTemplate,
    id: `${nextTemplate.id}-${Date.now()}`,
    status: 'locked'
  }
  pathState.value.nodes.push(nextNode)
  pathState.value.cursor += 1
  newestNodeId.value = nextNode.id
  window.setTimeout(() => {
    newestNodeId.value = ''
  }, 900)
}

const completeNode = nodeId => {
  const nodes = pathState.value.nodes
  const index = nodes.findIndex(node => node.id === nodeId)
  if (index === -1 || nodes[index].status === 'locked') return

  nodes[index].status = 'done'
  const next = nodes.slice(index + 1).find(node => node.status !== 'done')
  if (next) {
    next.status = 'current'
  }
  appendNextNode()
  pathState.value.stage = next?.title ? `正在${next.title}` : '收尾中'
  persist()

  if (selectedNode.value?.id === nodeId) {
    selectedNode.value = nodes[index]
  }
}

const startNode = node => {
  if (node.status === 'locked') return
  router.push(node.route || '/chat')
}

const resetPath = () => {
  pathState.value = makeInitialPath()
  newestNodeId.value = ''
  selectedNode.value = null
  persist()
}
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

  .flip-card {
    min-height: 460px;
  }
}
</style>
