<template>
  <div class="hotwords-chart" :class="{ 'hotwords-chart--empty': !displayWords.length }">
    <div v-if="title" class="hotwords-chart__header">
      <h3>{{ title }}</h3>
      <span class="hotwords-chart__count">{{ displayWords.length }} 个热词</span>
    </div>

    <div v-if="!displayWords.length" class="hotwords-chart__empty">
      <span>暂无热词数据</span>
    </div>

    <canvas
      v-else
      ref="canvasRef"
      class="hotwords-chart__canvas"
      :width="canvasWidth"
      :height="canvasHeight"
      @click="handleClick"
    ></canvas>

    <!-- tooltip on hover/click -->
    <div
      v-if="tooltip.visible"
      class="hotwords-chart__tooltip"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <strong>{{ tooltip.text }}</strong>
      <span>权重 {{ tooltip.weight }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'

const props = defineProps({
  words: {
    type: Array,
    default: () => []
    // [{ text: '光合作用', weight: 92 }, ...]
  },
  title: {
    type: String,
    default: '热词分析'
  },
  maxWords: {
    type: Number,
    default: 50
  },
  width: {
    type: Number,
    default: 680
  },
  height: {
    type: Number,
    default: 420
  }
})

const emit = defineEmits(['word-click'])

const canvasRef = ref(null)
const tooltip = reactive({ visible: false, x: 0, y: 0, text: '', weight: 0 })
let placedRects = []
let resizeObserver = null

const canvasWidth = ref(props.width)
const canvasHeight = ref(props.height)

// ---- palette for word colours ----
const PALETTE_LIGHT = [
  '#163f8f', '#2f80ed', '#11695f', '#28b487',
  '#93491f', '#e86c00', '#4c1d95', '#8b5cf6',
  '#9f1239', '#fb7185', '#854d0e', '#f59e0b'
]

const PALETTE_DARK = [
  '#5b9bd5', '#6db3f2', '#52b86f', '#6dd49e',
  '#f0a060', '#ffb347', '#b39cf5', '#c9b8ff',
  '#fb8ea0', '#fdacb8', '#f5c542', '#ffd166'
]

const isDark = () => document.documentElement.getAttribute('data-theme') === 'dark' ||
  (!document.documentElement.getAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)

const palette = () => isDark() ? PALETTE_DARK : PALETTE_LIGHT

const displayWords = computed(() => {
  const list = (props.words || [])
    .filter(w => w && w.text)
    .slice(0, props.maxWords)
  if (!list.length) return []

  const weights = list.map(w => w.weight || 1)
  const wMin = Math.min(...weights)
  const wMax = Math.max(...weights)
  const range = wMax - wMin || 1

  return list.map(w => ({
    text: String(w.text).trim(),
    weight: w.weight || 1,
    norm: (w.weight - wMin) / range  // 0..1
  }))
})

const getFontSize = norm => {
  const min = 13
  const max = 44
  return Math.round(min + norm * (max - min))
}

// ---- spiral-based placement ----
function rectsOverlap(a, b, padding = 3) {
  return !(
    a.x + a.w + padding < b.x ||
    b.x + b.w + padding < a.x ||
    a.y + a.h + padding < b.y ||
    b.y + b.h + padding < a.y
  )
}

function placeWord(ctx, text, fontSize, cw, ch) {
  ctx.font = `800 ${fontSize}px "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif`
  const metrics = ctx.measureText(text)
  const tw = metrics.width + 8
  const th = fontSize * 1.25

  // Archimedean spiral
  const cx = cw / 2
  const cy = ch / 2
  let angle = Math.random() * Math.PI * 2
  let radius = 0
  const maxRadius = Math.min(cw, ch) * 0.65
  const step = 0.6
  const angleStep = 0.15

  for (let i = 0; i < 3000; i++) {
    const x = cx + radius * Math.cos(angle) - tw / 2
    const y = cy + radius * Math.sin(angle) - th / 2
    const rect = { x: Math.max(2, x), y: Math.max(2, y), w: tw, h: th }

    const overlaps = placedRects.some(r => rectsOverlap(r, rect))
    if (!overlaps) {
      placedRects.push(rect)
      return { x: rect.x, y: rect.y + fontSize * 0.85, w: tw }
    }

    radius += step
    angle += angleStep + (0.08 / (radius + 1))
    if (radius > maxRadius) break
  }

  // fallback: place at random
  for (let attempt = 0; attempt < 60; attempt++) {
    const fx = 4 + Math.random() * (cw - tw - 8)
    const fy = 4 + Math.random() * (ch - th - 8)
    const rect = { x: fx, y: fy, w: tw, h: th }
    if (!placedRects.some(r => rectsOverlap(r, rect))) {
      placedRects.push(rect)
      return { x: fx, y: fy + fontSize * 0.85, w: tw }
    }
  }

  return null
}

// ---- draw ----
function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const cw = canvas.width
  const ch = canvas.height
  const dpr = window.devicePixelRatio || 1

  // Set display size
  canvas.style.width = cw + 'px'
  canvas.style.height = ch + 'px'
  // Set actual size scaled for DPR
  canvas.width = cw * dpr
  canvas.height = ch * dpr
  ctx.scale(dpr, dpr)

  placedRects = []
  ctx.clearRect(0, 0, cw, ch)

  const words = displayWords.value
  if (!words.length) return

  const colors = palette()
  const bgColor = isDark() ? '#1a2535' : '#ffffff'
  const mutedColor = isDark() ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)'

  // bg
  ctx.fillStyle = bgColor
  ctx.beginPath()
  ctx.roundRect(0, 0, cw, ch, 12)
  ctx.fill()

  // subtle grid
  ctx.strokeStyle = mutedColor
  ctx.lineWidth = 1
  for (let x = 0; x < cw; x += 40) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, ch); ctx.stroke()
  }
  for (let y = 0; y < ch; y += 40) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(cw, y); ctx.stroke()
  }

  // Place words — largest first
  const sorted = [...words].sort((a, b) => b.weight - a.weight)
  const placed = []

  for (const word of sorted) {
    const fontSize = getFontSize(word.norm)
    const pos = placeWord(ctx, word.text, fontSize, cw, ch)
    if (pos) {
      placed.push({ ...word, ...pos, fontSize })
    }
  }

  // Draw
  for (const item of placed) {
    const alpha = 0.45 + item.norm * 0.55
    const colorIndex = Math.floor(item.norm * (colors.length - 1))
    const color = colors[Math.min(colorIndex, colors.length - 1)]
    ctx.globalAlpha = alpha
    ctx.fillStyle = color
    ctx.font = `800 ${item.fontSize}px "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif`
    ctx.fillText(item.text, item.x, item.y)

    // small underline for emphasis on top words
    if (item.norm > 0.7) {
      ctx.globalAlpha = alpha * 0.35
      ctx.fillStyle = color
      ctx.fillRect(item.x, item.y + 4, Math.min(item.w - 8, 40), 2)
    }
  }

  ctx.globalAlpha = 1

  // Store placed items for click detection
  canvas._placedWords = placed
}

