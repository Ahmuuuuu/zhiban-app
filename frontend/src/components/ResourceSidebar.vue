<template>
  <aside class="resource-sidebar" :class="{ collapsed: !visible }">
    <!-- 收缩开关 -->
    <button class="toggle-btn" @click="$emit('toggle')" :title="visible ? '收起' : '学习资源'">
      <span v-if="visible">▸</span>
      <span v-else class="collapsed-icon">📄</span>
    </button>

    <template v-if="visible">
      <header class="sidebar-header">
        <h3>学习资源</h3>
        <button class="close-btn" @click="$emit('toggle')">✕</button>
      </header>

      <div class="sidebar-body">
        <!-- 资源生成触发区 -->
        <section class="generate-section">
          <div class="generate-form" v-if="!isGenerating && generatedResources.length === 0">
            <input
              v-model="topicInput"
              class="topic-input"
              placeholder="输入学习主题..."
              @keydown.enter="startGenerate"
            />
            <div class="type-checkboxes">
              <label
                v-for="t in availableTypes"
                :key="t.value"
                class="type-label"
                :class="{ active: selectedTypes.includes(t.value) }"
                @click="toggleType(t.value)"
              >
                {{ t.label }}
              </label>
            </div>
            <button
              class="generate-btn"
              :disabled="!topicInput.trim() || isGenerating"
              @click="startGenerate"
            >
              开始生成
            </button>
          </div>

          <!-- 正在生成 -->
          <div v-if="isGenerating" class="generating-status">
            <div class="status-title">
              <span class="spinner"></span>
              正在生成学习资源...
            </div>
            <div class="progress-list">
              <div
                v-for="(res, idx) in progressItems"
                :key="idx"
                class="progress-item"
                :class="res.status"
              >
                <span class="progress-icon">{{ statusIcon(res.status) }}</span>
                <span class="progress-label">{{ res.label }}</span>
                <span class="progress-bar" v-if="res.status === 'generating'">
                  <span class="bar-fill"></span>
                </span>
              </div>
            </div>
            <div class="current-topic">主题：{{ topicInput || generatingTopic }}</div>
          </div>

          <!-- 生成完成 -->
          <div v-if="showResult" class="result-actions">
            <div class="result-summary">✓ 资源生成完成</div>
          </div>
        </section>

        <!-- 生成的资源列表 -->
        <section v-if="generatedResources.length > 0" class="resources-list">
          <div
            v-for="(res, idx) in generatedResources"
            :key="idx"
            class="resource-card"
          >
            <div class="resource-header">
              <span class="resource-icon">{{ typeIcon(res.resource_type) }}</span>
              <span class="resource-type">{{ typeLabel(res.resource_type) }}</span>
            </div>
            <div class="resource-topic">{{ res.topic }}</div>
            <div class="resource-preview">{{ truncate(res.content, 120) }}</div>
            <div class="resource-actions">
              <button
                class="view-btn"
                @click="toggleContent(idx)"
              >
                {{ expandedIdx === idx ? '收起' : '预览' }}
              </button>
              <button
                v-if="res.download_url"
                type="button"
                class="download-btn"
                @click="downloadResource(res)"
              >
                下载
              </button>
            </div>
            <div v-if="expandedIdx === idx" class="resource-content markdown-body"
              v-html="renderMarkdown(res.content)"
            ></div>
          </div>
        </section>

        <!-- 空状态 -->
        <div v-if="!isGenerating && generatedResources.length === 0 && !showResult" class="empty-state">
          <div class="empty-icon">📚</div>
          <p>输入学习主题，AI 将为你生成<br/>PPT、学习文档等资源</p>
        </div>
      </div>

      <!-- 底部重新生成按钮 -->
      <footer v-if="!isGenerating && generatedResources.length > 0" class="sidebar-footer">
        <button class="regenerate-btn" @click="resetAll">
          再生成一个
        </button>
      </footer>
    </template>
  </aside>
</template>

<script setup>
import { ref, watch, defineEmits } from 'vue'
import { resolveApiUrl, streamResourceGeneration } from '../api/apis'

const emit = defineEmits(['toggle'])

const props = defineProps({
  visible: { type: Boolean, default: false },
  /** 从外部传入的主题（AI 对话上下文） */
  contextTopic: { type: String, default: '' }
})

const availableTypes = [
  { value: 'ppt', label: 'PPT' },
  { value: 'document', label: '学习文档' },
  { value: 'mindmap', label: '思维导图' },
  { value: 'exercise', label: '练习题' },
  { value: 'case', label: '案例分析' },
  { value: 'reading', label: '扩展阅读' },
]

