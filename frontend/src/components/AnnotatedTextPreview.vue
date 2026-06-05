<template>
  <section class="annotated-text-preview">
    <div v-if="annotatable" class="annotated-text-toolbar">
      <button
        class="highlight-toggle"
        type="button"
        :class="{ active: annotationMode }"
        @click="annotationMode = !annotationMode"
      >
        荧光笔
      </button>
    </div>

    <article ref="contentRef" class="annotated-text-body" @mouseup="handleSelection">
      <template v-for="(segment, index) in segments" :key="index">
        <mark
          v-if="segment.annotation"
          class="annotation-mark"
          :data-annotation-id="segment.annotation.id"
          @click.stop="openAnnotation(segment.annotation)"
        >{{ segment.text }}</mark>
        <span v-else>{{ segment.text }}</span>
      </template>
    </article>

    <div
      v-if="editor.visible"
      class="annotation-popover"
      :style="{ left: `${editor.x}px`, top: `${editor.y}px` }"
    >
      <strong>{{ editor.mode === 'edit' ? '编辑笔记' : '添加笔记' }}</strong>
      <p>{{ editor.selectedText }}</p>
      <textarea v-model.trim="editor.note" rows="3" placeholder="写下注释"></textarea>
      <div class="annotation-popover__actions">
        <button type="button" @click="closeEditor">取消</button>
        <button
          v-if="editor.mode === 'edit'"
          type="button"
          class="danger"
          @click="removeAnnotation"
        >删除</button>
        <button type="button" class="primary" @click="saveAnnotation">保存</button>
      </div>
    </div>

    <aside v-if="normalizedAnnotations.length" class="annotation-panel">
      <h3>笔记</h3>
      <button
        v-for="annotation in normalizedAnnotations"
        :key="annotation.id"
        type="button"
        @click="jumpToAnnotation(annotation)"
      >
        <mark>{{ annotation.selected_text || annotation.selectedText }}</mark>
        <span>{{ annotation.note || '暂无注释' }}</span>
      </button>
    </aside>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  annotations: {
    type: Array,
    default: () => []
  },
  annotatable: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['create-note', 'update-note', 'delete-note'])

