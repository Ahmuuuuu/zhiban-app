<template>
  <main class="resource-center-page">
    <header class="center-header">
      <router-link class="home-pill" to="/">
        首页
      </router-link>

      <div class="title-block">
        <h1>资源中心</h1>
      </div>

      <label class="search-field">
        <Search :size="18" />
        <input v-model.trim="keyword" type="search" placeholder="搜索框" />
      </label>

      <button class="send-search" type="button">发送</button>

      <div class="header-actions">
        <button class="icon-btn refresh-btn" type="button" :disabled="loading" title="刷新资源" @click="loadResources">
          <RefreshCw :size="24" :class="{ spinning: loading }" />
        </button>
        <router-link class="import-link" to="/study-import">
          资料导入
        </router-link>
        <UserAccountButton
          variant="dark"
          logged-out-name="未登录"
          @login="loadResources"
        />
      </div>
    </header>

    <div v-if="errorMessage" class="notice">
      <AlertCircle :size="18" />
      <span>{{ errorMessage }}</span>
    </div>

    <section class="resource-shell">
      <aside class="category-panel">
        <h2>分类</h2>
        <button
          v-for="category in categories"
          :key="category"
          type="button"
          :class="{ active: activeCategory === category }"
          @click="switchCategory(category)"
        >
          {{ category }}
        </button>
      </aside>

      <section class="resource-list" aria-label="公共资源列表">
        <!-- 文档子分类 -->
        <div v-if="activeCategory === '文档'" class="sub-category-bar">
          <button
            v-for="sub in subCategories"
            :key="sub.value"
            type="button"
            class="sub-cat-btn"
            :class="{ active: activeSubCategory === sub.value }"
            @click="activeSubCategory = sub.value"
          >
            {{ sub.label }}
          </button>
        </div>

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
            :class="{ selected: selectedResource?.doc_id === resource.doc_id }"
            @click="openResourcePreview(resource)"
          >
            <div class="card-top">
              <span class="type-mark">
                <FileText :size="18" />
              </span>
              <span class="visibility">{{ resource.categoryLabel || '公开资源' }}</span>
            </div>

            <h2>{{ resource.title || '未命名资料' }}</h2>
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
            <div class="card-top">
              <span class="type-mark soft">
                <FileText :size="18" />
              </span>
              <span class="visibility">等待资源</span>
            </div>
            <h2>资源卡片</h2>
            <p>后端传入公共资源后，会在这里展示标题、摘要、时间和字数。</p>
          </article>
        </template>
      </section>

      <aside class="hot-panel">
        <h2>热门资源</h2>
        <div class="hot-list">
          <button
            v-for="resource in hotResources"
            :key="resource.doc_id"
            type="button"
            @click="openResourcePreview(resource)"
          >
            {{ resource.title || '未命名资源' }}
          </button>
          <p v-if="!hotResources.length" class="hot-empty">暂无热门资源</p>
        </div>

        <button class="share-btn" type="button">我要分享</button>
      </aside>
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
import {
  AlertCircle,
  FileText,
  RefreshCw,
  Search
} from 'lucide-vue-next'
import { getStudyResources } from '../api/apis'
import { hydrateSavedResourceRefs } from '../utils/savedResources'
import UserAccountButton from '../components/UserAccountButton.vue'

const resources = ref([])
const selectedResource = ref(null)
const previewOpen = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const categories = ['文档', 'ppt', '视频', '题库', '思维导图']
const activeCategory = ref(categories[0])
const activeSubCategory = ref('all')

// 与后端 KB_CATEGORIES 对齐
const subCategories = [
  { value: 'all', label: '全部' },
  { value: 'knowledge_point', label: '知识点讲解' },
  { value: 'exercise', label: '习题/题库' },
  { value: 'textbook', label: '教科书章节' },
  { value: 'note', label: '学习笔记' },
  { value: 'case_study', label: '实操案例' },
  { value: 'reference', label: '参考资料' },
]

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

  try {
    const result = await getStudyResources({ visibility: 'public' })
    const backendResources = normalizeResources(result).filter(item => item.visibility === 'public')
    const generatedResources = await hydrateSavedResourceRefs('public')
    resources.value = [...generatedResources, ...backendResources]
    selectedResource.value = resources.value[0] || null
  } catch (error) {
    if (error?.response?.status === 401) {
      errorMessage.value = '请先登录，再查看资源中心。'
    } else {
      errorMessage.value =
        error?.response?.data?.detail ||
        error?.response?.data?.msg ||
        error?.message ||
        '资源中心加载失败，请稍后再试。'
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
    ) && matchesCategory(resource)
  })
})

