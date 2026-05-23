<template>
  <div class="mindmap-preview">
    <div ref="mapEl" class="mindmap-canvas"></div>
    <div v-if="errorText" class="mindmap-fallback">
      <strong>{{ fallbackTitle }}</strong>
      <pre>{{ fallbackText }}</pre>
    </div>
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
  }
})

const mapEl = ref(null)
const errorText = ref('')
let mind = null
let nodeIndex = 0

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

const toMindElixirData = value => {
  const parsed = parseContent(value)
  const root = Array.isArray(parsed)
    ? { topic: fallbackTitle.value, children: parsed }
    : parsed?.nodeData || parsed?.root || parsed?.mindmap || parsed?.data || parsed

  nodeIndex = 0
  return {
    nodeData: normalizeNode(root),
    linkData: {},
    direction: MindElixir.RIGHT
  }
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

    mind = new MindElixir({
      el: mapEl.value,
      direction: MindElixir.RIGHT,
      editable: false,
      contextMenu: false,
      toolBar: false,
      keypress: false,
      draggable: true,
      mouseSelectionButton: 0,
      overflowHidden: false
    })

    mind.init(data)
    requestAnimationFrame(() => {
      mind?.scaleFit?.()
      mind?.toCenter?.()
    })
  } catch (error) {
    console.error('Mindmap render failed:', error)
    errorText.value = error?.message || 'render failed'
  }
}

watch(() => [props.content, props.title], renderMap, { deep: true })
onMounted(renderMap)

onBeforeUnmount(() => {
  if (mind) {
    mind.destroy()
    mind = null
  }
})
</script>

<style scoped>
.mindmap-preview {
  position: relative;
  width: 100%;
  min-height: 520px;
  border: 1px solid rgba(54, 117, 204, 0.18);
  border-radius: 18px;
  overflow: hidden;
  background: #f8fcff;
}

.mindmap-canvas {
  width: 100%;
  height: 620px;
  min-height: 520px;
}

.mindmap-preview :deep(.map-container) {
  background:
    radial-gradient(circle at 1px 1px, rgba(31, 77, 158, 0.08) 1px, transparent 0),
    #f8fcff;
  background-size: 18px 18px;
}

.mindmap-preview :deep(me-root > me-tpc) {
  background: #17479d;
  color: #fff;
  border-radius: 999px;
  padding: 12px 18px;
  font-weight: 800;
}

.mindmap-preview :deep(me-tpc) {
  border: 1px solid rgba(54, 117, 204, 0.22);
  border-radius: 14px;
  color: #163f8f;
  box-shadow: 0 10px 24px rgba(36, 87, 162, 0.12);
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
</style>