const topicInput = ref('')
const selectedTypes = ref(['ppt', 'document'])
const isGenerating = ref(false)
const generatingTopic = ref('')
const generatedResources = ref([])
const progressItems = ref([])
const showResult = ref(false)
const expandedIdx = ref(-1)

// 资源类型及其状态（用于进度展示）
const resourceStatusMap = {
  pending: '等待生成',
  generating: '生成中...',
  done: '已完成',
  reviewing: '审核中...',
}

const statusIcon = (status) => {
  switch (status) {
    case 'done': return '✓'
    case 'generating': return '◌'
    case 'reviewing': return '◎'
    default: return '○'
  }
}

const typeIcon = (type) => {
  const map = {
    ppt: '📊',
    document: '📝',
    mindmap: '🧠',
    exercise: '✏️',
    case: '📋',
    reading: '📖',
  }
  return map[type] || '📄'
}

const typeLabel = (type) => {
  const found = availableTypes.find(t => t.value === type)
  return found ? found.label : type
}

const toggleType = (val) => {
  if (isGenerating.value) return
  const idx = selectedTypes.value.indexOf(val)
  if (idx > -1) {
    if (selectedTypes.value.length > 1) {
      selectedTypes.value.splice(idx, 1)
    }
  } else {
    selectedTypes.value.push(val)
  }
}

