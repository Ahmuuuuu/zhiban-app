<template>
  <div class="mindmap-preview" :class="`mindmap-preview--${layoutProfile.name}`" @click="openFullscreen">
    <div ref="mapEl" class="mindmap-canvas"></div>
    <div v-if="!fullscreenOpen" class="mindmap-hint">点击放大预览</div>
    <div v-if="errorText && !fullscreenOpen" class="mindmap-fallback">
      <strong>{{ fallbackTitle }}</strong>
      <pre>{{ fallbackText }}</pre>
    </div>

    <Teleport to="body">
      <div
        v-if="fullscreenOpen"
        class="mindmap-overlay"
        :class="`mindmap-overlay--${layoutProfile.name}`"
        @click.self="closeFullscreen"
      >
        <div class="mindmap-overlay__toolbar">
          <button type="button" class="mindmap-overlay__back" @click="closeFullscreen">返回聊天</button>
          <span class="mindmap-overlay__title">{{ fallbackTitle }}</span>
          <div class="mindmap-overlay__actions">
            <button type="button" @click="zoomOut" title="缩小">−</button>
            <span class="mindmap-overlay__zoom-label">{{ Math.round(currentScale * 100) }}%</span>
            <button type="button" @click="zoomIn" title="放大">+</button>
            <button type="button" @click="zoomFit" title="适应画面">⊡</button>
            <button type="button" class="mindmap-overlay__close" @click="closeFullscreen" title="关闭">×</button>
          </div>
        </div>
        <div ref="overlayEl" class="mindmap-overlay__canvas"></div>
        <div v-if="overlayError" class="mindmap-fallback mindmap-fallback--overlay">
          <strong>{{ fallbackTitle }}</strong>
          <pre>{{ fallbackText }}</pre>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MindElixir from 'mind-elixir'
import 'mind-elixir/style.css'

const props = defineProps({
  content: {
    type: [String, Object, Array],
    default: ''
  },
  title: {
    type: String,
    default: ''
  },
  openSignal: {
    type: Number,
    default: 0
  }
})

const mapEl = ref(null)
const overlayEl = ref(null)
const errorText = ref('')
const overlayError = ref('')
const fullscreenOpen = ref(false)
const currentScale = ref(1)
const layoutProfile = ref({ name: 'balanced', title: '平衡结构' })
let mind = null
let overlayMind = null
let nodeIndex = 0

const branchPalette = [
  '#58AEEA',
  '#21A7A8',
  '#7BB940',
  '#D88A19',
  '#B889D8',
  '#E45F8F',
  '#F2B705',
  '#6D8EEB',
  '#EF746F',
  '#55C9A7'
]

const fallbackTitle = computed(() => props.title || '思维导图')
const fallbackText = computed(() => {
  if (typeof props.content === 'string') return props.content
  try {
    return JSON.stringify(props.content, null, 2)
  } catch {
    return ''
  }
})