const hotResources = computed(() => {
  return resources.value.slice(0, 5)
})

const openResourcePreview = resource => {
  selectedResource.value = resource
  previewOpen.value = true
}

const closeResourcePreview = () => {
  previewOpen.value = false
}

const matchesCategory = resource => {
  const cat = activeCategory.value

  if (cat === '文档') {
    // 文档按子分类匹配
    if (activeSubCategory.value === 'all') return true
    return resource.category === activeSubCategory.value
  }

  // 其他分类：按文件类型/关键词匹配
  const resourceType = String(resource.type || resource.category || '').toLowerCase()
  const categoryMap = {
    ppt: ['ppt', 'pptx', 'slide'],
    视频: ['video', 'mp4', 'mov', 'avi'],
    题库: ['quiz', 'question', 'exam', '题'],
    思维导图: ['mind', 'map', 'xmind', '思维']
  }
  return (categoryMap[cat] || []).some(type => resourceType.includes(type))
}

// 切换一级分类时重置子分类
const switchCategory = (cat) => {
  activeCategory.value = cat
  activeSubCategory.value = 'all'
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

const getWordCount = content => {
  return String(content || '').replace(/\s/g, '').length
}

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
.resource-center-page {
  width: 100vw;
  height: 100vh;
  padding: 26px 34px 30px;
  background: #fdfcf7;
  color: #163f8f;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

.center-header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
}

.back-btn,
.icon-btn,
.import-link {
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #fafafa;
  color: #163f8f;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

.back-btn,
.import-link {
  height: 42px;
  padding: 0 14px;
  gap: 8px;
  font-size: 14px;
  font-weight: 800;
}

.icon-btn {
  width: 42px;
  height: 42px;
}

.back-btn:hover,
.icon-btn:hover,
.import-link:hover {
  background: #c9dce9;
  border-color: #5f8fc3;
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);
  transform: translateY(-1px);
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
}

.eyebrow {
  margin: 0 0 6px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.center-header h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.15;
}

.center-header p:last-child {
  margin: 8px 0 0;
  color: #5f8fc3;
  font-size: 14px;
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

.notice,
.empty-state {
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #c9dce9;
}

.notice {
  min-height: 52px;
  padding: 0 16px;
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
.preview-panel {
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

@media (max-width: 980px) {
  .resource-center-page {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .center-header,
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

/* 草图版资源中心布局 */
.resource-center-page {
  width: 100vw;
  height: 100vh;
  padding: 28px 34px 28px;
  background:
    radial-gradient(ellipse 72% 44% at 10% 0%, rgba(209, 244, 250, 0.46), transparent 70%),
    linear-gradient(135deg, #fafafa 0%, rgb(237, 249, 252) 52%, #fafafa 100%);
  color: #163f8f;
  gap: 20px;
  overflow: hidden;
}

.center-header {
  display: grid;
  grid-template-columns: 62px 150px minmax(280px, 1fr) 64px auto;
  align-items: center;
  gap: 14px;
}

.home-pill,
.import-link,
.send-search,
.icon-btn,
.category-panel,
.resource-card,
.hot-panel {
  border: 1px solid rgba(22, 63, 143, 0.16);
  background: rgba(250, 250, 250, 0.78);
  color: #163f8f;
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
}

.home-pill {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
}

.title-block h1 {
  margin: 0;
  color: #163f8f;
  font-size: 28px;
  font-weight: 900;
  letter-spacing: 0;
}

.search-field {
  width: 100%;
  height: 42px;
  padding: 0 14px;
  border: 2px solid rgba(22, 63, 143, 0.86);
  border-radius: 18px;
  background: rgba(250, 250, 250, 0.88);
  color: #5f8fc3;
  box-shadow: none;
}

.search-field input::placeholder {
  color: rgba(22, 63, 143, 0.58);
}

.send-search {
  min-width: 76px;
  height: 42px;
  padding: 0 18px;
  border-radius: 18px;
  border: 2px solid rgba(22, 63, 143, 0.86);
  background: rgba(250, 250, 250, 0.88);
  color: #163f8f;
  box-shadow: none;
  font-weight: 800;
  cursor: pointer;
}

.header-actions {
  justify-content: flex-end;
  gap: 12px;
}

.icon-btn {
  width: 42px;
  height: 42px;
  border-radius: 18px;
}

.refresh-btn {
  color: #163f8f;
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}

.import-link {
  min-width: 82px;
  height: 46px;
  padding: 0 14px;
  border-radius: 22px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 800;
  border-color: rgba(22, 63, 143, 0.92);
  background: #163f8f;
  color: #fafafa;
  box-shadow:
    0 14px 30px rgba(22, 63, 143, 0.18),
    inset 0 1px 0 rgba(250, 250, 250, 0.18);
}

.center-header :deep(.account-entry.dark) {
  min-width: 128px;
  max-width: 156px;
  height: 46px;
  min-height: 46px;
  padding: 0 14px 0 7px;
  border-radius: 24px;
}

.center-header :deep(.account-entry.dark .account-avatar) {
  width: 32px;
  height: 32px;
  font-size: 13px;
}

.center-header :deep(.account-entry.dark .account-text strong),
.center-header :deep(.account-entry.dark .account-text small) {
  max-width: 86px;
}

.home-pill:hover,
.import-link:hover,
.send-search:hover,
.icon-btn:hover {
  transform: translateY(-2px);
  border-color: #5f8fc3;
  background: #c9dce9;
}

.import-link:hover {
  background: #1d5dab;
  border-color: #1d5dab;
  color: #fafafa;
}

.resource-shell {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: 214px minmax(0, 1fr) 250px;
  gap: 42px;
  overflow: hidden;
}

.category-panel {
  min-height: 0;
  border-radius: 28px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.category-panel h2 {
  position: relative;
  margin: 0;
  height: 52px;
  border-bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #163f8f;
  font-size: 21px;
}

.category-panel button {
  position: relative;
  width: calc(100% - 28px);
  height: 40px;
  margin: 7px 14px 0;
  border: 0;
  border-radius: 999px;
  background: rgba(250, 250, 250, 0.48);
  color: #163f8f;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.category-panel h2::after,
.category-panel button::after {
  content: "";
  position: absolute;
  left: 24px;
  right: 24px;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background:
    linear-gradient(to right, transparent 0%, rgba(201, 220, 233, 0.34) 24%, rgba(201, 220, 233, 0.72) 48%, rgba(201, 220, 233, 0.72) 52%, rgba(201, 220, 233, 0.34) 76%, transparent 100%),
    linear-gradient(to right, transparent 0%, transparent 42%, rgba(201, 220, 233, 0.9) 42%, rgba(201, 220, 233, 0.9) 58%, transparent 58%, transparent 100%);
  opacity: 0.66;
}

.category-panel button:hover,
.category-panel button.active {
  background: rgba(201, 220, 233, 0.72);
  color: #163f8f;
}

.resource-list {
  min-height: 0;
  padding: 18px 6px 10px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  grid-auto-rows: auto;
  align-content: start;
  gap: 28px 48px;
}

/* 文档子分类栏 */
.sub-category-bar {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  min-height: 42px;
  padding: 4px 0 10px;
}

.sub-cat-btn {
  height: 38px;
  padding: 0 20px;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 999px;
  background: rgba(250, 250, 250, 0.66);
  color: rgba(22, 63, 143, 0.7);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.sub-cat-btn:hover {
  background: #c9dce9;
  border-color: #5f8fc3;
}

.sub-cat-btn.active {
  background: rgba(201, 220, 233, 0.78);
  color: #163f8f;
  border-color: rgba(95, 143, 195, 0.42);
}

.resource-card {
  min-height: 0;
  max-height: none;
  height: 178px;
  padding: 14px 15px 16px;
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.92), rgba(237, 249, 252, 0.84)),
    #fafafa;
  cursor: pointer;
  position: relative;
  gap: 8px;
  overflow: hidden;
}

.resource-card::after {
  content: "";
  position: absolute;
  right: 16px;
  bottom: 14px;
  width: 36px;
  height: 8px;
  border-radius: 999px;
  background: #f0efdd;
  opacity: 0.82;
}

.resource-card:hover,
.resource-card.selected {
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.96), rgba(201, 220, 233, 0.74)),
    #fafafa;
  border-color: #5f8fc3;
  transform: translateY(-4px);
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
}

.type-mark.soft {
  background: #5f8fc3;
}

.visibility {
  background: #c9dce9;
  color: #163f8f;
  height: 24px;
  padding: 0 8px;
  font-size: 11px;
  white-space: nowrap;
  flex-shrink: 0;
}

.resource-card h2 {
  margin: 2px 0 0;
  font-size: 16px;
  line-height: 1.28;
  -webkit-line-clamp: 2;
  flex-shrink: 0;
}

.resource-card p {
  font-size: 12px;
  line-height: 1.55;
  -webkit-line-clamp: 2;
  min-height: 38px;
}

.resource-card footer {
  margin-top: auto;
  font-size: 11px;
  line-height: 1.2;
  position: relative;
  z-index: 1;
}

.resource-actions,
.resource-fullscreen__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  position: relative;
  z-index: 2;
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

.resource-action.primary {
  min-height: 38px;
  padding: 0 14px;
}

.placeholder-card {
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.8), rgba(237, 249, 252, 0.68)),
    #fafafa;
}

.hot-panel {
  position: relative;
  min-height: 0;
  padding: 10px 0 22px;
  border-color: transparent;
  border-left: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  display: flex;
  flex-direction: column;
}

.hot-panel::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 6px;
  width: 3px;
  border-radius: 999px;
  background:
    linear-gradient(to bottom, transparent 0%, rgba(201, 220, 233, 0.34) 20%, rgba(201, 220, 233, 0.68) 48%, rgba(201, 220, 233, 0.68) 52%, rgba(201, 220, 233, 0.34) 80%, transparent 100%),
    linear-gradient(to bottom, transparent 0%, transparent 38%, rgba(201, 220, 233, 0.86) 38%, rgba(201, 220, 233, 0.86) 62%, transparent 62%, transparent 100%);
  opacity: 0.72;
}

.hot-panel h2 {
  margin: 0 0 16px;
  padding-left: 26px;
  color: #163f8f;
  font-size: 18px;
}

.hot-list {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

.hot-list button,
.hot-list span {
  height: 2px;
  margin-left: 26px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(to right, transparent, rgba(201, 220, 233, 0.74) 18%, rgba(201, 220, 233, 0.74) 82%, transparent);
}

.hot-list button {
  height: auto;
  min-height: 28px;
  padding: 4px 0;
  text-align: left;
  color: #163f8f;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  background: transparent;
  border-bottom: 1px solid rgba(201, 220, 233, 0.7);
}

.share-btn {
  align-self: flex-end;
  min-width: 124px;
  height: 34px;
  border: 1px solid rgba(22, 63, 143, 0.32);
  border-radius: 8px;
  background: rgba(250, 250, 250, 0.82);
  color: #163f8f;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
}

.notice {
  position: fixed;
  left: 50%;
  top: 96px;
  z-index: 5;
  transform: translateX(-50%);
  background: #c9dce9;
}

@media (max-width: 1100px) {
  .center-header {
    grid-template-columns: auto 1fr;
  }

  .search-field,
  .send-search,
  .header-actions {
    grid-column: 1 / -1;
  }

  .resource-shell {
    grid-template-columns: 170px minmax(0, 1fr);
    gap: 22px;
  }

  .hot-panel {
    display: none;
  }

  .resource-list {
    grid-template-columns: repeat(2, minmax(180px, 1fr));
    gap: 24px;
  }
}

@media (max-width: 720px) {
  .resource-center-page {
    height: auto;
    min-height: 100vh;
    overflow: visible;
    padding: 18px;
  }

  .resource-shell {
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .category-panel {
    flex-direction: row;
    overflow-x: auto;
    border-radius: 18px;
  }

  .category-panel h2,
  .category-panel button {
    min-width: 96px;
    border-bottom: 0;
    border-right: 1px solid rgba(201, 220, 233, 0.44);
  }

  .category-panel button {
    width: auto;
    margin: 6px 8px;
    padding: 0 16px;
  }

  .resource-list {
    overflow: visible;
    grid-template-columns: 1fr;
  }
}
</style>