const truncate = (text, max) => {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

const resourceDownloadUrl = url => resolveApiUrl(url)

const resourceExtension = type => {
  const normalizedType = String(type || '').toLowerCase()

  if (normalizedType.includes('document')) return 'txt'
  if (normalizedType.includes('ppt')) return 'pptx'
  return 'md'
}

const resourceFileName = resource => {
  const extension = resourceExtension(resource.resource_type)
  const rawName = String(resource.filename || `${resource.topic || 'resource'}_${resource.resource_type || 'document'}`).trim()

  if (/\.[^.\\/]+$/.test(rawName)) {
    return rawName.replace(/\.[^.\\/]+$/, `.${extension}`)
  }

  return `${rawName}.${extension}`
}

const downloadResource = async resource => {
  if (!resource?.download_url) return

  try {
    const token = localStorage.getItem('token')
    const response = await fetch(resourceDownloadUrl(resource.download_url), {
      headers: {
        ...(token ? { token } : {})
      }
    })

    if (!response.ok) {
      throw new Error(`下载失败：${response.status}`)
    }

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = resourceFileName(resource)
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载生成资源失败：', error)
    window.alert('下载失败，请确认登录状态和后端服务是否正常。')
  }
}

const normalizeGeneratedResource = data => {
  const resourceType = data.resource_type || data.file_type || data.fileType || 'document'

  return {
    ...data,
    resource_id: data.resource_id || data.file_id || data.fileId || '',
    resource_type: resourceType,
    topic: data.topic || generatingTopic.value || topicInput.value || '学习资源',
    content: data.content || data.text || data.preview_content || data.previewContent || '',
    filename: data.filename || data.file_name || '',
    download_url: data.download_url || data.downloadUrl || (data.resource_id ? `/resource/${data.resource_id}/download` : '')
  }
}

const upsertGeneratedResource = data => {
  const resource = normalizeGeneratedResource(data)
  const index = generatedResources.value.findIndex(item => {
    return (
      (resource.resource_id && item.resource_id === resource.resource_id) ||
      (resource.resource_type && item.resource_type === resource.resource_type)
    )
  })

  if (index === -1) {
    generatedResources.value.push(resource)
    return
  }

  generatedResources.value[index] = {
    ...generatedResources.value[index],
    ...resource,
    content: resource.content || generatedResources.value[index].content
  }
}

const startGenerate = async () => {
  const topic = topicInput.value.trim() || generatingTopic.value
  if (!topic || isGenerating.value) return

  isGenerating.value = true
  showResult.value = false
  generatedResources.value = []
  expandedIdx.value = -1
  generatingTopic.value = topic

  // 初始化进度列表
  progressItems.value = selectedTypes.value.map(t => ({
    type: t,
    label: typeLabel(t),
    status: 'pending'
  }))

  // Leader 阶段
  progressItems.value.unshift({
    type: '_leader',
    label: '分析学习主题',
    status: 'generating'
  })

  // 添加审核阶段（稍后显示）
  const reviewerItem = {
    type: '_reviewer',
    label: '审核生成内容',
    status: 'pending'
  }

  try {
    await streamResourceGeneration(
      { topic, resource_types: selectedTypes.value },
      {
        onProgress: (eventData) => {
          // eventData: { resources: [...], review_passed: bool }
          const finishedTypes = eventData.resources || []

          // Leader 完成
          const leaderItem = progressItems.value.find(p => p.type === '_leader')
          if (leaderItem && leaderItem.status === 'generating') {
            leaderItem.status = 'done'
          }

          // 更新各资源类型状态
          for (const item of progressItems.value) {
            if (item.type === '_leader' || item.type === '_reviewer') continue
            if (finishedTypes.includes(item.type)) {
              item.status = 'done'
            } else {
              item.status = item.status === 'done' ? 'done' : 'generating'
            }
          }

          // 添加审核阶段
          if (eventData.review_passed !== undefined && finishedTypes.length > 0) {
            const hasReviewer = progressItems.value.some(p => p.type === '_reviewer')
            if (!hasReviewer) {
              progressItems.value.push(reviewerItem)
            }
            const rItem = progressItems.value.find(p => p.type === '_reviewer')
            if (rItem) {
              rItem.status = eventData.review_passed ? 'done' : 'generating'
            }
          }
        },
        onFile: (eventData) => {
          upsertGeneratedResource(eventData)
        },
        onDone: (eventData) => {
          // eventData: { done: true, resources: [...] }
          if (eventData.resources && Array.isArray(eventData.resources)) {
            eventData.resources.forEach(upsertGeneratedResource)
          }

          // 标记所有进度为完成
          progressItems.value.forEach(p => { p.status = 'done' })
          isGenerating.value = false
          showResult.value = true
        }
      }
    )
  } catch (error) {
    console.error('资源生成失败:', error)
    progressItems.value.push({
      type: '_error',
      label: '生成失败：' + (error.message || '请稍后重试'),
      status: 'done'
    })
    isGenerating.value = false
    showResult.value = true
  }
}

const resetAll = () => {
  topicInput.value = ''
  selectedTypes.value = ['ppt', 'document']
  generatedResources.value = []
  progressItems.value = []
  isGenerating.value = false
  showResult.value = false
  expandedIdx.value = -1
}

const toggleContent = (idx) => {
  expandedIdx.value = expandedIdx.value === idx ? -1 : idx
}

// 监听 contextTopic 变化
watch(() => props.contextTopic, (val) => {
  if (val && !isGenerating.value && generatedResources.value.length === 0) {
    topicInput.value = val
  }
})

// Simple markdown renderer (reused from ChatView)
const escapeHtml = (value) => {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const renderInlineMarkdown = (value) => {
  let text = escapeHtml(value)
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  text = text.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
  text = text.replace(/_([^_\n]+)_/g, '<em>$1</em>')
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
  return text
}

const isTableSeparator = (line) => {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line)
}

const renderTable = (tableLines) => {
  const rows = tableLines.map(line => {
    return line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map(cell => renderInlineMarkdown(cell.trim()))
  })
  const header = rows[0] || []
  const body = rows.slice(2)
  return `
    <div class="md-table-wrap">
      <table>
        <thead><tr>${header.map(cell => `<th>${cell}</th>`).join('')}</tr></thead>
        <tbody>${body.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>
      </table>
    </div>
  `
}

const renderMarkdown = (content) => {
  const text = String(content || '').trim()
  if (!text) return ''
  const lines = text.split(/\r?\n/)
  const html = []
  let paragraph = []
  let listItems = []
  let listType = ''
  let codeLines = []
  let inCodeBlock = false
  let codeLanguage = ''

  const flushParagraph = () => {
    if (!paragraph.length) return
    html.push(`<p>${paragraph.map(renderInlineMarkdown).join('<br>')}</p>`)
    paragraph = []
  }
  const flushList = () => {
    if (!listItems.length) return
    const tag = listType === 'ol' ? 'ol' : 'ul'
    html.push(`<${tag}>${listItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</${tag}>`)
    listItems = []
    listType = ''
  }
  const flushCode = () => {
    const languageLabel = codeLanguage ? `<span>${escapeHtml(codeLanguage)}</span>` : ''
    html.push(`<div class="md-code-block">${languageLabel}<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre></div>`)
    codeLines = []
    codeLanguage = ''
  }

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index]
    const line = rawLine.trim()
    if (line.startsWith('```')) {
      if (inCodeBlock) { flushCode(); inCodeBlock = false }
      else { flushParagraph(); flushList(); inCodeBlock = true; codeLanguage = line.replace(/^```/, '').trim() }
      continue
    }
    if (inCodeBlock) { codeLines.push(rawLine); continue }
    if (!line) { flushParagraph(); flushList(); continue }
    if (line.includes('|') && lines[index + 1] && isTableSeparator(lines[index + 1])) {
      flushParagraph(); flushList()
      const tableLines = [rawLine, lines[index + 1]]
      index += 2
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        tableLines.push(lines[index]); index += 1
      }
      index -= 1
      html.push(renderTable(tableLines))
      continue
    }
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/)
    if (headingMatch) {
      flushParagraph(); flushList()
      const level = Math.min(headingMatch[1].length + 2, 6)
      html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`)
      continue
    }
    const blockquoteMatch = line.match(/^>\s?(.+)$/)
    if (blockquoteMatch) {
      flushParagraph(); flushList()
      html.push(`<blockquote>${renderInlineMarkdown(blockquoteMatch[1])}</blockquote>`)
      continue
    }
    const orderedMatch = line.match(/^\d+\.\s+(.+)$/)
    const unorderedMatch = line.match(/^[-*]\s+(.+)$/)
    if (orderedMatch || unorderedMatch) {
      flushParagraph()
      const currentType = orderedMatch ? 'ol' : 'ul'
      if (listType && listType !== currentType) flushList()
      listType = currentType
      listItems.push((orderedMatch?.[1] || unorderedMatch?.[1] || '').trim())
      continue
    }
    flushList()
    paragraph.push(rawLine)
  }
  if (inCodeBlock) flushCode()
  flushParagraph()
  flushList()
  return html.join('')
}
</script>

