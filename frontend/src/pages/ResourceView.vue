<template>
  <main class="resource-page">
    <header class="resource-header">
      <div class="header-title-row">
        <router-link to="/resources" class="back-btn" aria-label="返回资源中心">
          <ChevronLeft :size="22" />
        </router-link>
        <div class="title-block">
        <p>My Resources</p>
        <h1>我的学习资源</h1>
        </div>
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
            @click="openResource(resource)"
          >
            <div class="card-top">
              <span class="type-mark">
                <FileImage v-if="resource.type === 'image'" :size="18" />
                <Presentation v-else-if="isPptResource(resource)" :size="18" />
                <GitBranch v-else-if="isMindmapResource(resource)" :size="18" />
                <Video v-else-if="isVideoResource(resource)" :size="18" />
                <FileText v-else :size="18" />
              </span>
              <span class="visibility">{{ resource.categoryLabel || '我的资源' }}</span>
            </div>

            <div class="resource-cover">
              <video
                v-if="resource.coverType === 'video'"
                class="resource-cover__video"
                :src="resource.previewUrl"
                preload="metadata"
                muted
                playsinline
              ></video>
              <img v-else :src="resource.coverUrl" :alt="resource.title" loading="lazy" @error="handleImageError($event)" />
            </div>

            <h2>{{ resource.title || '未命名资源' }}</h2>
            <p>{{ getResourceExcerpt(resource) }}</p>

            <footer>
              <span>{{ formatDate(resource.created_at) }}</span>
              <span v-if="resource.type === 'image'">图片</span>
              <span v-else-if="isVideoResource(resource)">视频</span>
              <span v-else>{{ getWordCount(resource.content) }} 字</span>
            </footer>
            <div class="resource-actions">
              <button
                v-if="canNarrateResource(resource)"
                class="resource-action"
                type="button"
                :disabled="isNarrationLoading(resource)"
                @click.stop="toggleNarration(resource)"
              >
                <PauseCircle v-if="isNarrationPlaying(resource)" :size="15" />
                <Volume2 v-else :size="15" />
                {{ isNarrationLoading(resource) ? '...' : (isNarrationPlaying(resource) ? '停' : '听') }}
              </button>
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
              <button
                v-if="canDeleteResource(resource)"
                class="resource-action danger"
                type="button"
                :disabled="isDeleteLoading(resource)"
                @click.stop="deleteVisibleResource(resource)"
              >
                <Trash2 :size="15" />
                {{ isDeleteLoading(resource) ? '删除中' : '删除' }}
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
            <button type="button" aria-label="关闭预览" @click="closeResourcePreview">&times;</button>
          </header>

          <div class="resource-fullscreen__meta">
            <span>{{ formatDate(selectedResource.created_at, true) }}</span>
            <span>{{ getWordCount(selectedResource.content) }} 字</span>
            <button
              v-if="canNarrateResource(selectedResource)"
              class="listen-inline-btn"
              type="button"
              :disabled="isNarrationLoading(selectedResource)"
              @click="toggleNarration(selectedResource)"
            >
              <PauseCircle v-if="isNarrationPlaying(selectedResource)" :size="15" />
              <Volume2 v-else :size="15" />
              {{ isNarrationLoading(selectedResource) ? '生成音频...' : (isNarrationPlaying(selectedResource) ? '暂停朗读' : '朗读资源') }}
            </button>
          </div>

          <div
            class="resource-fullscreen__content"
            :class="{ 'resource-fullscreen__content--ppt': isPptResource(selectedResource) }"
          >
            <PresentationPreview
              v-if="canUsePresentationPreview(selectedResource)"
              :resource="selectedResource"
              :editable="true"
              :annotatable="true"
              :annotations="selectedResource.annotations || []"
              @download="downloadResource"
              @image-error="handleImageError"
              @create-note="createAnnotation(selectedResource, $event)"
              @update-note="(id, payload) => updateAnnotation(selectedResource, id, payload)"
              @delete-note="deleteAnnotation(selectedResource, $event)"
              @export-pptx="exportResourcePptx(selectedResource, $event)"
            />
            <AnnotatedTextPreview
              v-else
              :content="selectedResource.content || '暂无正文内容'"
              :annotations="selectedResource.annotations || []"
              :annotatable="true"
              @create-note="createAnnotation(selectedResource, $event)"
              @update-note="(id, payload) => updateAnnotation(selectedResource, id, payload)"
              @delete-note="deleteAnnotation(selectedResource, $event)"
            />
          </div>
        </article>
      </section>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertCircle,
  FileImage,
  FileSearch,
  Presentation,
  FileText,
  GitBranch,
  PauseCircle,
  Video,
  Volume2,
  RefreshCw,
  ChevronLeft,
  Trash2
} from 'lucide-vue-next'
import {
  createResourceAnnotation,
  deleteGeneratedImage,
  deleteGeneratedResource,
  deleteResourceAnnotation,
  deleteStudyResource,
  downloadWithToken,
  exportEditedPptx,
  getGeneratedImages,
  getGeneratedResource,
  getGeneratedResources,
  getResourceAnnotations,
  getStudyResources,
  resolveApiUrl,
  updateResourceAnnotation
} from '../api/apis'
import { upsertQuizSet } from '../utils/quizBank'
import AnnotatedTextPreview from '../components/AnnotatedTextPreview.vue'
import PresentationPreview from '../components/ppt_video/PresentationPreview.vue'
import { useResourceNarration } from '../composables/useResourceNarration'
import { getResourceCoverUrl } from '../utils/resourceCover'

