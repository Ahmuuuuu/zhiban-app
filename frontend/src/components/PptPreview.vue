<template>
  <section v-if="localSlides.length" class="ppt-preview">
    <PresentationToolbar
      :current-index="activeIndex"
      :total="localSlides.length"
      :title="title"
      :editable="editable"
      v-model:editing="editing"
      :exporting="exporting"
      :annotatable="annotatable"
      :annotation-tool="annotationTool"
      :highlight-colors="highlightColors"
      v-model:active-highlight-color="activeHighlightColor"
      v-model:style-source="styleSource"
      :can-undo="canUndo"
      :can-redo="canRedo"
      @previous="goPrevious"
      @next="goNext"
      @toggle-tool="toggleAnnotationTool"
      @undo="undoEdit"
      @redo="redoEdit"
      @advanced-edit="emitAdvancedEdit"
      @export="emitExport"
    />

    <PptSlide
      :slide="currentSlide"
      :title="title"
      :editing="editing"
      :annotatable="annotatable"
      :annotation-tool="annotationTool"
      :active-highlight-color="activeHighlightColor"
      :style-source="styleSource"
      :annotations="currentSlideAnnotations"
      :slide-index="activeIndex"
      :theme-id="themeId"
      @update-field="updateSlideField"
      @select-text="handleTextSelection"
      @open-annotation="openAnnotation"
    />

    <div class="ppt-controls">
      <div class="ppt-dots">
        <button
          v-for="(slide, index) in localSlides"
          :key="slide.index ?? index"
          type="button"
          :class="{ active: index === activeIndex }"
          :aria-label="`slide ${index + 1}`"
          @click="selectSlide(index)"
        ></button>
      </div>
    </div>

    <div
      v-if="annotationEditor.visible"
      class="ppt-annotation-popover"
      :style="{ left: `${annotationEditor.x}px`, top: `${annotationEditor.y}px` }"
    >
      <strong>{{ annotationEditor.mode === 'edit' ? '&#x7F16;&#x8F91;&#x7B14;&#x8BB0;' : '&#x6DFB;&#x52A0;&#x6CE8;&#x91CA;' }}</strong>
      <p>{{ annotationEditor.selectedText }}</p>
      <textarea v-model.trim="annotationEditor.note" rows="3" placeholder="&#x5199;&#x4E0B;&#x6CE8;&#x91CA;"></textarea>
      <div class="ppt-annotation-popover__actions">
        <button type="button" @click="closeAnnotationEditor">&#x53D6;&#x6D88;</button>
        <button
          v-if="annotationEditor.mode === 'edit'"
          type="button"
          class="danger"
          @click="removeAnnotation"
        >&#x5220;&#x9664;</button>
        <button type="button" class="primary" @click="saveAnnotation">&#x4FDD;&#x5B58;</button>
      </div>
    </div>

    <aside v-if="currentSlideAnnotations.length" class="ppt-annotation-panel">
      <h4>&#x672C;&#x9875;&#x7B14;&#x8BB0;</h4>
      <button
        v-for="annotation in currentSlideAnnotations"
        :key="annotation.id"
        type="button"
        @click="openAnnotation(annotation)"
      >
        <mark>{{ annotation.selected_text || annotation.selectedText }}</mark>
        <span>{{ annotation.note || annotation.note_text || '&#x8367;&#x5149;&#x6807;&#x8BB0;' }}</span>
      </button>
    </aside>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import PptSlide from './ppt_video/ppt/PptSlide.vue'
import PresentationToolbar from './ppt_video/ppt/PresentationToolbar.vue'
import 'katex/dist/katex.min.css'

