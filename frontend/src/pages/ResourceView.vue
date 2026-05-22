<template>
  <main class="resource-page">
    <header class="resource-header">
      <div class="title-block">
        <p>My Resources</p>
        <h1>我的学习资源</h1>
      </div>

      <div class="header-actions">
        <button class="icon-btn refresh-btn" type="button" :disabled="loading" title="刷新资源" @click="loadResources">
          <RefreshCw :size="22" :class="{ spinning: loading }" />
        </button>
        <router-link class="import-link" to="/resources">资源中心</router-link>
        <router-link class="import-link primary" to="/study-import">资料导入</router-link>
      </div>
    </header>

    <div v-if="errorMessage" class="notice">
      <AlertCircle :size="18" />
      <span>{{ errorMessage }}</span>
    </div>

    <section class="resource-shell">
      <section class="resource-list" aria-label="我的资源列表">
        <template v-if="loading">
          <article v-for="item in 9" :key="item" class="resource-card skeleton-card">
            <span></span>
            <strong></strong>
            <p></p>
          </article>
        </template>

        <template v-else-if="filteredResources.length">
          <article
            v-for="resource in filteredResources"
            :key="resource.doc_id"
            class="resource-card"
            @click="openResourcePreview(resource)"
          >
            <div class="card-top">
              <span class="type-mark">
                <FileText :size="18" />
              </span>
              <span class="visibility">{{ resource.categoryLabel || '我的资源' }}</span>
            </div>

            <h2>{{ resource.title || '未命名资源' }}</h2>
            <p>{{ getExcerpt(resource.content) }}</p>

            <footer>
              <span>{{ formatDate(resource.created_at) }}</span>
              <span>{{ getWordCount(resource.content) }} 字</span>
            </footer>
            <div class="resource-actions">
              <router-link
                v-if="resource.quizId"
                class="resource-action"
                :to="`/question-bank/${resource.quizId}`"
                @click.stop
              >
                开始练习
              </router-link>
              <a
                v-if="resource.downloadUrl"
                class="resource-action"
                :href="resource.downloadUrl"
                target="_blank"
                rel="noopener noreferrer"
                @click.stop
              >
                下载原文件
              </a>
            </div>
          </article>
        </template>

        <template v-else>
          <article class="empty-state">
            <FileSearch :size="44" />
            <h2>还没有个人学习资源</h2>
            <p>{{ resources.length ? '换个分类试试。' : '可以先导入一份学习资料。' }}</p>
            <router-link class="import-link primary" to="/study-import">资料导入</router-link>
          </article>
        </template>
      </section>

    </section>

    <Teleport to="body">
      <section v-if="previewOpen && selectedResource" class="resource-fullscreen" @click.self="closeResourcePreview">
        <article class="resource-fullscreen__panel">
          <header class="resource-fullscreen__header">
            <div>
              <span>{{ selectedResource.categoryLabel || '学习资源' }}</span>
              <h2>{{ selectedResource.title || '未命名资源' }}</h2>
            </div>
            <button type="button" aria-label="关闭预览" @click="closeResourcePreview">×</button>
          </header>

          <div class="resource-fullscreen__meta">
            <span>{{ formatDate(selectedResource.created_at, true) }}</span>
            <span>{{ getWordCount(selectedResource.content) }} 字</span>
          </div>

          <div class="resource-fullscreen__content">
            <p>{{ selectedResource.content || '暂无正文内容' }}</p>
          </div>
        </article>
      </section>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  AlertCircle,
  FileSearch,
  FileText,
  RefreshCw
} from 'lucide-vue-next'
import { getStudyResources } from '../api/apis'
import { hydrateSavedResourceRefs } from '../utils/savedResources'

const route = useRoute()
const resources = ref([])
const selectedResource = ref(null)
const previewOpen = ref(false)
const loading = ref(false)
const errorMessage = ref('')


