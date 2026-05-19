<template>
  <main class="resource-page">
    <header class="resource-header">
      <div>
        <p class="eyebrow">My Resources</p>
        <h1>我的学习资源</h1>
        <p class="summary">这里只展示你自己上传的学习资料，公开资源请前往资源中心。</p>
      </div>

      <div class="header-actions">
        <button class="icon-btn" type="button" :disabled="loading" title="刷新资源" @click="loadResources">
          <RefreshCw :size="18" :class="{ spinning: loading }" />
        </button>
        <router-link class="import-link" to="/resources">
          <BookOpenText :size="17" />
          <span>资源中心</span>
        </router-link>
        <router-link class="import-link" to="/study-import">
          <Upload :size="17" />
          <span>资料导入</span>
        </router-link>
      </div>
    </header>

    <div class="resource-tools">
      <label class="search-field">
        <Search :size="18" />
        <input v-model.trim="keyword" type="search" placeholder="搜索我的资源标题或内容" />
      </label>
    </div>

    <div v-if="errorMessage" class="notice">
      <AlertCircle :size="18" />
      <span>{{ errorMessage }}</span>
    </div>

    <div v-else-if="loading" class="resource-grid">
      <article v-for="item in 6" :key="item" class="resource-card skeleton-card">
        <span></span>
        <strong></strong>
        <p></p>
        <p></p>
      </article>
    </div>

    <div v-else-if="filteredResources.length" class="resource-layout">
      <div class="resource-list">
        <article
          v-for="resource in filteredResources"
          :key="resource.doc_id"
          class="resource-card"
          :class="{ selected: selectedResource?.doc_id === resource.doc_id }"
          @click="selectedResource = resource"
        >
          <div class="card-top">
            <span class="type-mark">
              <FileText :size="18" />
            </span>
            <span class="visibility">{{ resource.categoryLabel || '我的资源' }}</span>
          </div>

          <h2>{{ resource.title || '未命名资料' }}</h2>
          <p>{{ getExcerpt(resource.content) }}</p>

          <footer>
            <span>
              <CalendarDays :size="15" />
              {{ formatDate(resource.created_at) }}
            </span>
            <span>{{ getWordCount(resource.content) }} 字</span>
          </footer>
        </article>
      </div>

      <aside class="preview-panel">
        <div class="preview-title">
          <span class="type-mark large">
            <BookOpenText :size="22" />
          </span>
          <div>
            <h2>{{ selectedResource?.title || '选择一份资料' }}</h2>
            <p>{{ selectedResource ? '我的资源' : '从左侧列表查看内容' }}</p>
          </div>
        </div>

        <div v-if="selectedResource" class="preview-meta">
          <span>文档 ID：{{ selectedResource.doc_id }}</span>
          <span>创建时间：{{ formatDate(selectedResource.created_at, true) }}</span>
        </div>

        <div class="preview-content">
          <p v-if="selectedResource">{{ selectedResource.content || '这份资料暂时没有内容。' }}</p>
          <p v-else>点击任意资源后，资料正文会在这里展示。</p>
        </div>
      </aside>
    </div>

    <div v-else class="empty-state">
      <FileSearch :size="44" />
      <h2>还没有个人学习资源</h2>
      <p>{{ resources.length ? '换个关键词试试。' : '可以先导入一份学习资料。' }}</p>
      <router-link class="import-link" to="/study-import">
        <Upload :size="17" />
        <span>资料导入</span>
      </router-link>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  AlertCircle,
  BookOpenText,
  CalendarDays,
  FileSearch,
  FileText,
  RefreshCw,
  Search,
  Upload
} from 'lucide-vue-next'
import { getStudyResources } from '../api/apis'

const resources = ref([])
const selectedResource = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const currentUserToken = ref('')

const categoryLabelMap = {
  knowledge_point: '知识点讲解',
  exercise: '习题/题库',
  textbook: '教科书章节',
  note: '学习笔记',
  case_study: '实操案例',
  reference: '参考资料',
}

const normalizeResources = data => {
  const list = Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : []

  return list.map((item, index) => ({
    doc_id: String(item.doc_id || item.id || index),
    title: item.title || '',
    content: item.preview || item.content || '',
    category: item.category || '',
    categoryLabel: categoryLabelMap[item.category] || '',
    visibility: item.visibility || 'private',
    created_at: item.created_at || ''
  }))
}

const loadResources = async () => {
  loading.value = true
  errorMessage.value = ''
  currentUserToken.value = localStorage.getItem('token') || ''

  if (!currentUserToken.value) {
    resources.value = []
    selectedResource.value = null
    errorMessage.value = '请先登录，再查看我的学习资源。'
    loading.value = false
    return
  }

  try {
    const result = await getStudyResources({ visibility: 'private' })
    resources.value = normalizeResources(result).filter(item => item.visibility !== 'public')
    selectedResource.value = resources.value[0] || null
  } catch (error) {
    if (error?.response?.status === 401) {
      errorMessage.value = '请先登录，再查看我的学习资源。'
    } else {
      errorMessage.value =
        error?.response?.data?.detail ||
        error?.response?.data?.msg ||
        error?.message ||
        '我的学习资源加载失败，请稍后再试。'
    }
  } finally {
    loading.value = false
  }
}

const filteredResources = computed(() => {
  const searchText = keyword.value.toLowerCase()

  return resources.value.filter(resource => {
    return (
      !searchText ||
      resource.title.toLowerCase().includes(searchText) ||
      resource.content.toLowerCase().includes(searchText)
    )
  })
})

watch(filteredResources, list => {
  if (!list.length) {
    selectedResource.value = null
    return
  }

  if (!selectedResource.value || !list.some(item => item.doc_id === selectedResource.value.doc_id)) {
    selectedResource.value = list[0]
  }
})