const props = defineProps({
  slides: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: ''
  },
  editable: {
    type: Boolean,
    default: true
  },
  exporting: {
    type: Boolean,
    default: false
  },
  annotatable: {
    type: Boolean,
    default: false
  },
  annotations: {
    type: Array,
    default: () => []
  },
  themeId: {
    type: String,
    default: ''
  },
  followLatest: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:slides', 'change', 'export-pptx', 'advanced-edit', 'create-note', 'update-note', 'delete-note'])

const activeIndex = ref(0)
const editing = ref(false)
const annotationTool = ref('')
const activeHighlightColor = ref('#ffe159')
const styleSource = ref('custom')
const localSlides = ref([])
const undoStack = ref([])
const redoStack = ref([])
const skipNextSlideSync = ref(false)
const userSelectedSlide = ref(false)
const annotationEditor = reactive({
  visible: false,
  mode: 'create',
  id: '',
  x: 0,
  y: 0,
  selectedText: '',
  note: '',
  position: null
})

const highlightColors = [
  { value: '#ffe159', label: 'yellow' },
  { value: '#8ee6a8', label: 'green' },
  { value: '#86d9ff', label: 'blue' },
  { value: '#ffb3d1', label: 'pink' },
  { value: '#c8b6ff', label: 'purple' }
]

const layoutLabels = {
  title_cover: '封面',
  concept_visual: '图文讲解',
  process_steps: '流程步骤',
  comparison: '对比分析',
  formula_focus: '公式推导',
  content_cards: '重点卡片'
}

const layoutLabel = layout => layoutLabels[layout] || '内容讲解'

const visualLabel = visual => {
  const type = visual?.type || 'diagram'
  const labels = {
    diagram: '图解',
    timeline: '时间线',
    comparison: '对比图',
    formula: '公式板',
    map: '地图'
  }
  return labels[type] || '视觉辅助'
}

const visualGlyph = visual => {
  const glyphs = {
    timeline: '1-2-3',
    comparison: 'A/B',
    formula: 'f(x)',
    map: 'MAP',
    diagram: 'VIS'
  }
  return glyphs[visual?.type || 'diagram'] || 'VIS'
}

const themePalettes = {
  academic_blue: ['#163f8f', '#2f80ed', '#44c2ff', '#f7fbff'],
  science_green: ['#11695f', '#28b487', '#a7f3d0', '#f6fffb'],
  warm_case: ['#93491f', '#e86c00', '#ffd166', '#fff8ed'],
  graphite: ['#17202a', '#566573', '#aeb6bf', '#f7f9fb'],
  aurora: ['#0f766e', '#22d3ee', '#a78bfa', '#f0fdfa'],
  coral: ['#9f1239', '#fb7185', '#fbbf24', '#fff1f2'],
  violet: ['#4c1d95', '#8b5cf6', '#38bdf8', '#f5f3ff'],
  sunlit: ['#854d0e', '#f59e0b', '#84cc16', '#fffbeb']
}

const slidePalette = slide => {
  if (Array.isArray(slide?.palette) && slide.palette.length >= 4) return slide.palette
  return themePalettes[slide?.theme] || themePalettes.academic_blue
}

const svgUrl = svg => `url("data:image/svg+xml,${encodeURIComponent(svg)}")`

const cleanDisplayText = value => String(value || '')
  .replace(/<!--[\s\S]*?-->/g, ' ')
  .replace(/<\/?[^>\n]+>/g, ' ')
  .replace(/<[^>\n]*$/g, ' ')
  .replace(/&nbsp;/gi, ' ')
  .replace(/&amp;/gi, '&')
  .replace(/&lt;/gi, '<')
  .replace(/&gt;/gi, '>')
  .replace(/[ \t]+\n/g, '\n')
  .replace(/\n{3,}/g, '\n\n')
  .trim()

const compactDisplayText = (value, limit = 260) => {
  const text = cleanDisplayText(value).replace(/\s+/g, ' ').trim()
  if (text.length <= limit) return text
  // 避免截断在 $...$ 或 $$...$$ 内部，破坏 KaTeX 渲染
  let cut = limit - 1
  const dollars = []
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '$') {
      if (text[i + 1] === '$') { dollars.push({ pos: i, display: true }); i++ }
      else { dollars.push({ pos: i, display: false }) }
    }
  }
  // 找到 cut 位置落在哪个 $ 区间内
  let inPair = false
  for (let j = 0; j + 1 < dollars.length; j += 2) {
    const open = dollars[j].pos
    const close = dollars[j + 1] ? dollars[j + 1].pos + (dollars[j + 1].display ? 1 : 0) : text.length
    if (cut > open && cut < close) {
      // cut 在 $...$ 内部 → 退回到 $ 之前
      cut = open - 1
      inPair = true
      break
    }
  }
  // 如果退回到 $ 之前导致太短（< 一半），则包含完整的公式
  if (inPair && cut < limit * 0.4) {
    for (let j = 0; j + 1 < dollars.length; j += 2) {
      const close = dollars[j + 1] ? dollars[j + 1].pos + (dollars[j + 1].display ? 1 : 0) : text.length
      if (close > limit * 0.5 && close < limit * 1.3) {
        cut = close
        break
      }
    }
  }
  return text.slice(0, cut).replace(/\s+$/, '') + '...'
}

const displayBlockText = (value, limit = 200) => compactDisplayText(value, limit)

