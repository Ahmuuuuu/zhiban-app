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
                <FileImage v-if="resource.type === 'image'" :size="18" />
                <Presentation v-else-if="isPptResource(resource)" :size="18" />
                <GitBranch v-else-if="isMindmapResource(resource)" :size="18" />
                <FileText v-else :size="18" />
              </span>
              <span class="visibility">{{ resource.categoryLabel || '我的资源' }}</span>
            </div>

            <div v-if="resource.type === 'image' && resource.previewUrl" class="image-thumb">
              <img :src="resource.previewUrl" :alt="resource.title" loading="lazy" @error="handleImageError($event)" />
            </div>

            <h2>{{ resource.title || '未命名资源' }}</h2>
            <p>{{ getResourceExcerpt(resource) }}</p>

            <footer>
              <span>{{ formatDate(resource.created_at) }}</span>
              <span v-if="resource.type === 'image'">图片</span>
              <span v-else>{{ getWordCount(resource.content) }} 字</span>
            </footer>
            <div class="resource-actions">
              <button
                v-if="isQuizResource(resource)"
                class="resource-action"
                type="button"
                @click.stop="startResourceQuiz(resource)"
              >
                开始练习
              </button>
              <button
                v-if="resource.downloadUrl"
                class="resource-action"
                type="button"
                @click.stop="downloadResource(resource)"
              >
                下载原文件
              </button>
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
            <template v-if="selectedResource.type === 'image' && selectedResource.previewUrl">
              <img
                class="preview-image"
                :src="selectedResource.previewUrl"
                :alt="selectedResource.title"
                @error="handleImageError"
              />
            </template>
            <template v-else-if="isMindmapResource(selectedResource)">
              <MindmapPreview
                :content="selectedResource.fullContent || selectedResource.content"
                :title="selectedResource.title"
              />
              <div class="resource-fullscreen__actions">
                <button
                  v-if="selectedResource.downloadUrl"
                  class="file-download-btn"
                  type="button"
                  @click="downloadResource(selectedResource)"
                >
                  下载思维导图
                </button>
              </div>
            </template>
            <template v-else-if="isPptResource(selectedResource)">
              <div v-if="selectedResource.previewUrl" class="file-preview-wrap">
                <img
                  class="preview-image"
                  :src="selectedResource.previewUrl"
                  :alt="selectedResource.title"
                  @error="handleImageError"
                />
              </div>
              <div class="file-placeholder-block">
                <Presentation v-if="isPptResource(selectedResource)" :size="48" />
                <GitBranch v-else :size="48" />
                <p>{{ selectedResource.title || (isPptResource(selectedResource) ? 'PPT 文件' : '思维导图') }}</p>
                <button
                  v-if="selectedResource.downloadUrl"
                  class="file-download-btn"
                  type="button"
                  @click="downloadResource(selectedResource)"
                >
                  下载{{ isPptResource(selectedResource) ? ' PPT 文件' : '思维导图' }}
                </button>
              </div>
            </template>
            <p v-else>{{ selectedResource.content || '暂无正文内容' }}</p>
          </div>
        </article>
      </section>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  FileImage,
  FileSearch,
  Presentation,
  FileText,
  GitBranch,
  RefreshCw
} from 'lucide-vue-next'
import { downloadWithToken, getGeneratedImages, getGeneratedResource, getGeneratedResources, getStudyResources, resolveApiUrl } from '../api/apis'
import { upsertQuizSet } from '../utils/quizBank'
import MindmapPreview from '../components/MindmapPreview.vue'

const route = useRoute()
const router = useRouter()
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

const normalizeGeneratedResources = data => {
  const list = Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : []

  return list.map(item => {
    const resourceType = item.resource_type || item.file_type || item.fileType || 'resource'
    const resourceId = item.resource_id || item.resourceId || item.id
    const filename = item.filename || `${item.topic || item.title || '生成资源'}_${resourceType}`

    const resourceText = String(`${resourceType} ${filename} ${item.topic || ''} ${item.title || ''}`).toLowerCase()
    const isQuiz = resourceText.includes('exercise') || resourceText.includes('quiz')
    const isMindmap = resourceText.includes('mindmap') || resourceText.includes('mind_map') || resourceText.includes('mind-map') || resourceText.includes('xmind')

    return {
      doc_id: `generated-${resourceId}`,
      source: 'generated',
      sourceId: String(resourceId || ''),
      title: item.title || item.topic || fileTitleWithoutExtension(filename),
      filename,
      content: isQuiz ? '这是一套生成题目，进入题库后开始练习。' : (item.preview || item.preview_content || item.content || ''),
      type: isMindmap ? 'mindmap' : resourceType,
      category: isQuiz ? 'exercise' : isMindmap ? 'mindmap' : 'reference',
      categoryLabel: isQuiz ? '习题/题库' : 'AI 生成',
      categoryLabel: isMindmap ? '思维导图' : (isQuiz ? '习题/题库' : 'AI 生成'),
      visibility: item.visibility || 'private',
      quizId: item.quiz_id || item.quizId || '',
      sessionId: item.session_id || item.sessionId || '',
      created_at: item.created_at || item.createdAt || '',
      previewUrl: resolveApiUrl(item.preview_url || item.previewUrl || ''),
      downloadUrl: resolveApiUrl(item.download_url || item.downloadUrl || (resourceId ? `/resource/${resourceId}/download` : ''))
    }
  })
}

