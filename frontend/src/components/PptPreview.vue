<template>
  <section v-if="localSlides.length" class="ppt-preview">
    <div class="ppt-toolbar">
      <div class="ppt-toolbar__title">
        <span>{{ activeIndex + 1 }} / {{ localSlides.length }}</span>
        <strong>{{ title || 'PPT Preview' }}</strong>
      </div>

      <div class="ppt-toolbar__actions">
        <button
          v-if="annotatable"
          class="highlight-toggle"
          type="button"
          :class="{ active: annotationTool === 'highlight' }"
          @click="toggleAnnotationTool('highlight')"
        >
          &#x8367;&#x5149;&#x7B14;
        </button>
        <button
          v-if="annotatable"
          class="note-toggle"
          type="button"
          :class="{ active: annotationTool === 'note' }"
          @click="toggleAnnotationTool('note')"
        >
          &#x6CE8;&#x91CA;
        </button>
        <div v-if="annotatable && annotationTool === 'highlight'" class="highlight-palette" aria-label="highlight colors">
          <button
            v-for="color in highlightColors"
            :key="color.value"
            type="button"
            :class="{ active: activeHighlightColor === color.value }"
            :title="color.label"
            :style="{ backgroundColor: color.value }"
            @click="activeHighlightColor = color.value"
          ></button>
        </div>
        <button v-if="editable" class="edit-toggle" type="button" @click="editing = !editing">
          {{ editing ? '&#x5B8C;&#x6210;&#x7F16;&#x8F91;' : '&#x7F16;&#x8F91;&#x5185;&#x5BB9;' }}
        </button>
        <button v-if="editable && editing" class="history-btn" type="button" :disabled="!canUndo" @click="undoEdit">
          &#x4E0A;&#x4E00;&#x6B65;
        </button>
        <button v-if="editable && editing" class="history-btn" type="button" :disabled="!canRedo" @click="redoEdit">
          &#x4E0B;&#x4E00;&#x6B65;
        </button>
        <button v-if="editable" class="export-btn" type="button" :disabled="exporting" @click="emitExport">
          {{ exporting ? '&#x5BFC;&#x51FA;&#x4E2D;...' : '&#x5BFC;&#x51FA; PPTX' }}
        </button>
      </div>
    </div>

    <article
      class="ppt-slide"
      :class="{
        editing,
        'is-dense': currentSlideTextLength > 420,
        'is-very-dense': currentSlideTextLength > 800
      }"
    >
      <div class="ppt-slide__stage">
        <input
          v-if="editing"
          class="slide-title-input"
          :value="currentSlide.title || title"
          @input="updateSlideField('title', $event.target.value)"
        />
        <h3 v-else>{{ currentSlide.title || title }}</h3>

        <textarea
          v-if="editing"
          class="slide-content-input"
          :value="currentSlide.text"
          @input="updateSlideField('text', $event.target.value)"
        ></textarea>

        <div v-else ref="slideContentRef" class="ppt-slide__content" @mouseup="handleTextSelection">
          <template v-for="(segment, index) in slideSegments" :key="index">
            <mark
              v-if="segment.annotation"
              class="ppt-annotation-mark"
              :class="{ 'has-note': isNoteAnnotation(segment.annotation) }"
              :data-annotation-id="segment.annotation.id"
              :style="{ background: annotationBackground(segment.annotation) }"
              @click.stop="openAnnotation(segment.annotation)"
              v-html="renderMath(segment.text)"
            ></mark>
            <span v-else v-html="renderMath(segment.text)"></span>
          </template>
        </div>
      </div>

      <aside class="ppt-slide__notes">
        <span>&#x8BB2;&#x7A3F;</span>
        <textarea
          v-if="editing"
          :value="currentSlide.notes"
          @input="updateSlideField('notes', $event.target.value)"
        ></textarea>
        <p v-else>{{ currentSlide.notes || '&#x6682;&#x65E0;&#x8BB2;&#x7A3F;' }}</p>
      </aside>
    </article>

    <div class="ppt-controls">
      <button type="button" :disabled="activeIndex <= 0" @click="activeIndex -= 1">&#x4E0A;&#x4E00;&#x9875;</button>
      <div class="ppt-dots">
        <button
          v-for="(slide, index) in localSlides"
          :key="slide.index ?? index"
          type="button"
          :class="{ active: index === activeIndex }"
          :aria-label="`slide ${index + 1}`"
          @click="activeIndex = index"
        ></button>
      </div>
      <button type="button" :disabled="activeIndex >= localSlides.length - 1" @click="activeIndex += 1">&#x4E0B;&#x4E00;&#x9875;</button>
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
import { renderMath } from '../utils/renderMath'
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
  }
})

const emit = defineEmits(['update:slides', 'change', 'export-pptx', 'create-note', 'update-note', 'delete-note'])

const activeIndex = ref(0)
const editing = ref(false)
const annotationTool = ref('')
const activeHighlightColor = ref('#ffe159')
const localSlides = ref([])
const undoStack = ref([])
const redoStack = ref([])
const skipNextSlideSync = ref(false)
const slideContentRef = ref(null)
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