const visualSvgData = slide => {
  const [primary, secondary, accent, paper] = slidePalette(slide)
  const type = slide?.visual?.type || 'diagram'
  const label = visualGlyph(slide?.visual)
  const motif = {
    timeline: `<path d="M92 210H628" stroke="${paper}" stroke-width="12" stroke-linecap="round" opacity=".85"/><circle cx="145" cy="210" r="34" fill="${accent}"/><circle cx="300" cy="210" r="34" fill="${paper}"/><circle cx="455" cy="210" r="34" fill="${accent}"/><circle cx="610" cy="210" r="34" fill="${paper}"/>`,
    comparison: `<rect x="86" y="86" width="240" height="250" rx="28" fill="${paper}" opacity=".86"/><rect x="394" y="86" width="240" height="250" rx="28" fill="${accent}" opacity=".82"/><path d="M360 70v290" stroke="${paper}" stroke-width="10" opacity=".72"/>`,
    formula: `<path d="M80 230C160 90 260 350 360 210S550 90 640 235" fill="none" stroke="${paper}" stroke-width="14" stroke-linecap="round"/><rect x="120" y="84" width="480" height="72" rx="24" fill="${accent}" opacity=".78"/>`,
    map: `<path d="M180 92c110-34 167 46 246 19 96-33 161 45 135 130-22 72-109 55-177 91-94 49-218 6-238-78-15-61-40-139 34-162z" fill="${paper}" opacity=".82"/><circle cx="440" cy="218" r="28" fill="${accent}"/>`,
    diagram: `<circle cx="220" cy="210" r="104" fill="${paper}" opacity=".82"/><rect x="350" y="112" width="210" height="196" rx="36" fill="${accent}" opacity=".78"/><path d="M300 210h90" stroke="${paper}" stroke-width="14" stroke-linecap="round"/>`
  }[type] || ''
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 430"><defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="${primary}"/><stop offset=".58" stop-color="${secondary}"/><stop offset="1" stop-color="${accent}"/></linearGradient></defs><rect width="720" height="430" rx="36" fill="url(#g)"/><circle cx="620" cy="60" r="140" fill="${paper}" opacity=".18"/><circle cx="72" cy="380" r="170" fill="${paper}" opacity=".12"/>${motif}<text x="360" y="392" text-anchor="middle" font-family="Arial, sans-serif" font-size="38" font-weight="800" fill="${paper}" opacity=".94">${label}</text></svg>`
}

const visualImageStyle = slide => ({
  backgroundImage: svgUrl(visualSvgData(slide))
})

const slideVisualStyle = slide => {
  const [primary, secondary, accent, paper] = slidePalette(slide)
  const bg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720"><defs><linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop stop-color="${paper}"/><stop offset=".56" stop-color="${paper}"/><stop offset="1" stop-color="${accent}" stop-opacity=".42"/></linearGradient></defs><rect width="1200" height="720" fill="url(#bg)"/><path d="M0 0H1200V95C930 136 716 46 457 92 269 125 123 174 0 136Z" fill="${primary}" opacity=".94"/><path d="M810 0c156 44 262 132 390 92V0Z" fill="${secondary}" opacity=".9"/><circle cx="1030" cy="154" r="118" fill="${accent}" opacity=".24"/><circle cx="930" cy="210" r="76" fill="${secondary}" opacity=".18"/></svg>`
  return {
    '--slide-primary': primary,
    '--slide-secondary': secondary,
    '--slide-accent': accent,
    '--slide-paper': paper,
    backgroundImage: svgUrl(bg)
  }
}

const splitTextBlocks = text => cleanDisplayText(text)
  .split(/\r?\n|[;；]/)
  .map(line => line.replace(/^[-*•\s]+/, '').trim())
  .filter(Boolean)

const chooseLayout = (slide, index) => {
  const text = `${slide?.title || ''}\n${slide?.text || slide?.content || ''}`
  if (index === 0) return 'title_cover'
  if (/对比|比较|区别|vs\.?|差异/i.test(text)) return 'comparison'
  if (/步骤|流程|过程|阶段|路径|step|process/i.test(text)) return 'process_steps'
  if (/\$[^$]+\$|=|\\sum|\\frac|\^|_/.test(text)) return 'formula_focus'
  if (splitTextBlocks(slide?.text || slide?.content).length >= 5) return 'content_cards'
  return 'concept_visual'
}

const chooseTheme = (slide, index) => {
  const text = `${slide?.title || ''}\n${slide?.text || slide?.content || ''}`
  if (/案例|场景|case|story/i.test(text)) return 'warm_case'
  if (/生物|化学|物理|实验|细胞|science/i.test(text)) return 'science_green'
  return ['academic_blue', 'aurora', 'coral', 'violet', 'sunlit', 'science_green', 'warm_case', 'graphite'][index % 8]
}

const normalizeBlocks = slide => {
  const blocks = Array.isArray(slide?.blocks) ? slide.blocks : []
  if (blocks.length) {
    return blocks
      .map(block => ({
        type: block?.type || 'key_point',
        text: cleanDisplayText(block?.text || block?.content)
      }))
      .filter(block => block.text)
  }
  return splitTextBlocks(slide?.text || slide?.content).slice(0, 8).map(text => ({ type: 'key_point', text }))
}

const normalizeSlide = (slide, index) => {
  const text = cleanDisplayText(slide?.text || slide?.content || '')
  const layout = slide?.layout || chooseLayout(slide, index)
  const visual = typeof slide?.visual === 'object' && slide.visual
    ? slide.visual
    : { type: layout === 'process_steps' ? 'timeline' : layout === 'formula_focus' ? 'formula' : layout === 'comparison' ? 'comparison' : 'diagram', query: slide?.visual_hint || slide?.title || '', caption: '' }

  return {
    ...slide,
    index: Number(slide?.index ?? index),
    title: compactDisplayText(slide?.title || '', 90),
    text,
    content: text,
    notes: cleanDisplayText(slide?.notes || slide?.speaker_notes || ''),
    speaker_notes: cleanDisplayText(slide?.speaker_notes || slide?.notes || ''),
    layout,
    theme: slide?.theme || chooseTheme(slide, index),
    visual: {
      ...visual,
      query: compactDisplayText(visual?.query || slide?.title || '', 90),
      caption: compactDisplayText(visual?.caption || '', 120)
    },
    blocks: normalizeBlocks({ ...slide, text })
  }
}

const syncLocalSlides = slides => {
  localSlides.value = (Array.isArray(slides) ? slides : []).map(normalizeSlide)
  if (activeIndex.value >= localSlides.value.length) {
    activeIndex.value = Math.max(localSlides.value.length - 1, 0)
  }
}

const currentSlide = computed(() => localSlides.value[activeIndex.value] || localSlides.value[0] || {})
const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)
const slideBlocks = computed(() => normalizeBlocks(currentSlide.value))
const firstBlockText = computed(() => slideBlocks.value[0]?.text || '')
const formulaText = computed(() => slideBlocks.value.find(block => /=|\$|\\sum|\\frac|\^|_/.test(block.text))?.text || firstBlockText.value)
const formulaBlocks = computed(() => slideBlocks.value.filter(block => block.text !== formulaText.value).slice(0, 5))

const currentSlideTextLength = computed(() => {
  const slide = currentSlide.value || {}
  return String(`${slide.title || ''}\n${slide.text || ''}\n${slide.notes || ''}`).length
})

const normalizePosition = annotation => {
  const raw = annotation?.position
  if (raw && typeof raw === 'object') return raw
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw)
    } catch {
      return {}
    }
  }
  return {}
}