<style scoped>
.resource-sidebar {
  position: relative;
  width: 340px;
  min-width: 340px;
  height: 100vh;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
  border-left: 1px solid rgba(196, 226, 248, 0.38);
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  overflow: hidden;
  z-index: 2;
}

.resource-sidebar.collapsed {
  width: 0;
  min-width: 0;
  border-left: none;
}

.toggle-btn {
  position: absolute;
  left: -36px;
  top: 80px;
  width: 36px;
  height: 64px;
  border: 1px solid rgba(196, 226, 248, 0.38);
  border-right: none;
  border-radius: 10px 0 0 10px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  color: #163f8f;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 3;
}

.toggle-btn:hover {
  background: rgba(255, 255, 255, 0.98);
}

.collapsed-icon {
  font-size: 20px;
}

.sidebar-header {
  padding: 18px 20px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(196, 226, 248, 0.3);
  flex-shrink: 0;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #163f8f;
}

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(22, 63, 143, 0.5);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(22, 63, 143, 0.08);
  color: #163f8f;
}

.sidebar-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 生成区 */
.generate-section {
  background: rgba(255, 255, 255, 0.5);
  border-radius: 14px;
  padding: 16px;
  border: 1px solid rgba(196, 226, 248, 0.3);
}

.topic-input {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid rgba(196, 226, 248, 0.5);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.7);
  color: #163f8f;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.topic-input:focus {
  border-color: #5f8fc3;
}

.topic-input::placeholder {
  color: rgba(22, 63, 143, 0.4);
}