const router = useRouter()
const resources = ref([])
const selectedResource = ref(null)
const previewOpen = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const deleteLoading = ref({})
const {
  canNarrateResource,
  toggleNarration,
  isNarrationLoading,
  isNarrationPlaying,
  stopCurrentAudio
} = useResourceNarration()


const categories = ['文档', 'PPT', '图片', '视频', '题库', '思维导图']
const activeCategory = ref(categories[0])

const switchCategory = cat => {
  activeCategory.value = cat
}

const categoryLabelMap = {
  knowledge_point: '知识点讲解',
  exercise: '习题/题库',
  textbook: '教科书章节',
  note: '学习笔记',
  case_study: '实操案例',
  reference: '参考资料',
  video: '视频',
}

const attachResourceCover = (resource, rawItem = {}) => {
  const shouldUseVideoFrame = isVideoResource(resource) && resource.previewUrl
  return {
    ...resource,
    coverUrl: getResourceCoverUrl({ ...resource, ...rawItem }),
    coverType: shouldUseVideoFrame ? 'video' : 'image'
  }
}

const normalizeResources = data => {
  const list = Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : []

  return list.map((item, index) => {
    const isVideo = item.category === 'video' || (item.type || item.file_type || '').includes('video')
    const rawContent = item.preview || item.content || ''
    const videoUrl = isVideo ? resolveApiUrl(rawContent) : ''
    const resource = {
      doc_id: String(item.doc_id || item.id || index),
      source: item.source || 'knowledge',
      sourceId: String(item.resource_id || item.resourceId || item.id || item.doc_id || ''),
      title: item.title || '',
      content: isVideo ? videoUrl : rawContent,
      type: isVideo ? 'video' : (item.type || item.file_type || ''),
      category: item.category || '',
      categoryLabel: categoryLabelMap[item.category] || '',
      visibility: item.visibility || 'private',
      created_at: item.created_at || item.createdAt || '',
      previewUrl: item.previewUrl || item.preview_url || videoUrl || '',
      downloadUrl: item.downloadUrl || item.download_url || videoUrl || ''
    }
    return attachResourceCover(resource, item)
  })
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
    const isVideoType = resourceText.includes('video') || resourceText.includes('mp4') || resourceText.includes('视频')

    const resource = {
      doc_id: `generated-${resourceId}`,
      source: 'generated',
      sourceId: String(resourceId || ''),
      title: item.title || item.topic || fileTitleWithoutExtension(filename),
      filename,
      content: item.content || item.preview || item.preview_content || (isQuiz ? '这是一套生成题目，进入题库后开始练习。' : ''),
      slides: Array.isArray(item.slides) ? item.slides : [],
      narration: item.narration || null,
      type: isMindmap ? 'mindmap' : resourceType,
      category: isQuiz ? 'exercise' : isMindmap ? 'mindmap' : 'reference',
      categoryLabel: isMindmap ? '思维导图' : (isQuiz ? '习题/题库' : 'AI 生成'),
      visibility: item.visibility || 'private',
      quizId: item.quiz_id || item.quizId || '',
      sessionId: item.session_id || item.sessionId || '',
      created_at: item.created_at || item.createdAt || '',
      previewUrl: resolveApiUrl(item.preview_url || item.previewUrl || (isVideoType ? (item.content || item.preview || '') : '')),
      downloadUrl: resolveApiUrl(item.download_url || item.downloadUrl || (resourceId ? `/resource/${resourceId}/download` : ''))
    }
    return attachResourceCover(resource, item)
  })
}