// ---- click → tooltip / emit ----
function handleClick(e) {
  const canvas = canvasRef.value
  if (!canvas || !canvas._placedWords) return

  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / (window.devicePixelRatio || 1) / rect.width
  const scaleY = canvas.height / (window.devicePixelRatio || 1) / rect.height
  const mx = (e.clientX - rect.left) * scaleX
  const my = (e.clientY - rect.top) * scaleY

  for (const item of canvas._placedWords) {
    if (mx >= item.x && mx <= item.x + item.w && my >= item.y - item.fontSize && my <= item.y + 4) {
      emit('word-click', item)
      tooltip.visible = true
      tooltip.text = item.text
      tooltip.weight = item.weight
      tooltip.x = e.clientX - rect.left
      tooltip.y = e.clientY - rect.top - 46
      setTimeout(() => { tooltip.visible = false }, 1800)
      return
    }
  }
  tooltip.visible = false
}

// ---- responsive resize ----
function handleResize() {
  if (!canvasRef.value) return
  const parent = canvasRef.value.parentElement
  if (!parent || !parent.clientWidth) return
  canvasWidth.value = Math.min(props.width, parent.clientWidth - 32)
  canvasHeight.value = Math.round(canvasWidth.value * 0.6)
  nextTick(draw)
}

onMounted(() => {
  handleResize()
  resizeObserver = new ResizeObserver(handleResize)
  if (canvasRef.value?.parentElement) {
    resizeObserver.observe(canvasRef.value.parentElement)
  }
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('resize', handleResize)
})

watch(() => props.words, () => nextTick(draw), { deep: true })
watch(() => props.width, handleResize)
</script>

<style scoped>
.hotwords-chart {
  position: relative;
  width: 100%;
  min-height: 160px;
  display: grid;
  gap: 10px;
}

.hotwords-chart--empty {
  min-height: 120px;
}

.hotwords-chart__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.hotwords-chart__header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: var(--color-text-heading, #143761);
}

.hotwords-chart__count {
  font-size: 0.78rem;
  color: var(--color-muted, #7a756b);
}

.hotwords-chart__empty {
  display: grid;
  place-items: center;
  min-height: 120px;
  border: 1px dashed var(--color-border, #e5ded3);
  border-radius: 12px;
  color: var(--color-muted, #7a756b);
  font-size: 0.88rem;
}

.hotwords-chart__canvas {
  width: 100%;
  height: auto;
  border-radius: 12px;
  border: 1px solid var(--color-border, #e5ded3);
  cursor: pointer;
}

.hotwords-chart__tooltip {
  position: absolute;
  z-index: 10;
  padding: 6px 12px;
  border-radius: 8px;
  background: var(--color-text, #1f1f1a);
  color: var(--color-card, #fff);
  font-size: 0.8rem;
  pointer-events: none;
  display: grid;
  gap: 2px;
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.18);
  white-space: nowrap;
  transform: translateX(-50%);
  animation: hotwords-tooltip-in 0.22s ease;
}

.hotwords-chart__tooltip strong {
  font-size: 0.88rem;
}

@keyframes hotwords-tooltip-in {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}
</style>