const categoryLabelMap = {
  knowledge_point: '知识点讲解',
  exercise: '习题/题库',
  textbook: '教科书章节',
  note: '学习笔记',
  case_study: '实操案例',
  reference: '参考资料',
}

const activeCategory = computed(() => String(route.query.category || 'document'))
const activeSubCategory = computed(() => String(route.query.sub || 'all'))
const normalizeResources = data => {
  const list = Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : []

  return list.map((item, index) => ({
    doc_id: String(item.doc_id || item.id || index),
    title: item.title || '',
    content: item.preview || item.content || '',
    type: item.type || item.file_type || '',
    category: item.category || '',
    categoryLabel: categoryLabelMap[item.category] || '',
    visibility: item.visibility || 'private',
    created_at: item.created_at || item.createdAt || '',
    previewUrl: item.previewUrl || item.preview_url || '',
    downloadUrl: item.downloadUrl || item.download_url || ''
  }))
}

const loadResources = async () => {
  loading.value = true
  errorMessage.value = ''

  if (!localStorage.getItem('token')) {
    resources.value = []
    selectedResource.value = null
    errorMessage.value = '请先登录，再查看我的学习资源。'
    loading.value = false
    return
  }

  try {
    const result = await getStudyResources({ visibility: 'private' })
    const backendResources = normalizeResources(result).filter(item => item.visibility !== 'public')
    const generatedResources = await hydrateSavedResourceRefs('private')
    resources.value = [...generatedResources, ...backendResources]
    selectedResource.value = resources.value[0] || null
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.response?.data?.msg ||
      error?.message ||
      '我的学习资源加载失败，请稍后再试。'
  } finally {
    loading.value = false
  }
}

const filteredResources = computed(() => resources.value.filter(matchesCategory))

const openResourcePreview = resource => {
  selectedResource.value = resource
  previewOpen.value = true
}

const closeResourcePreview = () => {
  previewOpen.value = false
}

const matchesCategory = resource => {
  const cat = activeCategory.value

  if (cat === 'document') {
    if (activeSubCategory.value === 'all') return true
    return resource.category === activeSubCategory.value
  }

  const resourceType = String(resource.type || resource.category || resource.title || '').toLowerCase()
  const categoryMap = {
    ppt: ['ppt', 'pptx', 'slide', 'reference'],
    video: ['video', 'mp4', 'mov', 'avi'],
    quiz: ['quiz', 'question', 'exam', 'exercise', '题'],
    mindmap: ['mind', 'map', 'xmind', '思维', 'note']
  }
  return (categoryMap[cat] || []).some(type => resourceType.includes(type))
}

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

const getWordCount = content => String(content || '').replace(/\s/g, '').length