const normalizeGeneratedImages = data => {
  const list = Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : data?.images || data?.image_list || []
  return (Array.isArray(list) ? list : []).map(item => {
    const imageId = String(item.image_id || item.imageId || item.id || '')
    const url = item.url || item.image_url || item.imageUrl || item.preview_url || item.previewUrl || ''
    const resource = {
      doc_id: `image-${imageId}`,
      source: 'generated',
      sourceId: imageId,
      title: item.title || item.prompt || fileTitleWithoutExtension(item.filename || item.file_name || item.name || ''),
      filename: item.filename || item.file_name || item.name || `image-${imageId || Date.now()}.jpg`,
      content: item.prompt || item.content || item.preview || '',
      type: 'image',
      category: 'reference',
      categoryLabel: 'AI 生成图片',
      visibility: item.visibility || 'private',
      quizId: '',
      sessionId: '',
      created_at: item.created_at || item.createdAt || '',
      previewUrl: resolveApiUrl(url),
      downloadUrl: resolveApiUrl(item.download_url || item.downloadUrl || url || (imageId ? `/image/${imageId}/download` : ''))
    }
    return attachResourceCover(resource, item)
  })
}

const mergeImageDuplicates = list => {
  const seen = new Set()
  return list.filter(item => {
    if (item.type !== 'image') return true
    const key = item.previewUrl || item.downloadUrl || item.sourceId || item.doc_id
    if (!key) return true
    if (seen.has(key)) return false
    seen.add(key)
    return true
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
    const result = await getStudyResources({ mine: true })
    const backendResources = normalizeResources(result)
    const generatedResult = await getGeneratedResources()
    const generatedBackendResources = normalizeGeneratedResources(generatedResult)
    const imageResult = await getGeneratedImages()
    const imageResources = normalizeGeneratedImages(imageResult)
    resources.value = mergeImageDuplicates([...imageResources, ...generatedBackendResources, ...backendResources])
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
      const isVideo = (data.resource_type || data.file_type || resource.type || '').toLowerCase().includes('video')
      const looksLikeUrl = /^(https?:\/\/|\/static\/|\/resource\/)/.test(String(fullContent).trim())
      selectedResource.value = {
        ...resource,
        content: fullContent,
        fullContent,
        slides: Array.isArray(data.slides) ? data.slides : resource.slides || [],
        narration: data.narration || resource.narration || null,
        filename: data.filename || resource.filename,
        type: isMindmapResource(resource) ? 'mindmap' : (data.resource_type || data.file_type || resource.type),
        sessionId: data.session_id || resource.sessionId || '',
        previewUrl: (isVideo && looksLikeUrl) ? resolveApiUrl(String(fullContent).trim()) : resource.previewUrl,
        downloadUrl: resolveApiUrl(data.download_url || data.downloadUrl || resource.downloadUrl)
      }
    } catch (error) {
      console.error('加载资源详情失败：', error)
    }
  }

  loadAnnotationsForResource(selectedResource.value)
}

const openResource = resource => {
  if (isQuizResource(resource)) {
    startResourceQuiz(resource)
    return
  }
  openResourcePreview(resource)
}

const closeResourcePreview = () => {
  previewOpen.value = false
}

const fileTitleWithoutExtension = filename => String(filename || '生成资源').replace(/\.[^.\\/]+$/, '')

const getAnnotationTarget = resource => {
  const id = resource?.sourceId || resource?.resourceId || resource?.resource_id || resource?.id || resource?.doc_id || ''
  const sourceId = String(id || '').replace(/^(generated|image)-/, '')
  const sourceType = resource?.source === 'generated' ? 'generated' : 'knowledge'
  return { sourceType, sourceId }
}

const normalizeAnnotations = result => {
  const data = result?.data?.data || result?.data || result || []
  const list = Array.isArray(data) ? data : data.records || data.list || data.annotations || []
  return (Array.isArray(list) ? list : []).map(item => ({
    ...item,
    id: item.id || item.annotation_id || item.annotationId,
    selected_text: item.selected_text || item.selectedText || '',
    note: item.note || item.note_text || item.noteText || '',
    note_text: item.note_text || item.note || item.noteText || '',
    position: typeof item.position === 'string'
      ? (() => {
          try {
            return JSON.parse(item.position)
          } catch {
            return {}
          }
        })()
      : item.position || {}
  }))
}