const normalizedAnnotations = computed(() => props.annotations.map(annotation => ({
  ...annotation,
  id: annotation.id || annotation.annotation_id || annotation.annotationId || `${annotation.selected_text || annotation.selectedText}-${annotation.note}`,
  position: normalizePosition(annotation)
})))

const getAnnotationColor = annotation => annotation?.position?.color || '#ffe159'

const isNoteAnnotation = annotation => annotation?.position?.tool === 'note' || Boolean(annotation?.note || annotation?.note_text)

const annotationBackground = annotation => {
  if (isNoteAnnotation(annotation)) return 'rgba(237, 249, 252, 0.66)'
  const color = getAnnotationColor(annotation)
  return `linear-gradient(transparent 18%, ${color} 18%, ${color} 88%, transparent 88%)`
}

const toggleAnnotationTool = tool => {
  annotationTool.value = annotationTool.value === tool ? '' : tool
}

const currentSlideAnnotations = computed(() => normalizedAnnotations.value
  .filter(annotation => annotation.position?.kind === 'ppt')
  .filter(annotation => Number(annotation.position.slideIndex) === activeIndex.value)
  .filter(annotation => Number.isFinite(Number(annotation.position.start)) && Number.isFinite(Number(annotation.position.end)))
  .sort((a, b) => Number(a.position.start) - Number(b.position.start)))

const slideSegments = computed(() => {
  const text = cleanDisplayText(currentSlide.value.text || '')
  const result = []
  let cursor = 0

  for (const annotation of currentSlideAnnotations.value) {
    const start = Math.max(0, Math.min(text.length, Number(annotation.position.start)))
    const end = Math.max(start, Math.min(text.length, Number(annotation.position.end)))
    if (start < cursor || end <= start) continue
    if (start > cursor) result.push({ text: text.slice(cursor, start) })
    result.push({ text: text.slice(start, end), annotation })
    cursor = end
  }

  if (cursor < text.length) result.push({ text: text.slice(cursor) })
  return result.length ? result : [{ text }]
})

const cloneSlides = slides => JSON.parse(JSON.stringify(slides || []))

const publishSlides = () => {
  const slides = localSlides.value.map(slide => ({
    ...slide,
    content: slide.text,
    speaker_notes: slide.notes
  }))
  skipNextSlideSync.value = true
  emit('update:slides', slides)
  emit('change', slides)
}

const currentExportSlides = () => localSlides.value.map(slide => ({
  ...slide,
  style_source: styleSource.value,
  content: slide.text,
  speaker_notes: slide.notes
}))

const clampActiveIndex = value => {
  const max = Math.max(localSlides.value.length - 1, 0)
  return Math.min(Math.max(Number(value) || 0, 0), max)
}

const selectSlide = index => {
  userSelectedSlide.value = true
  activeIndex.value = clampActiveIndex(index)
}

const goPrevious = () => {
  userSelectedSlide.value = true
  activeIndex.value = clampActiveIndex(activeIndex.value - 1)
}

const goNext = () => {
  userSelectedSlide.value = true
  activeIndex.value = clampActiveIndex(activeIndex.value + 1)
}

const emitExport = () => {
  const slides = currentExportSlides()
  emit('update:slides', slides)
  emit('export-pptx', slides)
}

const emitAdvancedEdit = () => {
  const slides = currentExportSlides()
  emit('update:slides', slides)
  emit('advanced-edit', slides)
}

const updateSlideField = (field, value) => {
  const slide = localSlides.value[activeIndex.value]
  if (!slide) return
  if (slide[field] === value) return

  undoStack.value.push({
    slides: cloneSlides(localSlides.value),
    activeIndex: activeIndex.value
  })
  if (undoStack.value.length > 60) undoStack.value.shift()
  redoStack.value = []

  localSlides.value[activeIndex.value] = {
    ...slide,
    [field]: value,
    ...(field === 'text' ? { content: value } : {}),
    ...(field === 'notes' ? { speaker_notes: value } : {})
  }
  publishSlides()
}

