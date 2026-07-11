<template>
  <div class="ppt-toolbar">
    <div class="ppt-toolbar__title">
      <span>{{ currentIndex + 1 }} / {{ total }}</span>
      <strong>{{ title || 'PPT Preview' }}</strong>
    </div>

    <div class="ppt-toolbar__actions">
      <button
        class="nav-btn"
        type="button"
        :disabled="currentIndex <= 0"
        title="上一页"
        @click="$emit('previous')"
      >
        &#x25C0;
      </button>
      <button
        class="nav-btn"
        type="button"
        :disabled="currentIndex >= total - 1"
        title="下一页"
        @click="$emit('next')"
      >
        &#x25B6;
      </button>
      <button
        v-if="annotatable"
        class="highlight-toggle"
        type="button"
        :class="{ active: annotationTool === 'highlight' }"
        @click="$emit('toggle-tool', 'highlight')"
      >
        荧光笔
      </button>
      <button
        v-if="annotatable"
        class="note-toggle"
        type="button"
        :class="{ active: annotationTool === 'note' }"
        @click="$emit('toggle-tool', 'note')"
      >
        注释
      </button>
      <div v-if="annotatable && annotationTool === 'highlight'" class="highlight-palette" aria-label="highlight colors">
        <button
          v-for="color in highlightColors"
          :key="color.value"
          type="button"
          :class="{ active: activeHighlightColor === color.value }"
          :title="color.label"
          :style="{ backgroundColor: color.value }"
          @click="$emit('update:activeHighlightColor', color.value)"
        ></button>
      </div>
      <button v-if="editable" class="edit-toggle" type="button" @click="$emit('update:editing', !editing)">
        {{ editing ? '完成编辑' : '编辑内容' }}
      </button>
      <button v-if="editable" class="advanced-edit-btn" type="button" @click="$emit('advanced-edit')">
        高级编辑
      </button>
      <button v-if="editable && editing" class="history-btn" type="button" :disabled="!canUndo" @click="$emit('undo')">
        上一步
      </button>
      <button v-if="editable && editing" class="history-btn" type="button" :disabled="!canRedo" @click="$emit('redo')">
        下一步
      </button>
      <label class="style-source-select">
        <span>风格</span>
        <select :value="styleSource" @change="$emit('update:styleSource', $event.target.value)">
          <option value="builtin">内置风格</option>
          <option value="custom">我的素材</option>
        </select>
      </label>
      <button v-if="editable" class="export-btn" type="button" :disabled="exporting" @click="$emit('export')">
        {{ exporting ? '导出中...' : '导出 PPTX' }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  currentIndex: {
    type: Number,
    default: 0
  },
  total: {
    type: Number,
    default: 0
  },
  title: {
    type: String,
    default: ''
  },
  editable: {
    type: Boolean,
    default: false
  },
  editing: {
    type: Boolean,
    default: false
  },
  exporting: {
    type: Boolean,
    default: false
  },
  annotatable: {
    type: Boolean,
    default: false
  },
  annotationTool: {
    type: String,
    default: ''
  },
  highlightColors: {
    type: Array,
    default: () => []
  },
  activeHighlightColor: {
    type: String,
    default: ''
  },
  canUndo: {
    type: Boolean,
    default: false
  },
  canRedo: {
    type: Boolean,
    default: false
  },
  styleSource: {
    type: String,
    default: 'custom'
  }
})

defineEmits([
  'previous',
  'next',
  'toggle-tool',
  'update:activeHighlightColor',
  'update:styleSource',
  'update:editing',
  'undo',
  'redo',
  'advanced-edit',
  'export'
])
</script>

<style scoped>
.ppt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 34px;
}

.ppt-toolbar__title {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #5f8fc3;
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
.advanced-edit-btn,
.highlight-toggle,
.note-toggle,
.nav-btn,
.history-btn,
.export-btn {
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: rgba(250, 250, 250, 0.88);
  color: #163f8f;
  font-weight: 900;
  font-size: 12px;
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

.style-source-select {
  min-height: 30px;
  padding: 0 8px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: rgba(250, 250, 250, 0.88);
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 900;
}

.style-source-select select {
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  outline: none;
  cursor: pointer;
}

.edit-toggle {
  border-color: rgba(22, 63, 143, 0.9);
}

.advanced-edit-btn {
  border-color: rgba(22, 63, 143, 0.5);
  background: #ffffff;
  color: #163f8f;
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
  border: 2px solid rgba(255, 255, 255, 0.92);
  border-radius: 999px;
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
</style>