const contentRef = ref(null)
const annotationMode = ref(Boolean(props.annotatable))
const editor = reactive({
  visible: false,
  mode: 'create',
  id: '',
  x: 0,
  y: 0,
  selectedText: '',
  note: '',
  position: null
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
  return {
    kind: 'text',
    start: Number(annotation?.start ?? 0),
    end: Number(annotation?.end ?? 0)
  }
}

const normalizedAnnotations = computed(() => props.annotations
  .map(annotation => ({
    ...annotation,
    id: annotation.id || annotation.annotation_id || annotation.annotationId || `${annotation.selected_text || annotation.selectedText}-${annotation.note}`,
    position: normalizePosition(annotation)
  }))
  .filter(annotation => annotation.position?.kind === 'text')
  .filter(annotation => Number.isFinite(Number(annotation.position.start)) && Number.isFinite(Number(annotation.position.end)))
  .sort((a, b) => Number(a.position.start) - Number(b.position.start)))

const segments = computed(() => {
  const text = props.content || ''
  const result = []
  let cursor = 0

  for (const annotation of normalizedAnnotations.value) {
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

const closeEditor = () => {
  editor.visible = false
}

const handleSelection = () => {
  if (!props.annotatable || !annotationMode.value || !contentRef.value) return
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return

  const range = selection.getRangeAt(0)
  if (!contentRef.value.contains(range.commonAncestorContainer)) return

  const selectedText = selection.toString().trim()
  if (!selectedText) return

  const start = getOffset(contentRef.value, range.startContainer, range.startOffset)
  const end = getOffset(contentRef.value, range.endContainer, range.endOffset)
  const rect = range.getBoundingClientRect()

  Object.assign(editor, {
    visible: true,
    mode: 'create',
    id: '',
    x: Math.min(rect.left + window.scrollX, window.innerWidth - 340),
    y: rect.bottom + window.scrollY + 8,
    selectedText,
    note: '',
    position: { kind: 'text', start: Math.min(start, end), end: Math.max(start, end) }
  })
}

const openAnnotation = annotation => {
  const el = contentRef.value?.querySelector(`[data-annotation-id="${CSS.escape(String(annotation.id))}"]`)
  const rect = el?.getBoundingClientRect()
  Object.assign(editor, {
    visible: true,
    mode: 'edit',
    id: annotation.id,
    x: rect ? Math.min(rect.left + window.scrollX, window.innerWidth - 340) : window.innerWidth / 2 - 160,
    y: rect ? rect.bottom + window.scrollY + 8 : window.scrollY + 120,
    selectedText: annotation.selected_text || annotation.selectedText || '',
    note: annotation.note || '',
    position: annotation.position
  })
}

const saveAnnotation = () => {
  const payload = {
    selected_text: editor.selectedText,
    note: editor.note,
    position: editor.position
  }

  if (editor.mode === 'edit') {
    emit('update-note', editor.id, payload)
  } else {
    emit('create-note', payload)
  }
  closeEditor()
}

const removeAnnotation = () => {
  if (editor.id) emit('delete-note', editor.id)
  closeEditor()
}

const jumpToAnnotation = annotation => {
  const el = contentRef.value?.querySelector(`[data-annotation-id="${CSS.escape(String(annotation.id))}"]`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  if (el) openAnnotation(annotation)
}
</script>

<style scoped>
.annotated-text-preview {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 280px);
  gap: 18px;
  align-items: start;
}

.annotated-text-toolbar {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
}

.highlight-toggle {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(214, 176, 38, 0.62);
  border-radius: 8px;
  background: rgba(255, 225, 89, 0.22);
  color: #8a6a00;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.highlight-toggle.active {
  border-color: rgba(214, 176, 38, 0.86);
  background: #ffe159;
  color: #4f3b00;
}

.annotated-text-body {
  min-height: 320px;
  padding: 28px;
  border: 1px solid rgba(22, 63, 143, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.84);
  color: #1f3356;
  font-size: 16px;
  line-height: 1.9;
  white-space: pre-wrap;
}

.annotation-mark {
  border-radius: 4px;
  background: linear-gradient(transparent 38%, rgba(255, 225, 89, 0.72) 38%);
  color: inherit;
  cursor: pointer;
}

.annotation-popover {
  position: fixed;
  z-index: 10000;
  width: min(320px, calc(100vw - 28px));
  padding: 14px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(22, 63, 143, 0.2);
}

.annotation-popover strong {
  display: block;
  margin-bottom: 8px;
  color: #163f8f;
}

.annotation-popover p {
  max-height: 76px;
  margin: 0 0 10px;
  overflow: auto;
  color: #5d6f86;
  font-size: 13px;
  line-height: 1.5;
}

.annotation-popover textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid rgba(22, 63, 143, 0.18);
  border-radius: 8px;
  padding: 10px;
  color: #1f3356;
  font: inherit;
}

.annotation-popover__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.annotation-popover button,
.annotation-panel button {
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 8px;
  background: #ffffff;
  color: #163f8f;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.annotation-popover button {
  min-height: 32px;
  padding: 0 12px;
}

.annotation-popover .primary {
  border-color: #163f8f;
  background: #163f8f;
  color: #ffffff;
}

.annotation-popover .danger {
  color: #b64040;
}

.annotation-panel {
  position: sticky;
  top: 0;
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgba(22, 63, 143, 0.12);
  border-radius: 8px;
  background: rgba(244, 251, 253, 0.92);
}

.annotation-panel h3 {
  margin: 0;
  color: #163f8f;
  font-size: 15px;
}

.annotation-panel button {
  display: grid;
  gap: 6px;
  padding: 10px;
  text-align: left;
}

.annotation-panel mark {
  background: rgba(255, 225, 89, 0.68);
  color: #1f3356;
}

.annotation-panel span {
  color: #5d6f86;
  font-size: 13px;
  line-height: 1.45;
}

@media (max-width: 900px) {
  .annotated-text-preview {
    grid-template-columns: 1fr;
  }
}
</style>