const normalizeSlide = (slide, index) => ({
  ...slide,
  index: Number(slide?.index ?? index),
  title: slide?.title || '',
  text: slide?.text || slide?.content || '',
  content: slide?.content || slide?.text || '',
  notes: slide?.notes || slide?.speaker_notes || '',
  speaker_notes: slide?.speaker_notes || slide?.notes || ''
})

const syncLocalSlides = slides => {
  localSlides.value = (Array.isArray(slides) ? slides : []).map(normalizeSlide)
  if (activeIndex.value >= localSlides.value.length) {
    activeIndex.value = Math.max(localSlides.value.length - 1, 0)
  }
}

const currentSlide = computed(() => localSlides.value[activeIndex.value] || localSlides.value[0] || {})
const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

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
  const text = String(currentSlide.value.text || '')
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
  content: slide.text,
  speaker_notes: slide.notes
}))

const emitExport = () => {
  const slides = currentExportSlides()
  emit('update:slides', slides)
  emit('export-pptx', slides)
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

const getOffset = (root, targetNode, targetOffset) => {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let offset = 0
  let node = walker.nextNode()
  while (node) {
    if (node === targetNode) return offset + targetOffset
    offset += node.textContent?.length || 0
    node = walker.nextNode()
  }
  return offset
}

const closeAnnotationEditor = () => {
  annotationEditor.visible = false
}

const handleTextSelection = () => {
  if (!props.annotatable || !annotationTool.value || editing.value || !slideContentRef.value) return
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return

  const range = selection.getRangeAt(0)
  if (!slideContentRef.value.contains(range.commonAncestorContainer)) return

  const selectedText = selection.toString().trim()
  if (!selectedText) return

  const start = getOffset(slideContentRef.value, range.startContainer, range.startOffset)
  const end = getOffset(slideContentRef.value, range.endContainer, range.endOffset)
  const rect = range.getBoundingClientRect()

  const position = {
      kind: 'ppt',
      slideIndex: activeIndex.value,
      start: Math.min(start, end),
      end: Math.max(start, end),
      tool: annotationTool.value,
      color: activeHighlightColor.value
  }

  if (annotationTool.value === 'highlight') {
    emit('create-note', {
      selected_text: selectedText,
      note: '',
      note_text: '',
      position
    })
    selection.removeAllRanges()
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
    position
  })
}

const openAnnotation = annotation => {
  const el = slideContentRef.value?.querySelector(`[data-annotation-id="${CSS.escape(String(annotation.id))}"]`)
  const rect = el?.getBoundingClientRect()
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
    if (previousLength !== localSlides.value.length) {
      activeIndex.value = Math.min(activeIndex.value, Math.max(localSlides.value.length - 1, 0))
    }
    undoStack.value = []
    redoStack.value = []
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

<style scoped>
.ppt-preview {
  display: grid;
  gap: 14px;
}

.ppt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.edit-toggle,
.highlight-toggle,
.note-toggle,
.history-btn,
.export-btn,
.ppt-controls > button {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: #fff;
  color: #163f8f;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
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
  min-height: clamp(520px, 64vh, 760px);
  padding: clamp(22px, 2.6vw, 38px);
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 20px 50px rgba(22, 63, 143, 0.16);
  display: flex;
  flex-direction: column;
  gap: clamp(14px, 2vw, 20px);
  overflow: visible;
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
  gap: clamp(14px, 2vw, 24px);
}

.ppt-slide h3 {
  margin: 0;
  color: #163f8f;
  font-size: clamp(26px, 3.8vw, 48px);
  line-height: 1.16;
  text-align: center;
}

.ppt-slide__content {
  width: min(88%, 940px);
  max-height: 100%;
  margin: 0 auto;
  padding: 2px 8px 2px 0;
  overflow: auto;
  color: rgba(22, 63, 143, 0.82);
  font-size: clamp(17px, 1.65vw, 23px);
  line-height: 1.62;
  white-space: pre-line;
  word-break: break-word;
}

.ppt-slide.is-dense h3 {
  font-size: clamp(23px, 3vw, 38px);
}

.ppt-slide.is-dense .ppt-slide__content {
  width: min(94%, 1040px);
  font-size: clamp(15px, 1.35vw, 19px);
  line-height: 1.58;
}

.ppt-slide.is-very-dense h3 {
  font-size: clamp(20px, 2.5vw, 32px);
}

.ppt-slide.is-very-dense .ppt-slide__content {
  width: min(96%, 1100px);
  font-size: clamp(14px, 1.15vw, 17px);
  line-height: 1.52;
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
  max-height: min(150px, 24vh);
  padding: 10px 12px;
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
  margin: 5px 0 0;
  line-height: 1.65;
}

.ppt-slide__notes textarea {
  min-height: 74px;
  margin-top: 6px;
  padding: 10px 12px;
  resize: vertical;
  line-height: 1.6;
}

.ppt-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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
</style>