.type-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.type-label {
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid rgba(196, 226, 248, 0.5);
  font-size: 12px;
  color: rgba(22, 63, 143, 0.7);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.type-label.active {
  background: rgba(22, 63, 143, 0.1);
  border-color: #163f8f;
  color: #163f8f;
  font-weight: 600;
}

.type-label:hover {
  background: rgba(22, 63, 143, 0.06);
}

.generate-btn {
  width: 100%;
  margin-top: 12px;
  padding: 10px;
  border: none;
  border-radius: 10px;
  background: #163f8f;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.generate-btn:hover:not(:disabled) {
  background: #1d5dab;
  transform: translateY(-1px);
}

.generate-btn:disabled {
  background: rgba(22, 63, 143, 0.3);
  cursor: not-allowed;
}

/* 生成进度 */
.generating-status {
  padding: 4px 0;
}

.status-title {
  font-size: 14px;
  font-weight: 600;
  color: #163f8f;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(22, 63, 143, 0.2);
  border-top-color: #163f8f;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  color: rgba(22, 63, 143, 0.7);
  transition: all 0.3s;
}

.progress-item.done {
  color: #163f8f;
}

.progress-item.done .progress-icon {
  color: #22c55e;
}

.progress-item.generating {
  color: #163f8f;
  font-weight: 600;
  background: rgba(22, 63, 143, 0.05);
}

.progress-icon {
  width: 20px;
  text-align: center;
  font-size: 14px;
}

.progress-label {
  flex: 1;
}

.progress-bar {
  width: 60px;
  height: 4px;
  border-radius: 2px;
  background: rgba(22, 63, 143, 0.1);
  overflow: hidden;
}

.bar-fill {
  display: block;
  height: 100%;
  width: 60%;
  border-radius: 2px;
  background: linear-gradient(90deg, #5f8fc3, #163f8f);
  animation: bar-pulse 1.5s ease-in-out infinite;
}

@keyframes bar-pulse {
  0%, 100% { transform: translateX(-30%); }
  50% { transform: translateX(70%); }
}

.current-topic {
  margin-top: 10px;
  font-size: 12px;
  color: rgba(22, 63, 143, 0.5);
}

/* 结果 */
.result-actions {
  text-align: center;
}

.result-summary {
  font-size: 14px;
  font-weight: 600;
  color: #22c55e;
  padding: 4px 0;
}

/* 资源列表 */
.resources-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.resource-card {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  padding: 14px;
  border: 1px solid rgba(196, 226, 248, 0.3);
  transition: all 0.2s;
}

.resource-card:hover {
  border-color: rgba(22, 63, 143, 0.2);
  box-shadow: 0 4px 12px rgba(22, 63, 143, 0.06);
}

.resource-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.resource-icon {
  font-size: 16px;
}

.resource-type {
  font-size: 12px;
  font-weight: 600;
  color: #5f8fc3;
  background: rgba(95, 143, 195, 0.1);
  padding: 2px 8px;
  border-radius: 6px;
}

.resource-topic {
  font-size: 14px;
  font-weight: 600;
  color: #163f8f;
  margin-bottom: 6px;
}

.resource-preview {
  font-size: 12px;
  color: rgba(22, 63, 143, 0.6);
  line-height: 1.5;
  margin-bottom: 8px;
}

.resource-actions {
  display: flex;
  gap: 8px;
}

.view-btn,
.download-btn {
  padding: 4px 12px;
  border: 1px solid rgba(196, 226, 248, 0.5);
  border-radius: 8px;
  background: transparent;
  color: #163f8f;
  font-size: 12px;
  line-height: 1.4;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s;
}

.view-btn:hover,
.download-btn:hover {
  background: rgba(22, 63, 143, 0.06);
}

.resource-content {
  margin-top: 10px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(196, 226, 248, 0.2);
  font-size: 13px;
  line-height: 1.7;
  color: #163f8f;
  max-height: 400px;
  overflow-y: auto;
  white-space: normal;
}

/* 空状态 */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state p {
  font-size: 13px;
  color: rgba(22, 63, 143, 0.5);
  line-height: 1.6;
}

/* 底部 */
.sidebar-footer {
  padding: 12px 18px 18px;
  border-top: 1px solid rgba(196, 226, 248, 0.2);
  flex-shrink: 0;
}

.regenerate-btn {
  width: 100%;
  padding: 10px;
  border: 1.5px dashed rgba(196, 226, 248, 0.5);
  border-radius: 10px;
  background: transparent;
  color: #5f8fc3;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.regenerate-btn:hover {
  border-color: #163f8f;
  color: #163f8f;
  background: rgba(22, 63, 143, 0.03);
}

/* Markdown 样式（与 ChatView 对齐） */
.resource-content :deep(p) {
  margin: 0;
  color: #163f8f;
}

.resource-content :deep(p + p) {
  margin-top: 10px;
}

.resource-content :deep(h3),
.resource-content :deep(h4) {
  margin: 12px 0 6px;
  color: #163f8f;
}

.resource-content :deep(ul),
.resource-content :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.resource-content :deep(code) {
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.5);
  color: #163f8f;
  font-family: monospace;
  font-size: 0.92em;
}

.resource-content :deep(.md-code-block) {
  margin: 8px 0;
  border-radius: 6px;
  border: 1px solid rgba(196, 226, 248, 0.3);
  background: rgba(255, 255, 255, 0.3);
}

.resource-content :deep(pre) {
  margin: 0;
  padding: 10px;
  overflow-x: auto;
}

.resource-content :deep(pre code) {
  padding: 0;
  background: transparent;
}

.resource-content :deep(a) {
  color: #163f8f;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 2px;
}

@media (max-width: 1100px) {
  .resource-sidebar {
    width: 280px;
    min-width: 280px;
  }
}

@media (max-width: 800px) {
  .resource-sidebar {
    position: fixed;
    right: 0;
    top: 0;
    width: 300px;
    min-width: 300px;
    box-shadow: -4px 0 20px rgba(0,0,0,0.1);
  }
  .resource-sidebar.collapsed {
    transform: translateX(100%);
    width: 300px;
  }
}
</style>