const normalizeGeneratedImages = data => {
  const list = Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : data?.images || data?.image_list || []
  return (Array.isArray(list) ? list : []).map(item => {
    const imageId = String(item.image_id || item.imageId || item.id || '')
    const url = item.url || item.image_url || item.imageUrl || item.preview_url || item.previewUrl || ''
    return {
      doc_id: `image-${imageId}`,
      source: 'generated',
      sourceId: imageId,
      title: item.title || item.prompt || fileTitleWithoutExtension(item.filename || item.file_name || item.name || ''),
      filename: item.filename || item.file_name || item.name || `image-${imageId || Date.now()}.jpg`,
      content: item.prompt || item.content || item.preview || '',
      type: 'image',
      category: 'reference',
      categoryLabel: 'AI 生成图片',
      visibility: 'private',
      quizId: '',
      sessionId: '',
      created_at: item.created_at || item.createdAt || '',
      previewUrl: resolveApiUrl(url),
      downloadUrl: resolveApiUrl(item.download_url || item.downloadUrl || url || (imageId ? `/image/${imageId}/download` : ''))
    }
  })
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
    const generatedResult = await getGeneratedResources()
    const generatedBackendResources = normalizeGeneratedResources(generatedResult)
    const imageResult = await getGeneratedImages()
    const imageResources = normalizeGeneratedImages(imageResult)
    resources.value = [...imageResources, ...generatedBackendResources, ...backendResources]
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

const openResourcePreview = async resource => {
  selectedResource.value = resource
  previewOpen.value = true

  if (resource?.source === 'generated' && resource?.sourceId && !resource?.fullContent) {
    try {
      const detail = await getGeneratedResource(resource.sourceId)
      const data = detail?.data || detail || {}
      const fullContent = data.content || data.preview || resource.content || ''
      selectedResource.value = {
        ...resource,
        content: fullContent,
        fullContent,
        filename: data.filename || resource.filename,
        type: isMindmapResource(resource) ? 'mindmap' : (data.resource_type || data.file_type || resource.type),
        sessionId: data.session_id || resource.sessionId || '',
        downloadUrl: resolveApiUrl(data.download_url || data.downloadUrl || resource.downloadUrl)
      }
    } catch (error) {
      console.error('加载资源详情失败：', error)
    }
  }
}

const closeResourcePreview = () => {
  previewOpen.value = false
}

const fileTitleWithoutExtension = filename => String(filename || '生成资源').replace(/\.[^.\\/]+$/, '')

const isQuizResource = resource => {
  const text = String(`${resource?.type || ''} ${resource?.category || ''} ${resource?.filename || ''} ${resource?.title || ''}`).toLowerCase()
  return Boolean(resource?.quizId) || text.includes('exercise') || text.includes('quiz') || text.includes('question') || text.includes('exam') || text.includes('题')
}

const isPptResource = resource => {
  const text = String(`${resource?.type || ''} ${resource?.category || ''} ${resource?.filename || ''} ${resource?.title || ''}`).toLowerCase()
  return text.includes('ppt') || text.includes('pptx') || text.includes('slide') || text.includes('演示')
}

const isMindmapResource = resource => {
  const text = String(`${resource?.type || ''} ${resource?.category || ''} ${resource?.filename || ''} ${resource?.title || ''}`).toLowerCase()
  return text.includes('mindmap') || text.includes('mind_map') || text.includes('mind-map') || text.includes('脑图') || text.includes('思维导图')
}

const downloadResource = async resource => {
  try {
    await downloadWithToken(resource.downloadUrl, resource.filename || `${resource.title || 'resource'}.md`)
  } catch (error) {
    console.error('下载资源失败：', error)
    window.alert('下载失败，请确认登录状态和后端服务是否正常。')
  }
}

const startResourceQuiz = async resource => {
  if (resource.quizId) {
    router.push(`/question-bank/${resource.quizId}`)
    return
  }

  if (!resource.sourceId) return

  try {
    const detail = await getGeneratedResource(resource.sourceId)
    const data = detail?.data || detail || {}
    const quiz = upsertQuizSet({
      sourceId: resource.sourceId,
      sessionId: data.session_id || resource.sessionId || '',
      title: resource.title,
      filename: resource.filename,
      fileType: resource.type || 'exercise',
      content: data.content || resource.content || ''
    })

    if (!quiz) {
      window.alert('这套题暂时没有拿到完整题目内容，请让后端在资源详情里返回完整 content。')
      return
    }

    router.push(`/question-bank/${quiz.id}`)
  } catch (error) {
    console.error('打开题库资源失败：', error)
    window.alert('题目加载失败，请稍后再试。')
  }
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

const getResourceExcerpt = resource => {
  if (isMindmapResource(resource)) return '点击查看可视化思维导图'
  return getExcerpt(resource?.content)
}

const handleImageError = event => {
  event.target.style.display = 'none'
}

const getWordCount = content => String(content || '').replace(/\s/g, '').length

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
  font-family: inherit;
  cursor: pointer;
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

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
  margin: 0 auto;
  border-radius: 12px;
}

.image-thumb {
  height: 100px;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(237, 249, 252, 0.6);
}

.image-thumb img {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.file-preview-wrap {
  margin-bottom: 16px;
}

.file-placeholder-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 40px 20px;
  color: #5f8fc3;
  text-align: center;
}

.file-placeholder-block p {
  margin: 0;
  font-size: 15px;
  color: #5f8fc3;
}

.file-download-btn {
  min-height: 42px;
  padding: 0 24px;
  border: none;
  border-radius: 18px;
  background: #163f8f;
  color: #ffffff;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.file-download-btn:hover {
  background: #1a4da8;
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