const patchSelectedResource = patch => {
  if (!selectedResource.value) return
  selectedResource.value = { ...selectedResource.value, ...patch }
  resources.value = resources.value.map(item => item.doc_id === selectedResource.value.doc_id ? selectedResource.value : item)
}

const loadAnnotationsForResource = async resource => {
  const target = getAnnotationTarget(resource)
  if (!target.sourceId) {
    patchSelectedResource({ annotations: [] })
    return
  }

  try {
    const result = await getResourceAnnotations(target.sourceId, target.sourceType)
    patchSelectedResource({ annotations: normalizeAnnotations(result) })
  } catch (error) {
    console.warn('加载资源笔记失败：', error)
    patchSelectedResource({ annotations: [] })
  }
}

const createAnnotation = async (resource, payload) => {
  const target = getAnnotationTarget(resource)
  if (!target.sourceId) return

  try {
    await createResourceAnnotation(target.sourceId, {
      ...payload,
      source_type: target.sourceType,
      source_id: target.sourceId
    })
    await loadAnnotationsForResource(resource)
  } catch (error) {
    console.error('保存标注失败：', error)
    const detail = error?.response?.data?.detail || error?.response?.data?.msg || error?.message || ''
    window.alert(`保存标注失败${detail ? `：${detail}` : '，请稍后再试。'}`)
  }
}

const updateAnnotation = async (resource, annotationId, payload) => {
  const target = getAnnotationTarget(resource)
  if (!target.sourceId || !annotationId) return

  try {
    await updateResourceAnnotation(target.sourceId, annotationId, payload)
    await loadAnnotationsForResource(resource)
  } catch (error) {
    console.error('更新笔记失败：', error)
    window.alert('更新笔记失败，请稍后再试。')
  }
}

const deleteAnnotation = async (resource, annotationId) => {
  const target = getAnnotationTarget(resource)
  if (!target.sourceId || !annotationId) return

  try {
    await deleteResourceAnnotation(target.sourceId, annotationId)
    await loadAnnotationsForResource(resource)
  } catch (error) {
    console.error('删除笔记失败：', error)
    window.alert('删除笔记失败，请稍后再试。')
  }
}

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
  return text.includes('mindmap') || text.includes('mind_map') || text.includes('mind-map') || text.includes('xmind') || text.includes('脑图') || text.includes('思维导图')
}

const isVideoResource = resource => {
  const typeCat = String(`${resource?.type || ''} ${resource?.category || ''}`).toLowerCase()
  const filename = String(resource?.filename || '').toLowerCase()
  return resource?.category === 'video' ||
    typeCat.includes('video') ||
    /\.(mp4|webm|ogg|mov|avi|mkv|flv|wmv)($|\s|\?)/i.test(filename)
}

const canUsePresentationPreview = resource => {
  return resource?.type === 'image' ||
    isVideoResource(resource) ||
    isMindmapResource(resource) ||
    isPptResource(resource)
}

const getResourceKind = resource => {
  const text = String(`${resource?.type || ''} ${resource?.category || ''} ${resource?.filename || ''} ${resource?.title || ''}`).toLowerCase()
  if (text.includes('image') || /\.(jpg|jpeg|png|webp|gif|bmp|svg)$/i.test(text)) return '图片'
  if (isPptResource(resource)) return 'PPT'
  if (isVideoResource(resource)) return '视频'
  if (isQuizResource(resource)) return '题库'
  if (isMindmapResource(resource)) return '思维导图'
  return '文档'
}

const matchesCategory = resource => {
  return getResourceKind(resource) === activeCategory.value
}

const downloadResource = async resource => {
  try {
    await downloadWithToken(resource.downloadUrl, resource.filename || `${resource.title || 'resource'}.md`)
  } catch (error) {
    console.error('下载资源失败：', error)
    window.alert(error?.message || '下载失败，请确认登录状态和后端服务是否正常。')
  }
}

const getDeleteId = resource => String(resource?.sourceId || resource?.resourceId || resource?.resource_id || resource?.id || resource?.doc_id || '').replace(/^(generated|image)-/, '')

const deleteKey = resource => `${resource?.type || resource?.source || 'resource'}-${getDeleteId(resource) || resource?.doc_id || ''}`

const isDeleteLoading = resource => Boolean(deleteLoading.value[deleteKey(resource)])

const setDeleteLoading = (resource, value) => {
  deleteLoading.value = {
    ...deleteLoading.value,
    [deleteKey(resource)]: value
  }
}

