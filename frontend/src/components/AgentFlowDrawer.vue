<template>
  <Teleport to="body">
    <Transition name="agent-flow-slide">
      <aside v-if="open && task" class="agent-flow-drawer">
        <header class="agent-flow-drawer__header">
          <div>
            <span>智能体工作流</span>
            <strong>{{ taskTitle }}</strong>
          </div>
          <button type="button" aria-label="关闭智能体工作流" @click="$emit('close')">×</button>
        </header>

        <section v-if="flowOptions.length > 1" class="agent-flow-switcher">
          <div class="agent-flow-section-title">
            本聊天流程
            <small>{{ flowOptions.length }} 条</small>
          </div>
          <div class="agent-flow-switcher__list">
            <button
              v-for="option in flowOptions"
              :key="option.id"
              type="button"
              :class="{ active: option.id === activeTaskId }"
              @click="$emit('select-task', option.id)"
            >
              <span :class="`is-${option.status}`"></span>
              <strong>{{ option.label }}</strong>
              <small>{{ option.meta }}</small>
            </button>
          </div>
        </section>

        <section class="agent-flow-drawer__stage">
          <div
            v-for="(node, index) in primaryNodes"
            :key="node.id"
            class="agent-flow-node-wrap"
          >
            <div
              class="agent-flow-node"
              :class="[`is-${node.status}`, { 'is-active': isActive(node.status) }]"
            >
              <span class="agent-flow-node__pulse"></span>
              <span class="agent-flow-node__icon">{{ statusIcon(node.status) }}</span>
              <div>
                <strong>{{ node.label }}</strong>
                <small>{{ node.message }}</small>
              </div>
            </div>
            <span
              v-if="index < primaryNodes.length - 1"
              class="agent-flow-link"
              :class="{ 'is-lit': isLinkLit(index) }"
            ></span>
          </div>
        </section>

        <section v-if="branchNodes.length" class="agent-flow-branches">
          <div class="agent-flow-section-title">
            {{ parallelTitle }}
            <small v-if="hasParallelBranches">同时调度</small>
          </div>
          <div v-if="hasParallelBranches" class="agent-flow-parallel-hub">
            <span>Executor</span>
            <i></i>
          </div>
          <div class="agent-flow-branch-grid">
            <article
              v-for="node in branchNodes"
              :key="node.id"
              class="agent-flow-branch"
              :class="[`is-${node.status}`, { 'is-active': isActive(node.status) }]"
            >
              <span>{{ statusIcon(node.status) }}</span>
              <div>
                <strong>{{ node.label }}</strong>
                <small>{{ node.message }}</small>
                <div v-if="node.progressText" class="agent-flow-branch__progress">{{ node.progressText }}</div>
                <div v-if="node.children.length" class="agent-flow-branch__children">
                  <span
                    v-for="child in node.children"
                    :key="child.id"
                    :class="`is-${child.status}`"
                    :title="child.message"
                  >
                    {{ child.label }}
                  </span>
                  <em v-if="node.hiddenChildren">+{{ node.hiddenChildren }}</em>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section class="agent-flow-log">
          <div class="agent-flow-section-title">实时动态</div>
          <div v-if="recentEvents.length" class="agent-flow-log__list">
            <p v-for="event in recentEvents" :key="event.key">
              <span :class="`is-${event.status}`"></span>
              <strong>{{ event.agent_name || event.agentName || event.agent_id }}</strong>
              <em>{{ event.message || statusText(event.status) }}</em>
            </p>
          </div>
          <div v-else class="agent-flow-log__empty">正在连接智能体流程...</div>
        </section>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  open: Boolean,
  task: {
    type: Object,
    default: null
  },
  tasks: {
    type: Array,
    default: () => []
  },
  selectedTaskId: {
    type: String,
    default: ''
  }
})

defineEmits(['close', 'select-task'])

const phaseLabels = {
  leader: '需求规划',
  executor: '并行生成',
  reviewer: '质量审核',
  saver: '保存资源',
  complete: '完成'
}