const resourceMetric = resource => {
  const type = String(resource.type || resource.category || '').toLowerCase()
  if (resource.quizId || type.includes('exercise') || type.includes('quiz')) return '题库资源'
  if (resource.downloadUrl) return `${type || 'file'} 文件`
  return `${getWordCount(resource.content)} 字`
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
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 24px;
  color: #163f8f;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

.resource-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.title-block p {
  margin: 0 0 5px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.title-block h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.15;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.icon-btn,
.import-link,
.resource-card,
.empty-state {
  border: 1px solid rgba(22, 63, 143, 0.16);
  background: rgba(250, 250, 250, 0.78);
  color: #163f8f;
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
}

.icon-btn {
  width: 42px;
  height: 42px;
  border-radius: 18px;
  cursor: pointer;
}

.refresh-btn {
  color: #163f8f;
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}

.import-link {
  min-width: 82px;
  height: 42px;
  padding: 0 14px;
  border-radius: 20px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.import-link.primary {
  border-color: rgba(22, 63, 143, 0.92);
  background: #163f8f;
  color: #fafafa;
}

.icon-btn:hover,
.import-link:hover {
  transform: translateY(-2px);
  border-color: #5f8fc3;
  background: #c9dce9;
}

.notice {
  min-height: 48px;
  padding: 0 16px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 18px;
  background: #c9dce9;
  display: flex;
  align-items: center;
  gap: 10px;
}

.resource-shell {
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.resource-list {
  min-height: 0;
  padding: 8px 4px 10px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  align-content: start;
  gap: 22px;
}

.resource-card {
  height: 178px;
  padding: 14px 15px 16px;
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.92), rgba(237, 249, 252, 0.84)),
    #fafafa;
  cursor: pointer;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.resource-card:hover {
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.96), rgba(201, 220, 233, 0.74)),
    #fafafa;
  border-color: #5f8fc3;
  transform: translateY(-4px);
}

.card-top,
.resource-card footer {
  display: flex;
  align-items: center;
}

.card-top {
  justify-content: space-between;
  gap: 8px;
  flex-shrink: 0;
}

.type-mark {
  width: 30px;
  height: 30px;
  border-radius: 12px;
  background: #163f8f;
  color: #fafafa;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.visibility {
  background: #c9dce9;
  color: #163f8f;
  font-size: 11px;
  font-weight: 800;
}

.visibility {
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.resource-card h2 {
  margin: 2px 0 0;
  color: #163f8f;
  font-size: 16px;
  line-height: 1.28;
  word-break: break-word;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card p {
  margin: 0;
  min-height: 38px;
  color: #5f8fc3;
  font-size: 12px;
  line-height: 1.55;
  word-break: break-word;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card footer {
  margin-top: auto;
  justify-content: space-between;
  gap: 10px;
  color: #5f8fc3;
  font-size: 11px;
}

.resource-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.resource-action {
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(22, 63, 143, 0.18);
  border-radius: 999px;
  background: #163f8f;
  color: #fafafa;
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  font-size: 12px;
  font-weight: 800;
}


.empty-state {
  grid-column: 1 / -1;
  min-height: 320px;
  padding: 32px;
  border-radius: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 12px;
}

.empty-state h2,
.empty-state p {
  margin: 0;
}

.empty-state p {
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

.resource-list::-webkit-scrollbar {
  width: 8px;
}

.resource-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(95, 143, 195, 0.45);
}

.spinning {
  animation: spin 0.9s linear infinite;
}

.resource-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 3000;
  padding: clamp(18px, 4vw, 46px);
  background: rgba(12, 28, 58, 0.34);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(16px) saturate(135%);
  -webkit-backdrop-filter: blur(16px) saturate(135%);
}

.resource-fullscreen__panel {
  width: min(1120px, 100%);
  height: min(780px, 100%);
  min-height: 0;
  padding: clamp(20px, 3vw, 34px);
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 30px 90px rgba(22, 63, 143, 0.24);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.resource-fullscreen__header,
.resource-fullscreen__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.resource-fullscreen__header span,
.resource-fullscreen__meta {
  color: #5f8fc3;
  font-size: 13px;
  font-weight: 800;
}

.resource-fullscreen__header h2 {
  margin: 5px 0 0;
  color: #163f8f;
  font-size: clamp(22px, 3vw, 34px);
  line-height: 1.2;
}

.resource-fullscreen__header button {
  width: 44px;
  height: 44px;
  border: 1px solid rgba(201, 220, 233, 0.9);
  border-radius: 18px;
  background: #fafafa;
  color: #163f8f;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
}

.resource-fullscreen__content {
  min-height: 0;
  flex: 1;
  padding: 22px;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 24px;
  background: rgba(237, 249, 252, 0.48);
  overflow: auto;
}

.resource-fullscreen__content p {
  margin: 0;
  color: #1f2d43;
  font-size: 16px;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
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

@media (max-width: 1120px) {
  .resource-header,
  .resource-shell {
    grid-template-columns: 1fr;
  }

  .resource-page,
  .resource-shell,
  .resource-list {
    overflow: visible;
  }

  .resource-page {
    height: auto;
  }
}
</style>