const canDeleteResource = resource => Boolean(resource && getDeleteId(resource))

const removeResourceFromList = resource => {
  resources.value = resources.value.filter(item => item.doc_id !== resource.doc_id)
  if (selectedResource.value?.doc_id === resource.doc_id) {
    selectedResource.value = resources.value[0] || null
    previewOpen.value = false
  }
}

const deleteVisibleResource = async resource => {
  if (!resource || isDeleteLoading(resource)) return
  const resourceId = getDeleteId(resource)
  if (!resourceId) {
    window.alert('当前资源缺少删除 ID，暂时无法删除。')
    return
  }
  const confirmed = window.confirm(`确定删除「${resource.title || '这个资源'}」吗？删除后不可恢复。`)
  if (!confirmed) return

  setDeleteLoading(resource, true)
  try {
    if (resource.type === 'image') {
      await deleteGeneratedImage(resourceId)
    } else if (resource.source === 'generated') {
      await deleteGeneratedResource(resourceId)
    } else {
      await deleteStudyResource(resourceId)
    }
    removeResourceFromList(resource)
  } catch (error) {
    console.error('删除资源失败：', error)
    window.alert(error?.response?.data?.detail || error?.response?.data?.msg || error?.message || '删除失败，请稍后再试。')
  } finally {
    setDeleteLoading(resource, false)
  }
}

const escapeHtml = value => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const splitSlideLines = value => String(value || '')
  .split(/\r?\n|[;；]/)
  .map(line => line.replace(/^[-*•\s]+/, '').trim())
  .filter(Boolean)

const pptDownloadName = resource => {
  const raw = String(resource?.filename || resource?.title || 'edited-presentation')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\.[^.]+$/, '')
  return `${raw || 'edited-presentation'}.ppt`
}