const resourceLabels = {
  ppt: 'PPT生成智能体',
  document: '文档生成智能体',
  mindmap: '思维导图智能体',
  exercise: '习题生成智能体',
  image: '图片生成智能体',
  video: '视频生成智能体',
  case: '案例资料智能体',
  reading: '阅读材料智能体'
}

const activeStatuses = new Set(['running', 'reviewing', 'retrying', 'saving'])

const flow = computed(() => props.task?.agentFlow || {})
const nodes = computed(() => flow.value.nodes || {})
const events = computed(() => Array.isArray(flow.value.events) ? flow.value.events : [])
const activeTaskId = computed(() => props.selectedTaskId || props.task?.id || '')
const terminalStatus = computed(() => {
  const taskStatus = normalizeStatus(props.task?.status)
  if (taskStatus === 'done' || taskStatus === 'failed') return taskStatus
  const completeStatus = normalizeStatus(nodes.value.complete?.status)
  return completeStatus === 'done' || completeStatus === 'failed' ? completeStatus : ''
})

const taskTitle = computed(() => {
  const text = props.task?.text || props.task?.tool?.label || '学习资源'
  return String(text).replace(/^帮我生成一份\s*/u, '').slice(0, 26)
})

const taskLabel = task => {
  const text = task?.text || task?.tool?.label || '学习资源'
  return String(text)
    .replace(/^帮我生成一份\s*/u, '')
    .replace(/^帮我生成\s*/u, '')
    .slice(0, 18) || '学习资源'
}

const taskMeta = task => {
  if (task?.tool?.generateMode === 'video') return '视频'
  const types = Array.isArray(task?.tool?.resourceTypes) ? task.tool.resourceTypes : []
  if (types.length) return types.map(type => resourceTypeShortName(type)).join(' / ')
  return statusText(task?.status)
}

const resourceTypeShortName = type => {
  const value = String(type || '').toLowerCase()
  const labels = {
    ppt: 'PPT',
    document: '文档',
    mindmap: '导图',
    exercise: '习题',
    image: '图片',
    video: '视频',
    case: '案例',
    reading: '阅读'
  }
  return labels[value] || value || '资源'
}

const flowOptions = computed(() => {
  const source = props.tasks?.length ? props.tasks : (props.task ? [props.task] : [])
  const seen = new Set()
  return source
    .filter(task => task?.id && !seen.has(task.id) && seen.add(task.id))
    .map((task, index) => ({
      id: task.id,
      label: taskLabel(task) || `流程 ${index + 1}`,
      meta: taskMeta(task),
      status: normalizeStatus(task.status)
    }))
})

const normalizeStatus = status => {
  const value = String(status || 'pending').toLowerCase()
  if (['running', 'reviewing', 'retrying', 'saving', 'done', 'failed'].includes(value)) return value
  return 'pending'
}

const statusIcon = status => {
  const value = normalizeStatus(status)
  if (value === 'done') return '✓'
  if (value === 'failed') return '!'
  if (value === 'retrying') return '↻'
  if (value === 'reviewing') return '审'
  if (value === 'saving') return '存'
  if (value === 'running') return '●'
  return '○'
}

const statusText = status => {
  const value = normalizeStatus(status)
  if (value === 'done') return '已完成'
  if (value === 'failed') return '失败'
  if (value === 'retrying') return '修订中'
  if (value === 'reviewing') return '审核中'
  if (value === 'saving') return '保存中'
  if (value === 'running') return '工作中'
  return '等待中'
}

const isActive = status => activeStatuses.has(normalizeStatus(status))

const phaseOrder = ['leader', 'executor', 'reviewer', 'saver', 'complete']
const phaseRank = phase => phaseOrder.indexOf(phase)
const phaseNodes = phase => Object.values(nodes.value)
  .filter(node => node.phase === phase)
  .sort((a, b) => Number(b.updatedAt || 0) - Number(a.updatedAt || 0))