const restoreHistoryState = state => {
  if (!state) return
  localSlides.value = cloneSlides(state.slides).map(normalizeSlide)
  activeIndex.value = Math.min(Math.max(Number(state.activeIndex || 0), 0), Math.max(localSlides.value.length - 1, 0))
  publishSlides()
}

const undoEdit = () => {
  if (!canUndo.value) return
  redoStack.value.push({
    slides: cloneSlides(localSlides.value),
    activeIndex: activeIndex.value
  })
  restoreHistoryState(undoStack.value.pop())
}

const redoEdit = () => {
  if (!canRedo.value) return
  undoStack.value.push({
    slides: cloneSlides(localSlides.value),
    activeIndex: activeIndex.value
  })
  restoreHistoryState(redoStack.value.pop())
}

const closeAnnotationEditor = () => {
  annotationEditor.visible = false
}

const handleTextSelection = ({ selectedText, rect, position }) => {
  if (!props.annotatable || !annotationTool.value || editing.value || !selectedText || !position) return
  const normalizedPosition = {
    ...position,
    start: Math.min(Number(position.start), Number(position.end)),
    end: Math.max(Number(position.start), Number(position.end)),
    slideIndex: activeIndex.value,
    tool: annotationTool.value,
    color: activeHighlightColor.value
  }

  if (annotationTool.value === 'highlight') {
    emit('create-note', {
      selected_text: selectedText,
      note: '',
      note_text: '',
      position: normalizedPosition
    })
    window.getSelection()?.removeAllRanges()
    return
  }

  Object.assign(annotationEditor, {
    visible: true,
    mode: 'create',
    id: '',
    x: Math.min(rect.left + window.scrollX, window.innerWidth - 340),
    y: rect.bottom + window.scrollY + 8,
    selectedText,
    note: '',
    position: normalizedPosition
  })
}

const openAnnotation = payload => {
  const annotation = payload?.annotation || payload
  const rect = payload?.rect
  Object.assign(annotationEditor, {
    visible: true,
    mode: 'edit',
    id: annotation.id,
    x: rect ? Math.min(rect.left + window.scrollX, window.innerWidth - 340) : window.innerWidth / 2 - 160,
    y: rect ? rect.bottom + window.scrollY + 8 : window.scrollY + 120,
    selectedText: annotation.selected_text || annotation.selectedText || '',
    note: annotation.note || annotation.note_text || '',
    position: annotation.position
  })
}

const saveAnnotation = () => {
  const payload = {
    selected_text: annotationEditor.selectedText,
    note: annotationEditor.note,
    note_text: annotationEditor.note,
    position: {
      ...(annotationEditor.position || {}),
      tool: 'note'
    }
  }

  if (annotationEditor.mode === 'edit') {
    emit('update-note', annotationEditor.id, payload)
  } else {
    emit('create-note', payload)
  }
  closeAnnotationEditor()
}

const removeAnnotation = () => {
  if (annotationEditor.id) emit('delete-note', annotationEditor.id)
  closeAnnotationEditor()
}

watch(
  () => props.slides,
  slides => {
    if (skipNextSlideSync.value) {
      skipNextSlideSync.value = false
      return
    }
    const previousLength = localSlides.value.length
    syncLocalSlides(slides)
    if (props.followLatest && !userSelectedSlide.value) {
      activeIndex.value = Math.max(localSlides.value.length - 1, 0)
    } else if (previousLength !== localSlides.value.length) {
      activeIndex.value = Math.min(activeIndex.value, Math.max(localSlides.value.length - 1, 0))
    }
    undoStack.value = []
    redoStack.value = []
  },
  { immediate: true }
)

watch(
  () => props.followLatest,
  value => {
    if (!value) return
    userSelectedSlide.value = false
    activeIndex.value = Math.max(localSlides.value.length - 1, 0)
  },
  { immediate: true }
)

watch(
  () => props.annotatable,
  value => {
    annotationTool.value = value ? 'highlight' : ''
  },
  { immediate: true }
)

watch(
  () => props.editable,
  value => {
    if (!value) editing.value = false
  },
  { immediate: true }
)
</script>

<style>
.ppt-preview {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  align-items: stretch;
  gap: 8px;
  width: 100%;
  height: 100%;
  max-height: calc(100vh - 112px);
  min-height: 0;
  overflow: hidden;
}

.ppt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 34px;
}