const getExcerpt = content => {
  const text = String(content || '').replace(/\s+/g, ' ').trim()
  return text ? text.slice(0, 118) : '暂无正文内容'
}

const getWordCount = content => {
  return String(content || '').replace(/\s/g, '').length
}

const formatDate = (value, withTime = false) => {
  if (!value) return '未知时间'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return '未知时间'

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {})
  })
}

onMounted(loadResources)
</script>

<style scoped>
.resource-page {
  height: 100%;
  min-height: 0;
  padding: 26px 34px 30px;
  color: #163f8f;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

.resource-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.resource-header h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.15;
}

.summary {
  margin: 8px 0 0;
  color: #5f8fc3;
  font-size: 14px;
}

.header-actions,
.resource-tools,
.card-top,
.preview-title,
.preview-meta,
.resource-card footer {
  display: flex;
  align-items: center;
}

.header-actions {
  gap: 10px;
  flex-shrink: 0;
}

.icon-btn,
.import-link {
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #163f8f;
  color: #fafafa;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

.icon-btn {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.import-link {
  height: 42px;
  padding: 0 14px;
  gap: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.icon-btn:hover,
.import-link:hover {
  background: #5f8fc3;
  border-color: #5f8fc3;
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);
  transform: translateY(-1px);
}

.spinning {
  animation: spin 0.9s linear infinite;
}

.search-field {
  width: 100%;
  height: 48px;
  padding: 0 16px;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #ffffff;
  color: #5f8fc3;
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-field input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: #163f8f;
  font: inherit;
}

.notice {
  min-height: 52px;
  padding: 0 16px;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #c9dce9;
  display: flex;
  align-items: center;
  gap: 10px;
}

.resource-layout {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(340px, 0.62fr);
  gap: 18px;
  overflow: hidden;
}

.resource-list,
.resource-grid {
  min-height: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(245px, 1fr));
  align-content: start;
  gap: 14px;
  padding-right: 4px;
}

.resource-card,
.preview-panel,
.empty-state {
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #fafafa;
}

.resource-card {
  min-height: 210px;
  max-height: 240px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.resource-card:hover,
.resource-card.selected {
  background: #f5f9fc;
  border-color: #5f8fc3;
  box-shadow: 0 14px 28px rgba(22, 63, 143, 0.12);
  transform: translateY(-2px);
}

.card-top {
  justify-content: space-between;
  gap: 10px;
}

.type-mark {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #163f8f;
  color: #fafafa;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.type-mark.large {
  width: 44px;
  height: 44px;
}

.visibility,
.preview-meta span {
  background: #c9dce9;
  color: #163f8f;
  font-size: 12px;
  font-weight: 800;
}

.visibility {
  height: 26px;
  padding: 0 9px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
}

.resource-card h2 {
  margin: 0;
  color: #163f8f;
  font-size: 18px;
  line-height: 1.35;
  word-break: break-word;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card p {
  margin: 0;
  color: #5f8fc3;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.resource-card footer {
  margin-top: auto;
  justify-content: space-between;
  gap: 10px;
  color: #5f8fc3;
  font-size: 12px;
  flex-wrap: wrap;
}

.resource-card footer span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.preview-panel {
  min-height: 0;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.preview-title {
  align-items: flex-start;
  gap: 12px;
}

.preview-title h2 {
  margin: 0;
  color: #163f8f;
  font-size: 20px;
  line-height: 1.35;
}

.preview-title p {
  margin: 5px 0 0;
  color: #5f8fc3;
  font-size: 13px;
}

.preview-meta {
  flex-wrap: wrap;
  gap: 8px;
}

.preview-meta span {
  min-height: 28px;
  padding: 5px 9px;
  border-radius: 8px;
  word-break: break-all;
}

.preview-content {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #ffffff;
  padding: 18px;
}

.preview-content p {
  margin: 0;
  color: #163f8f;
  font-size: 14px;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-state {
  flex: 1;
  min-height: 320px;
  padding: 32px;
  color: #163f8f;
  background: #c9dce9;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 12px;
}

.empty-state h2 {
  margin: 0;
  font-size: 20px;
}

.empty-state p {
  margin: 0;
  color: #5f8fc3;
}

.skeleton-card span,
.skeleton-card strong,
.skeleton-card p {
  display: block;
  border-radius: 8px;
  background: linear-gradient(90deg, #c9dce9, #fafafa, #c9dce9);
  background-size: 220% 100%;
  animation: shimmer 1.3s ease-in-out infinite;
}

.skeleton-card span {
  width: 40px;
  height: 34px;
}

.skeleton-card strong {
  width: 70%;
  height: 22px;
}

.skeleton-card p {
  width: 100%;
  height: 16px;
}

.resource-list::-webkit-scrollbar,
.preview-content::-webkit-scrollbar {
  width: 9px;
}

.resource-list::-webkit-scrollbar-track,
.preview-content::-webkit-scrollbar-track {
  background: #c9dce9;
  border-radius: 999px;
}

.resource-list::-webkit-scrollbar-thumb,
.preview-content::-webkit-scrollbar-thumb {
  background: #163f8f;
  border: 2px solid #c9dce9;
  border-radius: 999px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes shimmer {
  to {
    background-position: -220% 0;
  }
}

@media (max-width: 1080px) {
  .resource-page {
    height: auto;
    min-height: 100%;
    overflow: visible;
  }

  .resource-header,
  .resource-layout {
    grid-template-columns: 1fr;
  }

  .resource-layout,
  .resource-list {
    overflow: visible;
  }

  .preview-panel {
    min-height: 460px;
  }
}
</style>