const highestReachedPhaseRank = computed(() => {
  return Object.values(nodes.value).reduce((highest, node) => {
    const rank = phaseRank(node.phase)
    const status = normalizeStatus(node.status)
    if (rank >= 0 && status !== 'pending') return Math.max(highest, rank)
    return highest
  }, -1)
})

const aggregatePhaseStatus = phase => {
  if (terminalStatus.value === 'done') return 'done'
  if (terminalStatus.value === 'failed') return phase === 'complete' ? 'failed' : 'done'
  const candidates = phaseNodes(phase)
  if (!candidates.length) return 'pending'
  if (candidates.some(node => normalizeStatus(node.status) === 'failed')) return 'failed'
  const active = candidates.find(node => isActive(node.status))
  if (active) return normalizeStatus(active.status)
  if (candidates.some(node => normalizeStatus(node.status) === 'done')) return 'done'
  return normalizeStatus(candidates[0]?.status)
}

const phaseMessage = (phase, status) => {
  const candidates = phaseNodes(phase)
  if (status === 'done') {
    const done = candidates.find(node => normalizeStatus(node.status) === 'done')
    return done?.message || statusText(status)
  }
  const active = candidates.find(node => isActive(node.status))
  const failed = candidates.find(node => normalizeStatus(node.status) === 'failed')
  const sameStatus = candidates.find(node => normalizeStatus(node.status) === status)
  return active?.message || failed?.message || sameStatus?.message || candidates[0]?.message || statusText(status)
}

const primaryNodes = computed(() => {
  return phaseOrder.map(phase => {
    let status = normalizeStatus(aggregatePhaseStatus(phase))
    if (phaseRank(phase) < highestReachedPhaseRank.value && isActive(status)) {
      status = 'done'
    }
    return {
      id: phase,
      label: phaseLabels[phase],
      status,
      message: phaseMessage(phase, status)
    }
  })
})

const requestedResourceTypes = computed(() => {
  if (props.task?.tool?.generateMode === 'video') return ['video']
  const fromTool = props.task?.tool?.resourceTypes || []
  const fromEvents = Object.values(nodes.value)
    .map(node => node.resource_type || node.resourceType)
    .filter(Boolean)
  return [...new Set([...fromTool, ...fromEvents].map(item => String(item || '').toLowerCase()))]
    .filter(item => item && item !== 'external_video')
})

const hasParallelBranches = computed(() => requestedResourceTypes.value.length > 1)
const parallelTitle = computed(() => hasParallelBranches.value
  ? `${requestedResourceTypes.value.length} 条资源并行`
  : '资源分支'
)

const sortByAgentIndex = (left, right) => {
  const getIndex = node => {
    const id = String(node.agent_id || node.agentId || '')
    const matched = id.match(/section-(\d+)/i)
    return matched ? Number(matched[1]) : Number.MAX_SAFE_INTEGER
  }
  return getIndex(left) - getIndex(right)
}

const childNodesForType = type => {
  const children = Object.values(nodes.value)
    .filter(node => (
      node.phase === 'executor' &&
      String(node.resource_type || node.resourceType || '').toLowerCase() === type &&
      String(node.agent_id || node.agentId || '').includes(':section-')
    ))
    .sort(sortByAgentIndex)
    .map((node, index) => ({
      id: node.agent_id || node.agentId || `${type}-section-${index}`,
      label: `S${index + 1}`,
      status: normalizeStatus(node.status),
      message: node.message || statusText(node.status)
    }))

  return {
    visible: children.slice(0, 8),
    hidden: Math.max(children.length - 8, 0)
  }
}

const branchNodes = computed(() => {
  return requestedResourceTypes.value.map(type => {
    const direct = nodes.value[`executor:${type}`] ||
      (type === 'video' ? nodes.value.executor : null) ||
      Object.values(nodes.value).find(node => (
        node.phase === 'executor' &&
        String(node.resource_type || node.resourceType || '').toLowerCase() === type &&
        !String(node.agent_id || node.agentId || '').includes('section')
      ))
    const status = terminalStatus.value === 'done'
      ? 'done'
      : normalizeStatus(direct?.status || 'pending')
    const children = childNodesForType(type)
    const current = status === 'done' && direct?.total ? direct.total : direct?.current
    const progressText = direct?.total
      ? `${current || 0}/${direct.total}`
      : ''
    return {
      id: `branch:${type}`,
      label: resourceLabels[type] || `${type} 智能体`,
      status,
      message: direct?.message || statusText(status),
      progressText,
      children: children.visible,
      hiddenChildren: children.hidden
    }
  })
})