.ppt-toolbar__title {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.ppt-toolbar__title strong {
  max-width: 420px;
  overflow: hidden;
  color: #163f8f;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ppt-toolbar__actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.edit-toggle,
.highlight-toggle,
.note-toggle,
.nav-btn,
.history-btn,
.export-btn {
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 6px;
  background: #fff;
  color: #163f8f;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.nav-btn {
  width: 32px;
  padding: 0;
}

.nav-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.edit-toggle {
  border-color: rgba(22, 63, 143, 0.9);
}

.highlight-toggle {
  border-color: rgba(214, 176, 38, 0.62);
  background: rgba(255, 225, 89, 0.22);
  color: #8a6a00;
}

.note-toggle {
  border-color: rgba(95, 143, 195, 0.62);
  background: rgba(237, 249, 252, 0.82);
  color: #163f8f;
}

.highlight-toggle.active {
  border-color: rgba(214, 176, 38, 0.86);
  background: #ffe159;
  color: #4f3b00;
}

.note-toggle.active {
  border-color: rgba(22, 63, 143, 0.9);
  background: #163f8f;
  color: #ffffff;
}

.highlight-palette {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.highlight-palette button {
  width: 24px;
  height: 24px;
  padding: 0;
  border: 2px solid rgba(22, 63, 143, 0.12);
  border-radius: 50%;
  cursor: pointer;
}

.highlight-palette button.active {
  border-color: #163f8f;
  box-shadow: 0 0 0 2px rgba(22, 63, 143, 0.12);
}

.export-btn {
  border-color: rgba(22, 63, 143, 0.9);
  background: #163f8f;
  color: #ffffff;
}

.export-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.history-btn {
  background: rgba(237, 249, 252, 0.72);
}

.history-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ppt-slide {
  position: relative;
  justify-self: center;
  align-self: center;
  width: auto;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  aspect-ratio: 16 / 9;
  min-height: 0;
  margin: 0 auto;
  padding: clamp(16px, 2.1vw, 30px);
  border: 1px solid rgba(22, 63, 143, 0.1);
  border-radius: 6px;
  background: #ffffff center / cover no-repeat;
  box-shadow: 0 10px 28px rgba(22, 63, 143, 0.12);
  display: flex;
  flex-direction: column;
  gap: clamp(8px, 1.4vw, 14px);
  overflow: hidden;
}

.ppt-slide > * {
  position: relative;
  z-index: 1;
}

.ppt-slide.theme-science_green {
  border-color: rgba(35, 132, 102, 0.22);
}

.ppt-slide.theme-warm_case {
  border-color: rgba(188, 110, 50, 0.22);
}

.ppt-slide.theme-graphite {
  border-color: rgba(23, 32, 42, 0.18);
}

.ppt-slide__kicker {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: rgba(95, 143, 195, 0.82);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0;
}

.ppt-slide__art {
  position: absolute;
  right: clamp(22px, 3vw, 42px);
  bottom: clamp(86px, 11vh, 128px);
  z-index: 0;
  width: min(28%, 280px);
  aspect-ratio: 1.68;
  border-radius: 8px;
  background-position: center;
  background-size: cover;
  opacity: 0.32;
  box-shadow: 0 18px 44px rgba(22, 63, 143, 0.2);
  pointer-events: none;
}

.ppt-slide__kicker span,
.ppt-slide__kicker small {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--slide-primary, #163f8f) 12%, #ffffff);
}

.ppt-slide__kicker small {
  color: rgba(31, 51, 86, 0.62);
}

.ppt-slide.editing {
  outline: 2px solid rgba(95, 143, 195, 0.36);
  outline-offset: 3px;
}

.ppt-slide__stage {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  align-content: stretch;
  gap: clamp(8px, 1.2vw, 14px);
}

.ppt-slide h3 {
  margin: 0;
  color: #163f8f;
  font-size: clamp(22px, 2.8vw, 38px);
  line-height: 1.16;
  text-align: center;
}

.ppt-slide__content {
  width: min(92%, 1040px);
  min-height: 0;
  max-height: 100%;
  margin: 0 auto;
  padding: 2px 8px 2px 0;
  overflow: hidden;
  color: rgba(22, 63, 143, 0.82);
  font-size: clamp(14px, 1.35vw, 19px);
  line-height: 1.48;
  white-space: pre-line;
  word-break: break-word;
}

.ppt-slide h3,
.visual-panel strong,
.visual-panel p,
.process-step span,
.comparison-card p,
.formula-points p,
.content-card-grid article p {
  overflow-wrap: anywhere;
}

.ppt-slide h3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.slide-rich-text {
  min-width: 0;
  max-height: 100%;
  padding-right: 6px;
  overflow: hidden;
  white-space: pre-line;
  display: -webkit-box;
  -webkit-line-clamp: 20;
  -webkit-box-orient: vertical;
}

.layout-grid {
  display: grid;
  gap: clamp(18px, 2.8vw, 32px);
  align-items: stretch;
  min-height: 0;
}

.layout-grid--visual {
  grid-template-columns: minmax(0, 1.08fr) minmax(280px, 0.92fr);
}

.visual-panel {
  min-height: 0;
  max-height: 100%;
  padding: clamp(10px, 1.5vw, 16px);
  border: 1px solid rgba(95, 143, 195, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  display: grid;
  align-content: center;
  gap: 14px;
  color: #1f3356;
  text-align: center;
  box-shadow: 0 10px 24px rgba(22, 63, 143, 0.1);
  overflow: hidden;
}

.visual-panel__image {
  width: 100%;
  min-height: 150px;
  margin: 0 auto;
  border-radius: 8px;
  background-position: center;
  background-size: cover;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.42);
}

.visual-panel strong {
  color: #163f8f;
  font-size: clamp(18px, 2vw, 25px);
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.visual-panel p {
  margin: 0;
  color: rgba(31, 51, 86, 0.7);
  font-size: clamp(14px, 1.4vw, 17px);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.process-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(230px, 100%), 1fr));
  grid-auto-rows: minmax(0, auto);
  gap: 12px;
  align-items: start;
  align-content: start;
  min-height: 0;
  height: 100%;
}

.process-step {
  position: relative;
  min-height: 0;
  padding: 36px 12px 14px;
  border: 1px solid rgba(95, 143, 195, 0.18);
  border-radius: 8px;
  background: #ffffff;
  color: rgba(31, 51, 86, 0.82);
  box-shadow: 0 12px 28px rgba(22, 63, 143, 0.09);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 100%;
}

.process-step b {
  position: absolute;
  top: -18px;
  left: 50%;
  width: 42px;
  height: 42px;
  transform: translateX(-50%);
  border-radius: 50%;
  background: var(--slide-secondary, #e86c00);
  color: #ffffff;
  display: grid;
  place-items: center;
  font-size: 18px;
}

.process-step span {
  display: block;
  font-size: clamp(13px, 1.25vw, 16px);
  line-height: 1.48;
  max-height: 100%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 10;
  -webkit-box-orient: vertical;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: clamp(18px, 2.5vw, 28px);
  min-height: 0;
  height: 100%;
}

.comparison-card {
  min-height: 0;
  padding: 16px;
  border: 1px solid rgba(95, 143, 195, 0.18);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 14px 34px rgba(22, 63, 143, 0.1);
  overflow: hidden;
}

.comparison-card b {
  display: inline-grid;
  place-items: center;
  width: 42px;
  height: 42px;
  margin-bottom: 14px;
  border-radius: 8px;
  background: var(--slide-primary, #163f8f);
  color: #ffffff;
}

.comparison-card--accent b {
  background: var(--slide-secondary, #e86c00);
}

.comparison-card p {
  margin: 0 0 12px;
  color: rgba(31, 51, 86, 0.82);
  font-size: clamp(14px, 1.35vw, 18px);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 6;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.formula-layout {
  display: grid;
  grid-template-rows: minmax(86px, auto) minmax(0, 1fr);
  gap: 14px;
  min-height: 0;
  height: 100%;
}

.formula-box {
  min-height: 0;
  max-height: min(28vh, 150px);
  padding: clamp(10px, 1.5vw, 18px);
  border-radius: 8px;
  background:
    linear-gradient(135deg, var(--slide-primary, #163f8f), var(--slide-secondary, #2f80ed));
  color: #ffffff;
  display: grid;
  place-items: center;
  font-size: clamp(18px, 2.4vw, 32px);
  font-weight: 900;
  line-height: 1.25;
  text-align: center;
  overflow: hidden;
}

.formula-box .katex-display {
  margin: 0;
  max-width: 100%;
  overflow: hidden;
}

.formula-box .katex {
  max-width: 100%;
  white-space: normal;
}

.formula-points {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
  grid-auto-rows: minmax(0, auto);
  gap: 12px;
  min-height: 0;
  align-content: start;
  overflow: hidden;
}

.formula-points p,
.content-card-grid article p {
  margin: 0;
}

.formula-points p {
  padding: 14px 16px;
  border-left: 4px solid var(--slide-secondary, #e86c00);
  border-radius: 8px;
  background: #ffffff;
  color: rgba(31, 51, 86, 0.82);
  font-size: clamp(14px, 1.3vw, 17px);
  line-height: 1.46;
  min-height: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 6;
  -webkit-box-orient: vertical;
}

.content-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
  grid-auto-rows: minmax(0, auto);
  gap: 10px;
  min-height: 0;
  height: 100%;
  align-content: start;
  overflow: hidden;
}

.content-card-grid article {
  padding: 10px;
  border: 1px solid rgba(95, 143, 195, 0.16);
  border-radius: 8px;
  background: #ffffff;
  color: rgba(31, 51, 86, 0.82);
  display: grid;
  gap: 6px;
  align-content: start;
  box-shadow: 0 12px 26px rgba(22, 63, 143, 0.08);
  overflow: hidden;
  min-height: 0;
}

.content-card-grid article span {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--slide-primary, #163f8f) 14%, #ffffff);
  color: var(--slide-primary, #163f8f);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 900;
  flex-shrink: 0;
}

.content-card-grid article p {
  font-size: clamp(14px, 1.3vw, 16px);
  line-height: 1.42;
  overflow-wrap: anywhere;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.content-card-grid article p .katex {
  font-size: 0.95em;
  max-width: 100%;
  overflow-x: auto;
  display: inline-block;
  vertical-align: middle;
}

.ppt-slide.is-dense h3 {
  font-size: clamp(20px, 2.6vw, 34px);
}

.ppt-slide.is-dense .ppt-slide__content {
  width: min(96%, 1080px);
  font-size: clamp(13px, 1.15vw, 17px);
  line-height: 1.4;
}

.ppt-slide.is-dense .process-strip {
  grid-template-columns: repeat(auto-fit, minmax(min(250px, 100%), 1fr));
}

.ppt-slide.is-dense .content-card-grid {
  grid-template-columns: repeat(auto-fit, minmax(min(300px, 100%), 1fr));
}

.ppt-slide.is-dense .formula-points p,
.ppt-slide.is-dense .content-card-grid article p {
  -webkit-line-clamp: 4;
}

.ppt-slide.is-very-dense h3 {
  font-size: clamp(20px, 2.5vw, 32px);
}

.ppt-slide.is-very-dense .ppt-slide__content {
  width: min(98%, 1120px);
  font-size: clamp(12px, 1vw, 15px);
  line-height: 1.38;
}

.ppt-slide.is-very-dense .formula-box {
  max-height: 96px;
  font-size: clamp(16px, 2vw, 26px);
}

.ppt-slide.is-very-dense .process-step span,
.ppt-slide.is-very-dense .content-card-grid article p,
.ppt-slide.is-very-dense .formula-points p {
  -webkit-line-clamp: 4;
}

.ppt-slide__content span,
.ppt-slide__content mark {
  display: inline;
}

.ppt-annotation-mark {
  position: relative;
  border-radius: 4px;
  padding: 0 0.05em;
  color: inherit;
  cursor: pointer;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}

.ppt-annotation-mark.has-note {
  border-bottom: 2px solid rgba(22, 63, 143, 0.42);
}

.ppt-annotation-mark.has-note::after {
  content: "✎";
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.05em;
  height: 1.05em;
  margin-left: 0.16em;
  border-radius: 50%;
  background: #163f8f;
  color: #ffffff;
  font-size: 0.62em;
  font-weight: 900;
  line-height: 1;
  vertical-align: super;
}

.ppt-annotation-popover {
  position: fixed;
  z-index: 10000;
  width: min(320px, calc(100vw - 28px));
  padding: 14px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(22, 63, 143, 0.2);
}

.ppt-annotation-popover strong {
  display: block;
  margin-bottom: 8px;
  color: #163f8f;
}

.ppt-annotation-popover p {
  max-height: 76px;
  margin: 0 0 10px;
  overflow: auto;
  color: #5d6f86;
  font-size: 13px;
  line-height: 1.5;
}

.ppt-annotation-popover textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid rgba(22, 63, 143, 0.18);
  border-radius: 8px;
  padding: 10px;
  color: #1f3356;
  font: inherit;
}

.ppt-annotation-popover__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.ppt-annotation-popover button,
.ppt-annotation-panel button {
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 8px;
  background: #ffffff;
  color: #163f8f;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.ppt-annotation-popover button {
  min-height: 32px;
  padding: 0 12px;
}

.ppt-annotation-popover .primary {
  border-color: #163f8f;
  background: #163f8f;
  color: #ffffff;
}

.ppt-annotation-popover .danger {
  color: #b64040;
}

.ppt-annotation-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgba(22, 63, 143, 0.12);
  border-radius: 8px;
  background: rgba(244, 251, 253, 0.92);
}

.ppt-annotation-panel h4 {
  margin: 0;
  color: #163f8f;
  font-size: 14px;
}

.ppt-annotation-panel button {
  display: grid;
  gap: 6px;
  padding: 10px;
  text-align: left;
}

.ppt-annotation-panel mark {
  background: rgba(255, 225, 89, 0.68);
  color: #1f3356;
}

.ppt-annotation-panel span {
  color: #5d6f86;
  font-size: 13px;
  line-height: 1.45;
}

.slide-title-input,
.slide-content-input,
.ppt-slide__notes textarea {
  width: 100%;
  border: 1px solid rgba(95, 143, 195, 0.42);
  border-radius: 8px;
  background: rgba(237, 249, 252, 0.46);
  color: #163f8f;
  font: inherit;
  outline: none;
}

.slide-title-input {
  min-height: 58px;
  padding: 0 16px;
  font-size: clamp(24px, 4vw, 46px);
  font-weight: 900;
  text-align: center;
}

.slide-content-input {
  min-height: 260px;
  padding: 14px 16px;
  resize: vertical;
  font-size: 18px;
  line-height: 1.6;
}

.ppt-slide__notes {
  flex: 0 0 auto;
  max-height: 58px;
  padding: 6px 8px;
  border-radius: 8px;
  background: rgba(201, 220, 233, 0.24);
  color: rgba(22, 63, 143, 0.72);
  overflow: auto;
}

.ppt-slide__notes span {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.ppt-slide__notes p {
  margin: 2px 0 0;
  line-height: 1.35;
  font-size: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ppt-slide__notes textarea {
  min-height: 74px;
  margin-top: 6px;
  padding: 10px 12px;
  resize: vertical;
  line-height: 1.6;
}

.ppt-controls {
  display: grid;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 14px;
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

@media (max-width: 860px) {
  .ppt-preview {
    height: 100%;
    max-height: calc(100vh - 96px);
  }

  .ppt-slide {
    width: min(100%, calc((100vh - 132px) * 16 / 9));
    height: auto;
    max-height: 100%;
    aspect-ratio: 16 / 9;
    min-height: 0;
  }

  .layout-grid--visual,
  .comparison-grid,
  .formula-points,
  .content-card-grid {
    grid-template-columns: 1fr;
  }

  .process-strip {
    grid-template-columns: 1fr;
  }

  .process-step {
    min-height: auto;
    padding-top: 34px;
  }

  .visual-panel {
    min-height: 220px;
  }
}
</style>
