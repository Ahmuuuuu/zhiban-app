<!--
  SimpleChart.vue — light-weight SVG chart primitives for dashboard use.
  No external dependencies. Supports dark mode via CSS variables.

  Usage:
    <SimpleChart type="donut" :data="donutData" :size="180" />
    <SimpleChart type="bar" :data="barData" :width="400" :height="200" />
    <SimpleChart type="hbar" :data="hbarData" :width="320" :height="180" />

  Data shape:
    donut:  [{ label, value, color? }]
    bar:    [{ label, value, color? }]
    hbar:   [{ label, value, color? }]
-->
<template>
  <div class="simple-chart" :class="`simple-chart--${type}`">
    <svg
      v-if="type === 'donut'"
      :viewBox="`0 0 ${size} ${size}`"
      :width="size"
      :height="size"
      role="img"
      :aria-label="`Donut chart: ${data.map(d => d.label).join(', ')}`"
    >
      <g :transform="`translate(${c},${c})`">
        <template v-for="(arc, i) in donutArcs" :key="i">
          <path
            :d="arc.d"
            :fill="arc.color"
            :opacity="0.82"
            stroke="var(--color-card, #fff)"
            stroke-width="1.5"
            @mouseenter="hoverIndex = i"
            @mouseleave="hoverIndex = -1"
            :style="{ transform: hoverIndex === i ? 'scale(1.05)' : '', transformOrigin: '0 0', transition: 'transform 0.2s ease' }"
          />
        </template>
        <circle :r="innerR" fill="var(--color-card, #fff)" stroke="none" />
        <text text-anchor="middle" dy="0.35em" class="donut-center-text">
          <tspan class="donut-center-value">{{ centerDisplayValue }}</tspan>
          <tspan v-if="centerDisplayLabel" class="donut-center-unit" x="0" dy="16">{{ centerDisplayLabel }}</tspan>
        </text>
      </g>
    </svg>

    <svg
      v-else-if="type === 'bar'"
      :viewBox="`0 0 ${width} ${height}`"
      :width="width"
      :height="height"
      role="img"
      :aria-label="`Bar chart: ${data.map(d => d.label).join(', ')}`"
    >
      <defs>
        <linearGradient
          v-for="(bar, i) in barRects" :key="'grad-'+i"
          :id="`bar-grad-${i}`"
          x1="0" y1="0" x2="0" y2="1"
        >
          <stop offset="0%" :stop-color="bar.color" stop-opacity="0.92" />
          <stop offset="100%" :stop-color="bar.color" stop-opacity="0.55" />
        </linearGradient>
      </defs>
      <template v-for="(tick, i) in barTicks" :key="'tick-'+i">
        <line :x1="padL" :y1="tick.y" :x2="width - padR" :y2="tick.y" class="chart-grid-line" />
        <text :x="padL - 6" :y="tick.y + 3" text-anchor="end" class="chart-tick-text">{{ tick.label }}</text>
      </template>

      <template v-for="(bar, i) in barRects" :key="'bar-'+i">
        <rect
          :x="bar.x"
          :y="bar.y"
          :width="bar.w"
          :height="bar.h"
          :rx="bar.w < 20 ? bar.w/3 : 5"
          :fill="`url(#bar-grad-${i})`"
          :opacity="hoverIndex === i ? 1 : 0.88"
          @mouseenter="hoverIndex = i"
          @mouseleave="hoverIndex = -1"
          class="chart-bar-rect"
        />
        <text
          v-if="bar.h > 16"
          :x="bar.x + bar.w / 2"
          :y="bar.y + 14"
          text-anchor="middle"
          class="chart-bar-label"
        >{{ bar.value }}</text>
        <text
          v-for="(char, ci) in bar.label.split('')"
          :key="ci"
          :x="bar.x + bar.w / 2"
          :y="height - 2 + ci * 11"
          text-anchor="middle"
          class="chart-bar-name"
        >{{ char }}</text>
      </template>
    </svg>

    <svg
      v-else-if="type === 'hbar'"
      :viewBox="`0 0 ${width} ${height}`"
      :width="width"
      :height="height"
      role="img"
      :aria-label="`Horizontal bar chart: ${data.map(d => d.label).join(', ')}`"
    >
      <defs>
        <linearGradient
          v-for="(bar, i) in hbarRects" :key="'hbgrad-'+i"
          :id="`hbar-grad-${i}`"
          x1="0" y1="0" x2="1" y2="0"
        >
          <stop offset="0%" :stop-color="bar.color" stop-opacity="0.92" />
          <stop offset="100%" :stop-color="bar.color" stop-opacity="0.45" />
        </linearGradient>
      </defs>
      <template v-for="(bar, i) in hbarRects" :key="'hbar-'+i">
        <rect
          :x="bar.x"
          :y="bar.y"
          :width="bar.w"
          :height="bar.h"
          :rx="4"
          :fill="`url(#hbar-grad-${i})`"
          :opacity="hoverIndex === i ? 1 : 0.85"
          @mouseenter="hoverIndex = i"
          @mouseleave="hoverIndex = -1"
          class="chart-bar-rect"
        />
        <text :x="bar.x + 6" :y="bar.y + bar.h / 2 + 4" class="chart-bar-label">{{ bar.label }}</text>
        <text :x="bar.x + bar.w - 6" :y="bar.y + bar.h / 2 + 4" text-anchor="end" class="chart-bar-name">{{ bar.value }}</text>
      </template>
    </svg>

    <div v-if="showLegend && data.length" class="simple-chart__legend">
      <span
        v-for="(d, i) in data"
        :key="i"
        :style="{
          '--legend-color': d.color || PALETTE[i % PALETTE.length],
          fontWeight: hoverIndex === i ? 800 : 400
        }"
        @mouseenter="hoverIndex = i"
        @mouseleave="hoverIndex = -1"
      >{{ d.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const PALETTE = [
  '#2563eb', '#0891b2', '#059669', '#7c3aed',
  '#db2777', '#ea580c', '#ca8a04', '#4f46e5',
  '#0d9488', '#b91c1c', '#854d0e', '#1d4ed8'
]

// Vibrant mode palette — richer saturation
const PALETTE_VIBRANT = [
  '#2563eb', '#0e7490', '#16a34a', '#7c3aed',
  '#e11d48', '#f97316', '#eab308', '#6366f1',
  '#14b8a6', '#dc2626', '#a855f7', '#0ea5e9'
]

const props = defineProps({
  type: { type: String, default: 'bar', validator: v => ['bar', 'hbar', 'donut'].includes(v) },
  data: { type: Array, default: () => [] },
  size: { type: Number, default: 180 },     // for donut
  width: { type: Number, default: 400 },     // for bar/hbar
  height: { type: Number, default: 200 },
  unit: { type: String, default: '' },
  centerValue: { type: [String, Number], default: '' },
  centerLabel: { type: String, default: '' },
  showLegend: { type: Boolean, default: false }
})

const hoverIndex = ref(-1)

// ---- donut ----
const c = computed(() => props.size / 2)
const innerR = computed(() => props.size * 0.3)

const total = computed(() => props.data.reduce((s, d) => s + (Number(d.value) || 0), 0))
const centerDisplayValue = computed(() => props.centerValue !== '' ? props.centerValue : total.value)
const centerDisplayLabel = computed(() => props.centerLabel || props.unit)

function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = (angleDeg - 90) * Math.PI / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const large = endAngle - startAngle > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y} L ${cx} ${cy} Z`
}

const donutArcs = computed(() => {
  const t = total.value || 1
  const outer = props.size * 0.42
  let angle = 0
  return props.data.map((d, i) => {
    const slice = (Number(d.value) || 0) / t * 360
    const start = angle
    const end = angle + slice
    angle = end
    return {
      d: describeArc(0, 0, outer, start, end),
      color: d.color || PALETTE[i % PALETTE.length]
    }
  })
})

// ---- bar ----
const padL = 44
const padR = 16
const barAreaH = computed(() => props.height - 28)
const maxVal = computed(() => Math.max(1, ...props.data.map(d => Number(d.value) || 0)))
const barCount = computed(() => Math.max(1, props.data.length))
const barGap = 10
const barTotalW = computed(() => props.width - padL - padR - (barCount.value - 1) * barGap)
const barW = computed(() => Math.max(8, Math.min(60, barTotalW.value / barCount.value)))

const barTicks = computed(() => {
  const max = maxVal.value
  if (max <= 0) return []
  // Find a nice step
  const roughStep = max / 4
  const magnitude = Math.pow(10, Math.floor(Math.log10(roughStep)))
  const normalized = roughStep / magnitude
  let step
  if (normalized <= 1.5) step = magnitude
  else if (normalized <= 3) step = 2 * magnitude
  else if (normalized <= 7) step = 5 * magnitude
  else step = 10 * magnitude

  const ticks = []
  for (let v = 0; v <= max + step * 0.5; v += step) {
    ticks.push({
      label: v >= 100 ? Math.round(v) : v,
      y: props.height - 24 - (v / max) * barAreaH.value
    })
  }
  return ticks
})

const barRects = computed(() => {
  const max = maxVal.value
  return props.data.map((d, i) => {
    const x = padL + i * (barW.value + barGap)
    const h = Math.max(2, (Number(d.value) || 0) / max * barAreaH.value)
    return {
      x, y: props.height - 24 - h, w: barW.value, h,
      label: d.label, value: d.value,
      color: d.color || PALETTE[i % PALETTE.length]
    }
  })
})

// ---- hbar ----
const hpadL = 80
const hpadR = 50
const hbarGap = 6
const hbarH = computed(() => {
  const count = props.data.length || 1
  return Math.max(14, Math.min(30, (props.height - (count - 1) * hbarGap) / count))
})
const hmaxVal = computed(() => Math.max(1, ...props.data.map(d => Number(d.value) || 0)))
const hbarAreaW = computed(() => props.width - hpadL - hpadR)

const hbarRects = computed(() => {
  const max = hmaxVal.value
  return props.data.map((d, i) => {
    const y = i * (hbarH.value + hbarGap) + 4
    const w = Math.max(8, (Number(d.value) || 0) / max * hbarAreaW.value)
    return {
      x: hpadL, y, w, h: hbarH.value,
      label: d.label, value: d.value,
      color: d.color || PALETTE[i % PALETTE.length]
    }
  })
})
</script>

<style scoped>
.simple-chart {
  width: 100%;
  display: grid;
  place-items: center;
  gap: 8px;
}

.simple-chart svg {
  max-width: 100%;
  height: auto;
  overflow: visible;
}

.chart-grid-line {
  stroke: color-mix(in srgb, var(--color-border, #e5ded3) 60%, transparent);
  stroke-width: 0.8;
}

.chart-tick-text {
  fill: var(--color-muted, #7a756b);
  font-size: 10px;
}

.donut-center-text {
  font-size: 18px;
  font-weight: 800;
  fill: var(--color-text-heading, #143761);
}

.donut-center-unit {
  font-size: 9px;
  font-weight: 600;
  fill: var(--color-muted, #7a756b);
}

.chart-bar-rect {
  transition: opacity 0.22s ease, filter 0.22s ease;
  cursor: pointer;
}

.chart-bar-rect:hover {
  filter: brightness(1.08) drop-shadow(0 2px 6px rgba(0,0,0,0.12));
}

.chart-bar-label {
  fill: #fff;
  font-size: 9px;
  font-weight: 700;
  pointer-events: none;
}

.chart-bar-name {
  fill: var(--color-muted, #7a756b);
  font-size: 9px;
  font-weight: 600;
  pointer-events: none;
}

.simple-chart__legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px 14px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-muted, #7a756b);
}

.simple-chart__legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  transition: font-weight 0.15s;
}

.simple-chart__legend span::before {
  content: "";
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  background: var(--legend-color);
}
</style>