const recentEvents = computed(() => {
  const normalized = events.value
    .slice(-8)
    .reverse()
    .map((event, index) => ({
      ...event,
      key: `${event.agent_id || event.agentId || index}-${event.updatedAt || event.elapsed_ms || index}`,
      status: normalizeStatus(event.status)
    }))
  if (!terminalStatus.value) return normalized
  const terminalEvents = normalized.filter(event => (
    event.phase === 'complete' ||
    event.status === terminalStatus.value ||
    event.status === 'failed'
  ))
  return terminalEvents.length ? terminalEvents : [{
    key: `terminal-${terminalStatus.value}`,
    agent_name: terminalStatus.value === 'failed' ? '生成失败' : '完成',
    status: terminalStatus.value,
    message: terminalStatus.value === 'failed' ? '生成失败' : '生成完成'
  }]
})

const isLinkLit = index => {
  const left = primaryNodes.value[index]
  const right = primaryNodes.value[index + 1]
  return normalizeStatus(left?.status) === 'done' || isActive(right?.status)
}
</script>

<style scoped>
.agent-flow-drawer {
  position: fixed;
  top: 72px;
  right: 18px;
  z-index: 80;
  width: min(390px, calc(100vw - 28px));
  max-height: calc(100vh - 96px);
  overflow: hidden auto;
  padding: 18px;
  border: 1px solid rgba(169, 195, 218, 0.72);
  border-radius: 18px;
  background: rgba(250, 253, 255, 0.94);
  box-shadow: 0 24px 70px rgba(20, 61, 108, 0.22);
  backdrop-filter: blur(18px);
}

.agent-flow-drawer__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
}

.agent-flow-drawer__header span,
.agent-flow-section-title {
  display: block;
  color: #5c7fa5;
  font-size: 12px;
  font-weight: 900;
}

.agent-flow-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.agent-flow-section-title small {
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(47, 128, 237, 0.1);
  color: #2f80ed;
  font-size: 11px;
}

.agent-flow-drawer__header strong {
  display: block;
  margin-top: 4px;
  color: #173c67;
  font-size: 18px;
  line-height: 1.25;
}

.agent-flow-drawer__header button {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 50%;
  background: rgba(223, 234, 245, 0.82);
  color: #234c77;
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
}

.agent-flow-switcher {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid rgba(194, 212, 227, 0.72);
  border-radius: 14px;
  background: rgba(239, 246, 252, 0.62);
}

.agent-flow-switcher__list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.agent-flow-switcher__list button {
  width: 100%;
  min-height: 42px;
  padding: 8px 10px;
  border: 1px solid rgba(194, 212, 227, 0.86);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.74);
  color: #1c416a;
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.agent-flow-switcher__list button:hover,
.agent-flow-switcher__list button.active {
  border-color: rgba(47, 128, 237, 0.48);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 20px rgba(47, 128, 237, 0.12);
}

.agent-flow-switcher__list span {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #a9bed0;
}

.agent-flow-switcher__list span.is-running,
.agent-flow-switcher__list span.is-reviewing,
.agent-flow-switcher__list span.is-retrying,
.agent-flow-switcher__list span.is-saving {
  background: #2f80ed;
  box-shadow: 0 0 0 4px rgba(47, 128, 237, 0.12);
}

.agent-flow-switcher__list span.is-done {
  background: #24b47e;
}

.agent-flow-switcher__list span.is-failed {
  background: #e65252;
}