const buildEditedPptHtml = resource => {
  const slides = Array.isArray(resource?.slides) ? resource.slides : []
  const title = escapeHtml(resource?.title || 'Edited Presentation')
  const slideHtml = slides.map((slide, index) => {
    const slideTitle = escapeHtml(slide.title || `${resource?.title || 'Slide'} ${index + 1}`)
    const text = slide.text || slide.content || ''
    const notes = slide.notes || slide.speaker_notes || ''
    const lines = splitSlideLines(text)
      .map(line => `<li>${escapeHtml(line)}</li>`)
      .join('')

    return `
      <section class="slide">
        <div class="meta">${index + 1} / ${slides.length}</div>
        <h1>${slideTitle}</h1>
        <ul>${lines}</ul>
        ${notes ? `<aside>${escapeHtml(notes).replace(/\n/g, '<br>')}</aside>` : ''}
      </section>
    `
  }).join('')

  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>${title}</title>
  <style>
    @page { size: 13.333in 7.5in; margin: 0; }
    body { margin: 0; font-family: "Open Sans", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif; color: #163f8f; background: #f4fbfd; }
    .slide { box-sizing: border-box; width: 13.333in; height: 7.5in; padding: .55in .72in; page-break-after: always; background: linear-gradient(135deg, #fff 0%, #edf9fc 100%); display: flex; flex-direction: column; justify-content: center; position: relative; }
    .meta { position: absolute; top: .32in; right: .5in; color: #5f8fc3; font-size: 12pt; font-weight: 700; }
    h1 { margin: 0 0 .38in; text-align: center; font-size: 38pt; line-height: 1.15; }
    ul { width: 78%; margin: 0 auto; padding-left: .35in; font-size: 20pt; line-height: 1.55; }
    li { margin: 0 0 .12in; }
    aside { margin-top: auto; padding: .14in .18in; border-radius: .08in; background: rgba(201, 220, 233, .42); color: rgba(22, 63, 143, .74); font-size: 12pt; line-height: 1.5; }
  </style>
</head>
<body>${slideHtml}</body>
</html>`
}

const downloadEditedPpt = resource => {
  const blob = new Blob([buildEditedPptHtml(resource)], { type: 'application/vnd.ms-powerpoint;charset=utf-8' })
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = pptDownloadName(resource)
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

const pptxExportName = resource => {
  const raw = String(resource?.filename || resource?.title || 'edited-presentation')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\.[^.]+$/, '')
  return `${raw || 'edited-presentation'}.pptx`
}

const getResourceIdFromUrl = url => {
  const match = String(url || '').match(/\/resource\/([^/?#]+)(?:\/download)?/i)
  return match?.[1] || ''
}

const exportResourcePptx = async (resource, slides) => {
  const resourceId = resource?.sourceId || resource?.resourceId || resource?.resource_id || resource?.id || getResourceIdFromUrl(resource?.downloadUrl) || ''
  if (!resourceId) {
    window.alert('当前 PPT 没有资源 ID，暂时无法导出 PPTX。')
    return
  }

  try {
    await exportEditedPptx(resourceId, {
      title: resource?.title || '',
      filename: pptxExportName(resource),
      slides
    })
  } catch (error) {
    console.error('导出 PPTX 失败', error)
    window.alert(error?.message || '导出 PPTX 失败，请稍后再试。')
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
      questions: data.questions || data.items || (Array.isArray(data.data) ? data.data : null),
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
  if (isVideoResource(resource)) return '点击预览视频内容'
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

.header-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(20, 55, 97, 0.15);
  background: rgba(255, 255, 255, 0.62);
  color: #143761;
  text-decoration: none;
  flex-shrink: 0;
  transition: background 0.2s ease, transform 0.2s ease;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.86);
  transform: translateX(-2px);
}

.home-pill {
  min-height: 40px;
  padding: 0 18px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: #163f8f;
  text-decoration: none;
  font-size: 14px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  box-shadow: 0 12px 28px rgba(22, 63, 143, 0.08);
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
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 28px;
  overflow: hidden;
}

.category-panel {
  min-height: 0;
  border-radius: 28px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(22, 63, 143, 0.16);
  background: rgba(250, 250, 250, 0.78);
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
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
  font-size: 18px;
}

.category-panel button {
  position: relative;
  width: calc(100% - 28px);
  height: 36px;
  margin: 6px 14px 0;
  border: 0;
  border-radius: 999px;
  background: rgba(250, 250, 250, 0.48);
  color: #163f8f;
  font-size: 14px;
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
  padding: 8px 4px 10px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  align-content: start;
  gap: 22px;
}

.resource-card {
  height: 276px;
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

.resource-cover {
  height: 96px;
  border-radius: 16px;
  overflow: hidden;
  background: rgba(237, 249, 252, 0.76);
  box-shadow: inset 0 0 0 1px rgba(22, 63, 143, 0.08);
  flex-shrink: 0;
}

.resource-cover img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.resource-cover__video {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  pointer-events: none;
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
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
}

.resource-action {
  min-height: 28px;
  padding: 0 8px;
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
  gap: 5px;
}

.resource-action:disabled {
  opacity: 0.62;
  cursor: wait;
}

.resource-action.danger {
  border-color: rgba(220, 63, 48, 0.28);
  background: rgba(220, 63, 48, 0.12);
  color: #c7352d;
}

.resource-action.danger:hover:not(:disabled) {
  background: #c7352d;
  color: #ffffff;
}

.listen-inline-btn {
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(22, 63, 143, 0.18);
  border-radius: 999px;
  background: #163f8f;
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: inherit;
  font-size: 11px;
  font-weight: 900;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}

.listen-inline-btn:disabled {
  opacity: 0.62;
  cursor: wait;
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
  padding: clamp(12px, 2.5vw, 32px);
  background: rgba(12, 28, 58, 0.34);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(16px) saturate(135%);
  -webkit-backdrop-filter: blur(16px) saturate(135%);
}

.resource-fullscreen__panel {
  width: min(1380px, 100%);
  height: min(940px, 96vh);
  min-height: 0;
  padding: clamp(16px, 2vw, 28px);
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
  padding: clamp(14px, 1.7vw, 22px);
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 24px;
  background: rgba(237, 249, 252, 0.48);
  overflow: auto;
}

.resource-fullscreen__content--ppt {
  overflow: hidden;
  padding: 10px;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
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

.video-thumb {
  height: 100px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(22, 63, 143, 0.08), rgba(22, 63, 143, 0.16));
  color: #163f8f;
}

.preview-video {
  width: 100%;
  max-height: 100%;
  border-radius: 12px;
  display: block;
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
  .resource-header {
    grid-template-columns: 1fr;
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
    min-width: 80px;
    border-bottom: 0;
    border-right: 1px solid rgba(201, 220, 233, 0.44);
  }

  .category-panel button {
    width: auto;
    margin: 6px 8px;
    padding: 0 16px;
  }

  .resource-page,
  .resource-list {
    overflow: visible;
  }

  .resource-page {
    height: auto;
  }
}
</style>