const parseContent = value => {
  if (!value) return { topic: fallbackTitle.value, children: [] }
  if (typeof value === 'object') return value

  const text = String(value).trim()
  const jsonText = text
    .replace(/^```(?:json)?/i, '')
    .replace(/```$/i, '')
    .trim()

  try {
    return JSON.parse(jsonText)
  } catch {
    const lines = text
      .split(/\r?\n/)
      .map(line => line.replace(/^[-*\d.\s#]+/, '').trim())
      .filter(Boolean)

    return {
      topic: fallbackTitle.value,
      children: lines.map(line => ({ topic: line, children: [] }))
    }
  }
}

const normalizeNode = (node, parent = null) => {
  if (typeof node === 'string') {
    nodeIndex += 1
    return {
      id: `mind-${nodeIndex}`,
      topic: node,
      parent,
      expanded: true,
      children: []
    }
  }

  const rawChildren = Array.isArray(node?.children)
    ? node.children
    : Array.isArray(node?.nodes)
      ? node.nodes
      : []

  nodeIndex += 1
  const normalized = {
    id: String(node?.id || `mind-${nodeIndex}`),
    topic: String(node?.topic || node?.title || node?.name || node?.label || node?.text || fallbackTitle.value),
    parent,
    expanded: node?.expanded !== false,
    children: []
  }

  normalized.children = rawChildren.map(child => normalizeNode(child, normalized.id))
  return normalized
}

const collectStats = (node, depth = 1) => {
  const children = Array.isArray(node?.children) ? node.children : []
  const childStats = children.map(child => collectStats(child, depth + 1))
  const totalNodes = 1 + childStats.reduce((sum, item) => sum + item.totalNodes, 0)
  const maxDepth = Math.max(depth, ...childStats.map(item => item.maxDepth))
  const maxBreadth = Math.max(children.length, ...childStats.map(item => item.maxBreadth))
  const leafCount = children.length ? childStats.reduce((sum, item) => sum + item.leafCount, 0) : 1
  const topicLength = String(node?.topic || '').length + childStats.reduce((sum, item) => sum + item.topicLength, 0)
  return { totalNodes, maxDepth, maxBreadth, leafCount, topicLength }
}

const getBranchWeight = node => {
  const stats = collectStats(node)
  return stats.leafCount * 2 + stats.totalNodes + stats.maxDepth * 3
}

const detectKnowledgeType = node => {
  const text = JSON.stringify(node || '').toLowerCase()
  if (/流程|步骤|阶段|路径|顺序|过程|怎么做|process|step|stage|flow/.test(text)) return 'process'
  if (/对比|区别|优点|缺点|比较|相同|不同|compare|versus|pros|cons/.test(text)) return 'compare'
  if (/注意|原则|要点|清单|规范|风险|checklist|rule|risk/.test(text)) return 'checklist'
  if (/公式|定义|概念|性质|定理|原理|模型|concept|definition|theory/.test(text)) return 'concept'
  return 'general'
}

const chooseLayoutProfile = root => {
  const stats = collectStats(root)
  const rootChildren = root?.children?.length || 0
  const avgTopicLength = stats.totalNodes ? stats.topicLength / stats.totalNodes : 0
  const type = detectKnowledgeType(root)

  if (rootChildren >= 4 || stats.totalNodes > 26 || stats.leafCount > 14) {
    return { name: 'compact', title: '紧凑平衡', direction: MindElixir.SIDE, stats }
  }
  if (type === 'compare' || (rootChildren <= 3 && stats.totalNodes <= 22)) {
    return { name: 'split', title: '对比结构', direction: MindElixir.SIDE, stats }
  }
  if (rootChildren >= 7 || (stats.totalNodes >= 18 && stats.maxDepth <= 3 && avgTopicLength < 12)) {
    return { name: 'radial', title: '放射结构', direction: MindElixir.SIDE, stats }
  }
  if ((type === 'process' || avgTopicLength > 22) && rootChildren <= 2) {
    return { name: 'outline', title: '阅读提纲', direction: MindElixir.RIGHT, stats }
  }
  return { name: type === 'checklist' ? 'checklist' : 'balanced', title: '平衡结构', direction: MindElixir.SIDE, stats }
}

const assignBalancedBranchDirections = root => {
  const children = Array.isArray(root.children) ? root.children : []
  const buckets = [
    { direction: MindElixir.LEFT, weight: 0 },
    { direction: MindElixir.RIGHT, weight: 0 }
  ]

  children
    .map(child => ({ child, weight: getBranchWeight(child) }))
    .sort((a, b) => b.weight - a.weight)
    .forEach(({ child, weight }) => {
      const target = buckets[0].weight <= buckets[1].weight ? buckets[0] : buckets[1]
      child.direction = target.direction
      target.weight += weight
    })
}

const styleNodeByLayout = (node, profile, depth = 0, branchIndex = 0) => {
  const color = branchPalette[branchIndex % branchPalette.length]
  const children = Array.isArray(node.children) ? node.children : []

  if (depth === 0) {
    node.style = {
      color: '#ffffff',
      background: profile.name === 'radial' ? '#30313D' : '#2F5D9F',
      fontWeight: '800',
      fontSize: profile.name === 'outline' ? '18px' : '20px',
      border: '0'
    }
  } else if (depth === 1) {
    node.branchColor = color
    node.style = {
      color: '#ffffff',
      background: color,
      fontWeight: '800',
      fontSize: profile.name === 'radial' ? '13px' : '15px',
      border: '0'
    }
    if (profile.direction === MindElixir.SIDE && node.direction === undefined) {
      node.direction = branchIndex % 2 === 0 ? MindElixir.RIGHT : MindElixir.LEFT
    }
  } else {
    const softBg = `${color}18`
    node.branchColor = color
    node.style = {
      color: '#2B3440',
      background: profile.name === 'outline' ? '#FFFFFF' : softBg,
      fontWeight: depth === 2 ? '700' : '500',
      fontSize: depth >= 3 ? '12px' : '13px',
      border: `1px solid ${color}55`
    }
  }

  children.forEach((child, index) => {
    styleNodeByLayout(child, profile, depth + 1, depth === 0 ? index : branchIndex)
  })
}

const toMindElixirData = value => {
  const parsed = parseContent(value)
  const root = Array.isArray(parsed)
    ? { topic: fallbackTitle.value, children: parsed }
    : parsed?.nodeData || parsed?.root || parsed?.mindmap || parsed?.data || parsed

  nodeIndex = 0
  const nodeData = normalizeNode(root)
  const profile = chooseLayoutProfile(nodeData)
  if (profile.direction === MindElixir.SIDE) {
    assignBalancedBranchDirections(nodeData)
  }
  styleNodeByLayout(nodeData, profile)
  layoutProfile.value = profile

  return {
    nodeData,
    linkData: {},
    direction: profile.direction
  }
}

const themeForProfile = profile => {
  const isOutline = profile.name === 'outline'
  const isRadial = profile.name === 'radial'
  const isCompact = profile.name === 'compact'
  return {
    name: `Zhiban-${profile.name}`,
    type: 'light',
    palette: branchPalette,
    cssVar: {
      '--node-gap-x': isOutline ? '54px' : isCompact ? '44px' : isRadial ? '40px' : '48px',
      '--node-gap-y': isOutline ? '12px' : isCompact ? '7px' : isRadial ? '8px' : '11px',
      '--main-gap-x': isOutline ? '108px' : isCompact ? '112px' : isRadial ? '88px' : '104px',
      '--main-gap-y': isOutline ? '42px' : isCompact ? '24px' : isRadial ? '28px' : '38px',
      '--root-radius': isRadial ? '999px' : '10px',
      '--main-radius': isRadial ? '999px' : '8px',
      '--root-color': '#ffffff',
      '--root-bgcolor': '#2F5D9F',
      '--root-border-color': 'rgba(0, 0, 0, 0)',
      '--main-color': '#2B3440',
      '--main-bgcolor': '#ffffff',
      '--main-bgcolor-transparent': 'rgba(255, 255, 255, 0.9)',
      '--topic-padding': isCompact ? '4px 9px' : isRadial ? '5px 10px' : '6px 12px',
      '--color': '#5B6574',
      '--bgcolor': '#FAFCFF',
      '--selected': '#45A3FF',
      '--accent-color': '#21A7A8',
      '--panel-color': '#2B3440',
      '--panel-bgcolor': '#ffffff',
      '--panel-border-color': '#E7EEF8',
      '--map-padding': isCompact ? '18px 24px' : isOutline ? '48px 72px' : '42px 64px'
    }
  }
}

const createMindInstance = (el, data, profile = layoutProfile.value) => {
  const instance = new MindElixir({
    el,
    direction: profile.direction,
    editable: false,
    contextMenu: false,
    toolBar: false,
    keypress: false,
    draggable: true,
    mouseSelectionButton: 0,
    overflowHidden: false,
    theme: themeForProfile(profile)
  })
  instance.init(data)
  return instance
}

const renderMap = async () => {
  await nextTick()
  if (!mapEl.value) return

  errorText.value = ''

  try {
    const data = toMindElixirData(props.content)

    if (mind) {
      mind.destroy()
      mind = null
    }

    mind = createMindInstance(mapEl.value, data)
    requestAnimationFrame(() => {
      mind?.scaleFit?.()
      mind?.toCenter?.()
    })
  } catch (error) {
    console.error('Mindmap render failed:', error)
    errorText.value = error?.message || 'render failed'
  }
}

const renderOverlayMap = async () => {
  await nextTick()
  if (!overlayEl.value) return

  overlayError.value = ''

  try {
    const data = toMindElixirData(props.content)

    if (overlayMind) {
      overlayMind.destroy()
      overlayMind = null
    }

    overlayMind = createMindInstance(overlayEl.value, data)
    await nextTick()
    requestAnimationFrame(() => {
      overlayMind?.scaleFit?.()
      overlayMind?.toCenter?.()
      currentScale.value = 1
    })
  } catch (error) {
    console.error('Overlay mindmap render failed:', error)
    overlayError.value = error?.message || 'overlay render failed'
  }
}

const openFullscreen = () => {
  if (fullscreenOpen.value) return
  fullscreenOpen.value = true
  nextTick(() => {
    if (overlayEl.value) {
      renderOverlayMap()
    }
  })
  document.addEventListener('keydown', handleKeydown)
}

const closeFullscreen = () => {
  fullscreenOpen.value = false
  if (overlayMind) {
    overlayMind.destroy()
    overlayMind = null
  }
  document.removeEventListener('keydown', handleKeydown)
}

const handleKeydown = (e) => {
  if (e.key === 'Escape') {
    closeFullscreen()
  }
}

const zoomIn = () => {
  if (!overlayMind) return
  const next = Math.min(currentScale.value + 0.25, 3)
  overlayMind.scale(next)
  currentScale.value = next
}

const zoomOut = () => {
  if (!overlayMind) return
  const next = Math.max(currentScale.value - 0.25, 0.25)
  overlayMind.scale(next)
  currentScale.value = next
}

const zoomFit = () => {
  if (!overlayMind) return
  overlayMind.scaleFit()
  overlayMind.toCenter()
  currentScale.value = 1
}

watch(() => [props.content, props.title], renderMap, { deep: true })
watch(() => props.openSignal, value => {
  if (value) openFullscreen()
})
onMounted(renderMap)

onBeforeUnmount(() => {
  if (mind) {
    mind.destroy()
    mind = null
  }
  if (overlayMind) {
    overlayMind.destroy()
    overlayMind = null
  }
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.mindmap-preview {
  position: relative;
  width: 100%;
  min-height: 520px;
  border: 1px solid rgba(44, 92, 153, 0.16);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  cursor: pointer;
  transition: box-shadow 0.2s ease;
}

.mindmap-preview:hover {
  box-shadow: 0 0 0 3px rgba(54, 117, 204, 0.14);
}

.mindmap-canvas {
  width: 100%;
  height: 620px;
  min-height: 520px;
}

.mindmap-hint {
  position: absolute;
  right: 12px;
  bottom: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(23, 71, 157, 0.72);
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.22s ease;
}

.mindmap-preview:hover .mindmap-hint {
  opacity: 1;
}

.mindmap-preview :deep(.map-container) {
  background: #fff;
}

.mindmap-preview :deep(me-root > me-tpc) {
  background: #2f5d9f;
  color: #fff;
  border-radius: 10px;
  padding: 13px 20px;
  font-weight: 800;
  box-shadow: 0 14px 34px rgba(47, 93, 159, 0.22);
}

.mindmap-preview :deep(me-tpc) {
  border-radius: 8px;
  line-height: 1.42;
  box-shadow: 0 8px 18px rgba(35, 59, 92, 0.1);
}

.mindmap-preview :deep(.lines path),
.mindmap-preview :deep(.subLines path) {
  stroke-width: 2.3px;
}

.mindmap-preview--radial :deep(me-root > me-tpc),
.mindmap-overlay--radial :deep(me-root > me-tpc) {
  border-radius: 999px;
  padding: 22px 20px;
  min-width: 92px;
  min-height: 92px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.mindmap-preview--radial :deep(me-tpc),
.mindmap-overlay--radial :deep(me-tpc) {
  border-radius: 999px;
}

.mindmap-preview--outline :deep(me-root > me-tpc),
.mindmap-overlay--outline :deep(me-root > me-tpc) {
  border-radius: 8px;
}

.mindmap-preview--outline :deep(me-tpc),
.mindmap-overlay--outline :deep(me-tpc) {
  min-width: 96px;
}

.mindmap-preview--compact :deep(me-root > me-tpc),
.mindmap-overlay--compact :deep(me-root > me-tpc) {
  padding: 10px 14px;
  font-size: 16px;
}

.mindmap-preview--compact :deep(me-tpc),
.mindmap-overlay--compact :deep(me-tpc) {
  padding: 4px 9px;
  font-size: 12px;
  line-height: 1.28;
  box-shadow: 0 5px 12px rgba(35, 59, 92, 0.08);
}

.mindmap-preview--compact :deep(.lines path),
.mindmap-preview--compact :deep(.subLines path),
.mindmap-overlay--compact :deep(.lines path),
.mindmap-overlay--compact :deep(.subLines path) {
  stroke-width: 1.8px;
}

.mindmap-fallback {
  position: absolute;
  inset: 18px;
  padding: 18px;
  overflow: auto;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  color: #163f8f;
}

.mindmap-fallback pre {
  white-space: pre-wrap;
  word-break: break-word;
}

/* ─── 全屏预览 ─── */

.mindmap-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(8, 23, 51, 0.82);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
}

.mindmap-overlay__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.mindmap-overlay__title {
  color: #fff;
  font-size: 16px;
  font-weight: 800;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mindmap-overlay__back {
  min-width: 82px;
  height: 38px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}

.mindmap-overlay__back:hover {
  background: rgba(255, 255, 255, 0.2);
}

.mindmap-overlay__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.mindmap-overlay__actions button {
  min-width: 38px;
  height: 38px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 17px;
  font-weight: 800;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease;
}

.mindmap-overlay__actions button:hover {
  background: rgba(255, 255, 255, 0.18);
}

.mindmap-overlay__zoom-label {
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  font-weight: 800;
  min-width: 46px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.mindmap-overlay__close {
  font-size: 20px !important;
  margin-left: 8px;
}

.mindmap-overlay__canvas {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.mindmap-overlay :deep(.map-container) {
  background: #fff;
}

.mindmap-overlay :deep(me-root > me-tpc) {
  background: #2f5d9f;
  color: #fff;
  border-radius: 10px;
  padding: 14px 22px;
  font-weight: 800;
  font-size: 16px;
  box-shadow: 0 16px 36px rgba(47, 93, 159, 0.24);
}

.mindmap-overlay :deep(me-tpc) {
  border-radius: 8px;
  line-height: 1.42;
  box-shadow: 0 9px 20px rgba(35, 59, 92, 0.12);
}

.mindmap-overlay :deep(.lines path),
.mindmap-overlay :deep(.subLines path) {
  stroke-width: 2.5px;
}

.mindmap-fallback--overlay {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: min(600px, 90vw);
  max-height: 70vh;
  color: #ccc;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
}
</style>