.agent-flow-switcher__list strong {
  overflow: hidden;
  font-size: 12px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-flow-switcher__list small {
  color: #6f8ca9;
  font-size: 11px;
  font-weight: 900;
  white-space: nowrap;
}

.agent-flow-drawer__stage {
  display: grid;
  gap: 0;
}

.agent-flow-node-wrap {
  display: grid;
  grid-template-columns: 1fr;
}

.agent-flow-node {
  position: relative;
  isolation: isolate;
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 12px;
  align-items: center;
  min-height: 58px;
  padding: 12px;
  border: 1px solid rgba(194, 212, 227, 0.9);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  color: #1c416a;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.agent-flow-node > *,
.agent-flow-branch > * {
  position: relative;
  z-index: 1;
}

.agent-flow-node.is-active::before,
.agent-flow-branch.is-active::before {
  content: "";
  position: absolute;
  inset: -2px;
  z-index: 0;
  padding: 2px;
  border-radius: inherit;
  background:
    conic-gradient(
      from var(--agent-flow-orbit-angle, 0deg),
      transparent 0deg,
      transparent 245deg,
      rgba(85, 214, 167, 0.22) 278deg,
      rgba(93, 156, 236, 0.95) 310deg,
      rgba(255, 255, 255, 0.98) 330deg,
      transparent 360deg
    );
  pointer-events: none;
  animation: agentFlowOrbit 1.2s linear infinite;
  -webkit-mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask:
    linear-gradient(#000 0 0) content-box,
    linear-gradient(#000 0 0);
  mask-composite: exclude;
}

.agent-flow-node__icon,
.agent-flow-branch > span {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #edf3f9;
  color: #6e8bac;
  font-size: 13px;
  font-weight: 900;
}

.agent-flow-node strong,
.agent-flow-branch strong {
  display: block;
  font-size: 14px;
}

.agent-flow-node small,
.agent-flow-branch small {
  display: -webkit-box;
  overflow: hidden;
  color: rgba(28, 65, 106, 0.66);
  font-size: 12px;
  line-height: 1.35;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.agent-flow-link {
  width: 2px;
  height: 22px;
  margin-left: 28px;
  background: rgba(177, 199, 218, 0.8);
}

.agent-flow-link.is-lit {
  background: linear-gradient(180deg, #5d9cec, #55d6a7, #5d9cec);
  background-size: 100% 200%;
  animation: agentFlowLine 1.1s linear infinite;
}

.agent-flow-node.is-running,
.agent-flow-node.is-reviewing,
.agent-flow-node.is-retrying,
.agent-flow-node.is-saving,
.agent-flow-branch.is-running,
.agent-flow-branch.is-reviewing,
.agent-flow-branch.is-retrying,
.agent-flow-branch.is-saving {
  border-color: rgba(65, 145, 226, 0.9);
  box-shadow: 0 12px 30px rgba(65, 145, 226, 0.2), 0 0 0 4px rgba(65, 145, 226, 0.08);
  transform: translateX(-2px);
}

.agent-flow-node.is-running .agent-flow-node__icon,
.agent-flow-branch.is-running > span {
  background: #2f80ed;
  color: #fff;
}

.agent-flow-node.is-reviewing .agent-flow-node__icon,
.agent-flow-branch.is-reviewing > span,
.agent-flow-node.is-retrying .agent-flow-node__icon,
.agent-flow-branch.is-retrying > span {
  background: #f4a340;
  color: #fff;
}

.agent-flow-node.is-saving .agent-flow-node__icon,
.agent-flow-branch.is-saving > span {
  background: #7b61ff;
  color: #fff;
}

.agent-flow-node.is-done .agent-flow-node__icon,
.agent-flow-branch.is-done > span {
  background: #24b47e;
  color: #fff;
}

.agent-flow-node.is-failed .agent-flow-node__icon,
.agent-flow-branch.is-failed > span {
  background: #e65252;
  color: #fff;
}

.agent-flow-node__pulse {
  position: absolute;
  left: 6px;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  opacity: 0;
  pointer-events: none;
}

.agent-flow-node.is-active .agent-flow-node__pulse {
  background: rgba(47, 128, 237, 0.18);
  animation: agentFlowPulse 1.4s ease-out infinite;
  opacity: 1;
}

.agent-flow-branches,
.agent-flow-log {
  margin-top: 18px;
}

.agent-flow-parallel-hub {
  position: relative;
  display: grid;
  place-items: center;
  margin: 10px 0 4px;
  color: #4d79a7;
  font-size: 11px;
  font-weight: 900;
}

.agent-flow-parallel-hub span {
  position: relative;
  z-index: 1;
  padding: 4px 10px;
  border: 1px solid rgba(95, 143, 195, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
}

.agent-flow-parallel-hub i {
  position: absolute;
  left: 12%;
  right: 12%;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(47, 128, 237, 0.6), transparent);
}

.agent-flow-branch-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}

.agent-flow-branch {
  position: relative;
  isolation: isolate;
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 9px;
  align-items: center;
  min-height: 66px;
  padding: 10px;
  border: 1px solid rgba(194, 212, 227, 0.86);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.68);
}

.agent-flow-branch__progress {
  margin-top: 6px;
  color: #2f80ed;
  font-size: 11px;
  font-weight: 900;
}

.agent-flow-branch__children {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}

.agent-flow-branch__children span,
.agent-flow-branch__children em {
  min-width: 24px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(169, 190, 208, 0.22);
  color: #6684a3;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
}

.agent-flow-branch__children span.is-running,
.agent-flow-branch__children span.is-reviewing,
.agent-flow-branch__children span.is-retrying,
.agent-flow-branch__children span.is-saving {
  background: rgba(47, 128, 237, 0.14);
  color: #1f70d6;
  box-shadow: 0 0 0 3px rgba(47, 128, 237, 0.08);
}

.agent-flow-branch__children span.is-done {
  background: rgba(36, 180, 126, 0.14);
  color: #159769;
}

.agent-flow-branch__children span.is-failed {
  background: rgba(230, 82, 82, 0.14);
  color: #d33d3d;
}

.agent-flow-log__list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.agent-flow-log__list p,
.agent-flow-log__empty {
  margin: 0;
  padding: 9px 10px;
  border-radius: 12px;
  background: rgba(239, 246, 252, 0.78);
  color: rgba(28, 65, 106, 0.72);
  font-size: 12px;
  line-height: 1.45;
}

.agent-flow-log__list span {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 7px;
  border-radius: 50%;
  background: #a9bed0;
}

.agent-flow-log__list span.is-running,
.agent-flow-log__list span.is-reviewing,
.agent-flow-log__list span.is-retrying,
.agent-flow-log__list span.is-saving {
  background: #2f80ed;
  box-shadow: 0 0 0 4px rgba(47, 128, 237, 0.12);
}

.agent-flow-log__list span.is-done {
  background: #24b47e;
}

.agent-flow-log__list span.is-failed {
  background: #e65252;
}

.agent-flow-log__list strong {
  margin-right: 6px;
  color: #1e4771;
}

.agent-flow-log__list em {
  font-style: normal;
}

.agent-flow-slide-enter-active,
.agent-flow-slide-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.agent-flow-slide-enter-from,
.agent-flow-slide-leave-to {
  opacity: 0;
  transform: translateX(32px);
}

@keyframes agentFlowPulse {
  0% {
    transform: scale(0.72);
    opacity: 0.72;
  }
  100% {
    transform: scale(1.35);
    opacity: 0;
  }
}

@keyframes agentFlowLine {
  from {
    background-position: 0 0;
  }
  to {
    background-position: 0 200%;
  }
}

@property --agent-flow-orbit-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

@keyframes agentFlowOrbit {
  from {
    --agent-flow-orbit-angle: 0deg;
  }
  to {
    --agent-flow-orbit-angle: 360deg;
  }
}

@media (max-width: 760px) {
  .agent-flow-drawer {
    top: auto;
    right: 10px;
    bottom: 10px;
    left: 10px;
    width: auto;
    max-height: 72vh;
  }
}
</style>
