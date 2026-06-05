<template>
  <main class="resource-center-page">
    <div class="page-bg-deco" aria-hidden="true">
      <span class="sweep sweep-one"></span>
      <span class="sweep sweep-two"></span>
    </div>
    <header class="center-header">
      <div class="title-block">
        <h1>资源中心</h1>
      </div>

      <label class="search-field">
        <Search :size="18" />
        <input v-model.trim="keyword" type="search" placeholder="搜索资源..." />
      </label>

      <button class="send-search" type="button">搜索</button>

      <div class="header-actions">
        <button class="icon-btn refresh-btn" type="button" :disabled="loading" title="刷新资源" @click="loadResources">
          <RefreshCw :size="24" :class="{ spinning: loading }" />
        </button>
        <router-link class="import-link" to="/study-import">
          资料导入
        </router-link>
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

      <section class="resource-list" aria-label="资源列表区域">
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
              <span class="visibility">{{ resource.categoryLabel || '公开资源' }}</span>
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
            <div class="resource-card-actions" @click.stop>
              <button
                class="reaction-btn"
                :class="{ active: resource.isLiked }"
                type="button"
                title="点赞"
                :disabled="isReactionLoading(resource, 'like') || !canReactResource(resource)"
                @click="toggleResourceLike(resource)"
              >
                <ThumbsUp :size="14" />
                <span>{{ formatCount(resource.likeCount) }}</span>
              </button>
              <button
                class="reaction-btn"
                :class="{ active: resource.isFavorited }"
                type="button"
                title="收藏"
                :disabled="isReactionLoading(resource, 'favorite') || !canReactResource(resource)"
                @click="toggleResourceFavorite(resource)"
              >
                <Bookmark :size="14" />
                <span>{{ formatCount(resource.favoriteCount) }}</span>
              </button>
              <button
                v-if="canNarrateResource(resource)"
                class="resource-action"
                type="button"
                :title="isNarrationPlaying(resource) ? '暂停朗读' : '朗读'"
                :disabled="isNarrationLoading(resource)"
                @click.stop="toggleNarration(resource)"
              >
                <PauseCircle v-if="isNarrationPlaying(resource)" :size="15" />
                <Volume2 v-else :size="15" />
              </button>
              <button
                v-if="isQuizResource(resource)"
                class="resource-action"
                type="button"
                title="开始练习"
                @click.stop="startResourceQuiz(resource)"
              >
                <FileQuestion :size="15" />
              </button>
              <button
                v-if="resource.downloadUrl"
                class="resource-action"
                type="button"
                title="下载文件"
                @click.stop="downloadResource(resource)"
              >
                <Download :size="15" />
              </button>
            </div>
          </article>
        </template>

        <template v-else>
          <article class="empty-state">
            <div class="card-top">
              <span class="type-mark soft">
                <FileText :size="18" />
              </span>
              <span class="visibility">暂无资源</span>
            </div>
            <h2>资源为空</h2>
            <p>上传学习资料或使用 AI 生成资源后，你的资料会出现在这里。</p>
          </article>
        </template>
      </section>

      <aside class="hot-panel">
        <h2>热门资源</h2>
        <div class="hot-list">
          <button
            v-for="resource in hotResources"
            :key="resource.doc_id"
            class="hot-resource-card"
            type="button"
            @click="openResource(resource)"
          >
            <span class="hot-resource-card__rank">{{ resource.hotRank }}</span>
            <span class="hot-resource-card__body">
              <strong>{{ resource.title || '未命名资源' }}</strong>
              <small>{{ getResourceKind(resource) }} · {{ getHotScore(resource) }} 热度</small>
            </span>
            <span class="hot-resource-card__stats">
              <span><ThumbsUp :size="12" />{{ formatCount(resource.likeCount) }}</span>
              <span><Bookmark :size="12" />{{ formatCount(resource.favoriteCount) }}</span>
            </span>
          </button>
          <p v-if="!hotResources.length" class="hot-empty">暂无热门资源</p>
        </div>

        <button class="share-btn" type="button">分享资源</button>
      </aside>
    </section>

    <Teleport to="body">
      <section v-if="previewOpen && selectedResource" class="resource-fullscreen" @click.self="closeResourcePreview">
        <article class="resource-fullscreen__panel">
          <header class="resource-fullscreen__header">
            <div>
              <span>{{ selectedResource.categoryLabel || '我的资源' }}</span>
              <h2>{{ selectedResource.title || '未命名资源' }}</h2>
            </div>
            <button type="button" aria-label="关闭预览" @click="closeResourcePreview">&#x2715;</button>
          </header>

          <div class="resource-fullscreen__meta">
            <span>{{ formatDate(selectedResource.created_at, true) }}</span>
            <span>{{ getWordCount(selectedResource.content) }} 字</span>
            <button
              class="reaction-btn reaction-btn--meta"
              :class="{ active: selectedResource.isLiked }"
              type="button"
              :disabled="isReactionLoading(selectedResource, 'like') || !canReactResource(selectedResource)"
              @click="toggleResourceLike(selectedResource)"
            >
              <ThumbsUp :size="14" />
              <span>{{ formatCount(selectedResource.likeCount) }}</span>
            </button>
            <button
              class="reaction-btn reaction-btn--meta"
              :class="{ active: selectedResource.isFavorited }"
              type="button"
              :disabled="isReactionLoading(selectedResource, 'favorite') || !canReactResource(selectedResource)"
              @click="toggleResourceFavorite(selectedResource)"
            >
              <Bookmark :size="14" />
              <span>{{ formatCount(selectedResource.favoriteCount) }}</span>
            </button>
          </div>

          <div v-if="canNarrateResource(selectedResource)" class="resource-fullscreen__audio">
            <button
              class="listen-inline-btn"
              type="button"
              :disabled="isNarrationLoading(selectedResource)"
              @click="toggleNarration(selectedResource)"
            >
              <PauseCircle v-if="isNarrationPlaying(selectedResource)" :size="15" />
              <Volume2 v-else :size="15" />
              {{ isNarrationLoading(selectedResource) ? '加载音频...' : (isNarrationPlaying(selectedResource) ? '暂停播放' : '播放资源') }}
            </button>
          </div>

          <div
            class="resource-fullscreen__content"
            :class="{ 'resource-fullscreen__content--media': isPresentationResource(selectedResource) || isVideoResource(selectedResource) }"
          >
            <template v-if="selectedResource.type === 'image' && selectedResource.previewUrl">
              <img
                class="preview-image"
                :src="selectedResource.previewUrl"
                :alt="selectedResource.title"
                @error="handleImageError"
              />
            </template>
            <template v-else-if="isPresentationResource(selectedResource)">
              <iframe
                v-if="selectedResource.previewUrl"
                class="preview-iframe"
                :src="selectedResource.previewUrl"
                frameborder="0"
                allowfullscreen
              ></iframe>
              <p v-else>课件加载中，请稍后...</p>
            </template>
            <template v-else-if="isVideoResource(selectedResource)">
              <video
                v-if="selectedResource.previewUrl"
                class="preview-video"
                :src="selectedResource.previewUrl"
                controls
                autoplay
                playsinline
              >
                您的浏览器不支持视频播放
              </video>
              <p v-else>{{ selectedResource.content || '暂无视频内容' }}</p>
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
                  下载思维导图文件
                </button>
              </div>
            </template>
            <template v-else-if="isPptResource(selectedResource)">
              <PptPreview
                v-if="selectedResource.slides?.length"
                v-model:slides="selectedResource.slides"
                :title="selectedResource.title"
                @export-pptx="exportResourcePptx(selectedResource, $event)"
              />
              <div v-else-if="selectedResource.previewUrl" class="file-preview-wrap">
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
            <p v-else>{{ selectedResource.content || '暂无内容可展示' }}</p>
          </div>
        </article>
      </section>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlertCircle,
  Bookmark,
  Download,
  FileImage,
  FileQuestion,
  Presentation,
  FileText,
  GitBranch,
  PauseCircle,
  RefreshCw,
  Search,
  ThumbsUp,
  Video,
  Volume2
} from 'lucide-vue-next'
import {
  downloadWithToken,
  exportEditedPptx,
  favoriteResource,
  getGeneratedImages,
  getGeneratedResource,
  getGeneratedResources,
  getPresentations,
  getStudyResources,
  likeResource,
  resolveApiUrl,
  unfavoriteResource,
  unlikeResource
} from '../api/apis'
import { upsertQuizSet } from '../utils/quizBank'

import MindmapPreview from '../components/MindmapPreview.vue'
import PptPreview from '../components/PptPreview.vue'
import { useResourceNarration } from '../composables/useResourceNarration'
import { getExplicitResourceCoverUrl, getResourceCoverUrl } from '../utils/resourceCover'

const route = useRoute()
const router = useRouter()
const resources = ref([])
const selectedResource = ref(null)
const previewOpen = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const reactionLoading = ref({})
const {
  canNarrateResource,
  toggleNarration,
  isNarrationLoading,
  isNarrationPlaying,
  stopCurrentAudio
} = useResourceNarration()
const keyword = ref('')
const categories = ['文档', 'PPT', '图片', '视频', '题库', '思维导图']
const activeCategory = ref(categories[0])
const pendingNotificationOpen = ref('')


// 鏄犲皠 KB_CATEGORIES 鐨勫€?

const categoryLabelMap = {
  knowledge_point: '知识点讲解',
  exercise: '习题/题库',
  textbook: '教材教辅',
  note: '学习笔记',
  case_study: '案例分析',
  reference: '参考资料',
  video: '视频',
}

const pickNumber = (...values) => {
  for (const value of values) {
    const number = Number(value)
    if (Number.isFinite(number)) return number
  }
  return 0
}

const pickBoolean = (...values) => {
  for (const value of values) {
    if (typeof value === 'boolean') return value
    if (value === 1 || value === '1' || value === 'true') return true
    if (value === 0 || value === '0' || value === 'false') return false
  }
  return false
}

const normalizeReactionFields = item => ({
  likeCount: pickNumber(item.like_count, item.likeCount, item.likes_count, item.likes, item.praise_count, item.upvote_count),
  favoriteCount: pickNumber(item.favorite_count, item.favoriteCount, item.collect_count, item.collectCount, item.collection_count, item.collections_count, item.favorites),
  isLiked: pickBoolean(item.is_liked, item.isLiked, item.liked, item.has_liked),
  isFavorited: pickBoolean(item.is_favorited, item.isFavorited, item.favorited, item.collected, item.is_collected, item.has_favorited)
})

const attachResourceCover = (resource, rawItem = {}) => {
  const explicitCover = getExplicitResourceCoverUrl({ ...resource, ...rawItem })
  const shouldUseVideoFrame = !explicitCover && isVideoResource(resource) && resource.previewUrl
  return {
    ...resource,
    coverUrl: explicitCover || getResourceCoverUrl({ ...resource, ...rawItem }),
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
      downloadUrl: item.downloadUrl || item.download_url || videoUrl || '',
      ...normalizeReactionFields(item)
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

    const resource = {
      doc_id: `generated-${resourceId}`,
      source: 'generated',
      sourceId: String(resourceId || ''),
      title: item.title || item.topic || fileTitleWithoutExtension(filename),
      filename,
      slides: Array.isArray(item.slides) ? item.slides : [],
      narration: item.narration || null,
      content: item.content || item.preview || item.preview_content || (isQuiz ? '包含选择题、填空题等多种题型的练习资源' : ''),
      type: isMindmap ? 'mindmap' : resourceType,
      category: isQuiz ? 'exercise' : isMindmap ? 'mindmap' : 'reference',
      categoryLabel: isMindmap ? '思维导图' : (isQuiz ? '练习题库' : 'AI 生成'),
      visibility: item.visibility || 'private',
      quizId: item.quiz_id || item.quizId || '',
      sessionId: item.session_id || item.sessionId || '',
      created_at: item.created_at || item.createdAt || '',
      previewUrl: resolveApiUrl(item.preview_url || item.previewUrl || (isVideoResource({ type: resourceType, filename, title: item.title || item.topic }) ? (item.content || item.preview || '') : '')),
      downloadUrl: resolveApiUrl(item.download_url || item.downloadUrl || (resourceId ? `/resource/${resourceId}/download` : (isVideoResource({ type: resourceType, filename, title: item.title || item.topic }) ? (item.content || item.preview || '') : ''))),
      ...normalizeReactionFields(item)
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
      visibility: 'private',
      quizId: '',
      sessionId: '',
      created_at: item.created_at || item.createdAt || '',
      previewUrl: resolveApiUrl(url),
      downloadUrl: resolveApiUrl(item.download_url || item.downloadUrl || url || (imageId ? `/image/${imageId}/download` : '')),
      ...normalizeReactionFields(item)
    }
    return attachResourceCover(resource, item)
  })
}

const normalizePresentations = data => {
  const list = Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : []
  return list.map(item => {
    const resource = {
      doc_id: `presentation-${item.id}`,
      source: 'presentation',
      sourceId: String(item.id || ''),
      title: item.topic || '动态课件',
      filename: `${item.topic || '动态课件'}.html`,
      content: item.file_url || '',
      type: 'presentation',
      category: 'presentation',
      categoryLabel: 'AI 课件',
      visibility: 'private',
      created_at: item.created_at || '',
      previewUrl: resolveApiUrl(item.file_url || ''),
      downloadUrl: resolveApiUrl(item.file_url || ''),
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

  try {
    const [publicResult, myResult, presentationResult] = await Promise.all([
      getStudyResources({ visibility: 'public' }),
      getStudyResources({ mine: true }),
      getPresentations()
    ])
    const publicResources = normalizeResources(publicResult).filter(item => item.visibility === 'public')
    const myResources = normalizeResources(myResult)
    const generatedResult = await getGeneratedResources()
    const generatedBackendResources = normalizeGeneratedResources(generatedResult)
    const imageResult = await getGeneratedImages()
    const imageResources = normalizeGeneratedImages(imageResult)
    const presentationResources = normalizePresentations(presentationResult)
    resources.value = mergeImageDuplicates([...presentationResources, ...imageResources, ...generatedBackendResources, ...myResources, ...publicResources])
    selectedResource.value = resources.value[0] || null
    openNotificationTargetResource()
  } catch (error) {
    if (error?.response?.status === 401) {
      errorMessage.value = '请先登录后再查看资源列表'
    } else {
      errorMessage.value =
        error?.response?.data?.detail ||
        error?.response?.data?.msg ||
        error?.message ||
        '资源中心加载失败，请稍后重试'
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
  return resources.value
    .slice()
    .sort((a, b) => {
      const scoreDiff = getHotScore(b) - getHotScore(a)
      if (scoreDiff !== 0) return scoreDiff
      return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
    })
    .slice(0, 5)
    .map((resource, index) => ({ ...resource, hotRank: index + 1 }))
})

const openResourcePreview = async resource => {
  selectedResource.value = resource
  previewOpen.value = true

  // 诊断日志：显示当前资源的视频相关字段
  console.log('[ResourceCenter] 打开资源预览:', {
    title: resource.title,
    source: resource.source,
    type: resource.type,
    category: resource.category,
    previewUrl: resource.previewUrl,
    content: String(resource.content || '').slice(0, 100),
    sourceId: resource.sourceId,
    downloadUrl: resource.downloadUrl
  })

  if (resource?.source === 'generated' && resource?.sourceId && !resource?.fullContent) {
    try {
      const detail = await getGeneratedResource(resource.sourceId)
      const data = detail?.data || detail || {}
      const fullContent = data.content || data.preview || resource.content || ''
      const isVideo = isVideoResource({ type: data.resource_type || data.file_type || resource.type, category: data.category || resource.category, filename: data.filename || resource.filename })
      const looksLikeUrl = /^(https?:\/\/|\/static\/|\/resource\/)/.test(String(fullContent).trim())
      console.log('[ResourceCenter] 获取详情后:', { isVideo, looksLikeUrl, fullContent: String(fullContent).slice(0, 100), dataKeys: Object.keys(data) })
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
        downloadUrl: resolveApiUrl(data.download_url || data.downloadUrl || resource.downloadUrl),
        ...normalizeReactionFields({ ...resource, ...data })
      }
      updateResourceState(selectedResource.value)
    } catch (error) {
      console.error('加载资源详情失败', error)
    }
  }
}

const findResourceByNotificationTarget = target => {
  const normalizedTarget = String(target || '').trim()
  if (!normalizedTarget) return null
  if (normalizedTarget === 'latest') {
    return resources.value.find(item => item.source === 'generated') || resources.value[0] || null
  }

  return resources.value.find(item => {
    const ids = [
      item.sourceId,
      item.resourceId,
      item.resource_id,
      item.id,
      item.doc_id
    ].map(value => String(value || ''))
    return ids.includes(normalizedTarget) ||
      ids.includes(`generated-${normalizedTarget}`) ||
      ids.includes(`image-${normalizedTarget}`)
  }) || null
}

const openNotificationTargetResource = () => {
  if (loading.value || !resources.value.length) return
  const target = String(route.query.resource_id || route.query.resourceId || route.query.id || route.query.open || '').trim()
  if (!target || pendingNotificationOpen.value === target) return

  const resource = findResourceByNotificationTarget(target)
  if (!resource) return

  pendingNotificationOpen.value = target
  if (isQuizResource(resource)) {
    startResourceQuiz(resource)
    return
  }
  openResourcePreview(resource)
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
  return text.includes('mindmap') || text.includes('mind_map') || text.includes('mind-map') || text.includes('思维') || text.includes('思维导图')
}

const isVideoResource = resource => {
  // 按 type / category / filename 后缀判定，不拿 title 匹配
  const typeCat = String(`${resource?.type || ''} ${resource?.category || ''}`).toLowerCase()
  const filename = String(resource?.filename || '').toLowerCase()
  return resource?.category === 'video' ||
    resource?.type === 'presentation' ||
    typeCat.includes('video') ||
    /\.(mp4|webm|ogg|mov|avi|mkv|flv|wmv)($|\s|\?)/i.test(filename)
}

const isPresentationResource = resource => resource?.type === 'presentation' || resource?.category === 'presentation'

const getResourceKind = resource => {
  const text = String(`${resource?.type || ''} ${resource?.category || ''} ${resource?.filename || ''} ${resource?.title || ''}`).toLowerCase()
  if (text.includes('image') || /\.(jpg|jpeg|png|webp|gif|bmp|svg)$/i.test(text)) return '图片'
  if (isPptResource(resource)) return 'PPT'
  if (isVideoResource(resource)) return '视频'
  if (isQuizResource(resource)) return '题库'
  if (isMindmapResource(resource)) return '思维导图'
  return '文档'
}

const downloadResource = async resource => {
  try {
    await downloadWithToken(resource.downloadUrl, resource.filename || `${resource.title || 'resource'}.md`)
  } catch (error) {
    console.error('下载资源失败', error)
    window.alert('下载失败，请检查网络连接或稍后重试')
  }
}

const pptxExportName = resource => {
  const raw = String(resource?.filename || resource?.title || 'edited-presentation')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\.[^.]+$/, '')
  return `${raw || 'edited-presentation'}.pptx`
}

const exportResourcePptx = async (resource, slides) => {
  const resourceId = resource?.sourceId || resource?.resourceId || resource?.resource_id || resource?.id || ''
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
    window.alert('导出 PPTX 失败，请确认后端已接入 /resource/{id}/export-pptx 接口。')
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
      window.alert('无法找到有效的练习数据，请确认资源中包含题目内容')
      return
    }

    router.push(`/question-bank/${quiz.id}`)
  } catch (error) {
    console.error('开始练习资源加载失败', error)
    window.alert('题目数据加载失败，请稍后重试')
  }
}

const matchesCategory = resource => {
  return getResourceKind(resource) === activeCategory.value
}

const getReactionId = resource => {
  const id = resource?.sourceId || resource?.resourceId || resource?.resource_id || ''
  return id && !String(id).startsWith('image-') ? id : ''
}

const canReactResource = resource => Boolean(getReactionId(resource))

const reactionKey = (resource, type) => `${type}-${getReactionId(resource) || resource?.doc_id || ''}`

const isReactionLoading = (resource, type) => Boolean(reactionLoading.value[reactionKey(resource, type)])

const setReactionLoading = (resource, type, value) => {
  reactionLoading.value = {
    ...reactionLoading.value,
    [reactionKey(resource, type)]: value
  }
}

const updateResourceState = patch => {
  if (!patch?.doc_id) return
  resources.value = resources.value.map(item => item.doc_id === patch.doc_id ? { ...item, ...patch } : item)
  if (selectedResource.value?.doc_id === patch.doc_id) {
    selectedResource.value = { ...selectedResource.value, ...patch }
  }
}

const getHotScore = resource => {
  return pickNumber(resource?.likeCount) * 2 + pickNumber(resource?.favoriteCount) * 3
}

const formatCount = value => {
  const count = pickNumber(value)
  if (count >= 10000) return `${(count / 10000).toFixed(count >= 100000 ? 0 : 1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(count >= 10000 ? 0 : 1)}k`
  return String(count)
}

const toggleResourceLike = async resource => {
  const resourceId = getReactionId(resource)
  if (!resourceId || isReactionLoading(resource, 'like')) return

  const nextLiked = !resource.isLiked
  const nextCount = Math.max(0, pickNumber(resource.likeCount) + (nextLiked ? 1 : -1))
  const optimistic = { ...resource, isLiked: nextLiked, likeCount: nextCount }
  updateResourceState(optimistic)
  setReactionLoading(resource, 'like', true)

  try {
    const result = nextLiked ? await likeResource(resourceId) : await unlikeResource(resourceId)
    const data = result?.data || result || {}
    updateResourceState({
      ...optimistic,
      ...normalizeReactionFields({ ...optimistic, ...data })
    })
  } catch (error) {
    console.error('资源点赞状态更新失败', error)
    updateResourceState(resource)
    window.alert('点赞失败，请稍后重试')
  } finally {
    setReactionLoading(resource, 'like', false)
  }
}

const toggleResourceFavorite = async resource => {
  const resourceId = getReactionId(resource)
  if (!resourceId || isReactionLoading(resource, 'favorite')) return

  const nextFavorited = !resource.isFavorited
  const nextCount = Math.max(0, pickNumber(resource.favoriteCount) + (nextFavorited ? 1 : -1))
  const optimistic = { ...resource, isFavorited: nextFavorited, favoriteCount: nextCount }
  updateResourceState(optimistic)
  setReactionLoading(resource, 'favorite', true)

  try {
    const result = nextFavorited ? await favoriteResource(resourceId) : await unfavoriteResource(resourceId)
    const data = result?.data || result || {}
    updateResourceState({
      ...optimistic,
      ...normalizeReactionFields({ ...optimistic, ...data })
    })
  } catch (error) {
    console.error('资源收藏状态更新失败', error)
    updateResourceState(resource)
    window.alert('收藏失败，请稍后重试')
  } finally {
    setReactionLoading(resource, 'favorite', false)
  }
}

// 切换资源大类
const switchCategory = cat => {
  activeCategory.value = cat
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
  return text ? text.slice(0, 118) : '暂无内容可展示'
}

const getResourceExcerpt = resource => {
  if (isMindmapResource(resource)) return '思维导图，点击预览查看完整内容'
  if (isVideoResource(resource)) return '点击预览视频内容'
  return getExcerpt(resource?.content)
}

const handleImageError = event => {
  event.target.style.display = 'none'
}

const getWordCount = content => {
  return String(content || '').replace(/\s/g, '').length
}

const formatDate = (value, withTime = false) => {
  if (!value) return '未知日期'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return '未知日期'

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {})
  })
}

const handleUserLogin = () => { loadResources() }

watch(
  () => route.fullPath,
  () => {
    pendingNotificationOpen.value = ''
    openNotificationTargetResource()
  }
)

onMounted(() => {
  loadResources()
  window.addEventListener('zhiban:user-logged-in', handleUserLogin)
})
onBeforeUnmount(() => {
  window.removeEventListener('zhiban:user-logged-in', handleUserLogin)
})
</script>

<style scoped>
.resource-center-page {
  width: 100vw;
  height: 100vh;
  padding: 26px 34px 30px;
  background: #fdfcf7;
  color: #163f8f;
  font-family: "Open Sans", "PingFang SC", "Microsoft YaHei", sans-serif;
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

.icon-btn:hover,
.import-link:hover {
  background: #c9dce9;
  border-color: #5f8fc3;
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);
  transform: translateY(-1px);
}

.header-actions,
.card-top,
.resource-card footer {
  display: flex;
  align-items: center;
}

.header-actions {
  gap: 10px;
}

.center-header h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.15;
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

.resource-list {
  min-height: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(245px, 1fr));
  align-content: start;
  gap: 14px;
  padding-right: 4px;
}

.resource-card {
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

.visibility {
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

.resource-list::-webkit-scrollbar {
  width: 9px;
}

.resource-list::-webkit-scrollbar-track {
  background: #c9dce9;
  border-radius: 999px;
}

.resource-list::-webkit-scrollbar-thumb {
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

.resource-fullscreen__content--media {
  padding: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #081733;
}

.resource-fullscreen__audio {
  display: flex;
  justify-content: flex-end;
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

.preview-iframe,
.preview-video {
  width: 100%;
  height: 100%;
  max-height: none;
  min-height: 360px;
  border-radius: 12px;
  display: block;
  border: none;
  background: #000;
  object-fit: contain;
}

.resource-fullscreen__content--media .preview-iframe {
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: 24px;
}

.resource-fullscreen__content--media .preview-video {
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: 24px;
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

/* 玻璃拟态面板样式 */
.resource-center-page {
  width: 100vw;
  height: 100vh;
  padding: 28px 34px 28px;
  position: relative;
  isolation: isolate;
  background: #f1f7fb;
  color: #163f8f;
  gap: 20px;
  overflow: hidden;
}

.page-bg-deco {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: #f1f7fb;
  overflow: hidden;
  pointer-events: none;
}

.page-bg-deco::before,
.page-bg-deco::after,
.sweep {
  position: absolute;
  display: block;
  border-radius: 50%;
  background: #e9eff3;
}

.page-bg-deco::before,
.page-bg-deco::after {
  content: "";
}

.page-bg-deco::before {
  width: clamp(540px, 62vw, 760px);
  height: clamp(540px, 62vw, 760px);
  left: 50%;
  top: -96px;
  transform: translateX(-50%);
}

.page-bg-deco::after {
  width: clamp(420px, 48vw, 620px);
  height: clamp(420px, 48vw, 620px);
  right: clamp(-280px, -18vw, -170px);
  bottom: clamp(-310px, -24vw, -210px);
}

.sweep-one {
  width: clamp(320px, 34vw, 520px);
  height: clamp(320px, 34vw, 520px);
  left: clamp(-250px, -14vw, -140px);
  top: 118px;
}

.sweep-two {
  width: clamp(320px, 34vw, 520px);
  height: clamp(320px, 34vw, 520px);
  right: clamp(-220px, -12vw, -130px);
  top: -92px;
}

.center-header {
  display: grid;
  grid-template-columns: max-content minmax(320px, 1fr) max-content max-content;
  align-items: center;
  gap: 12px;
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
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  min-width: max-content;
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
  white-space: nowrap;
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

/* 分类导航 */
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
  height: 330px;
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

.resource-cover {
  height: 108px;
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

.resource-card::after {
  display: none;
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
  max-height: 38px;
  flex-shrink: 0;
}

.resource-card footer {
  margin-top: auto;
  font-size: 11px;
  line-height: 1.2;
  position: relative;
  z-index: 1;
  flex-shrink: 0;
}

.resource-card-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 30px;
  width: 100%;
  position: relative;
  z-index: 2;
  flex-shrink: 0;
}

.reaction-btn {
  height: 30px;
  min-width: 46px;
  padding: 0 7px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: #45617e;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font: inherit;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.reaction-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(22, 63, 143, 0.32);
  background: #ffffff;
}

.reaction-btn.active {
  border-color: rgba(22, 63, 143, 0.36);
  background: #163f8f;
  color: #ffffff;
}

.reaction-btn.active svg {
  fill: currentColor;
}

.reaction-btn:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.reaction-btn--meta {
  height: 30px;
  min-width: 62px;
  background: rgba(22, 63, 143, 0.08);
}

.resource-fullscreen__actions {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
  position: relative;
  z-index: 2;
}

.resource-action {
  width: 30px;
  height: 30px;
  min-height: 30px;
  padding: 0;
  border: 1px solid rgba(22, 63, 143, 0.18);
  border-radius: 999px;
  background: #163f8f;
  color: #fafafa;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  font-size: 12px;
  font-weight: 800;
  font-family: inherit;
  cursor: pointer;
  gap: 5px;
  flex: 0 0 auto;
}

.resource-action:disabled {
  opacity: 0.62;
  cursor: wait;
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
  gap: 10px;
  overflow: hidden;
}

.hot-list > span {
  height: 2px;
  margin-left: 26px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(to right, transparent, rgba(201, 220, 233, 0.74) 18%, rgba(201, 220, 233, 0.74) 82%, transparent);
}

.hot-resource-card {
  min-height: 74px;
  margin-left: 20px;
  padding: 10px 10px;
  border: 1px solid rgba(22, 63, 143, 0.12);
  border-radius: 14px;
  background: rgba(250, 250, 250, 0.72);
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  grid-template-areas:
    "rank body"
    "rank stats";
  align-items: center;
  gap: 5px 8px;
  text-align: left;
  color: #163f8f;
  cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}

.hot-resource-card:hover {
  transform: translateX(3px);
  border-color: rgba(22, 63, 143, 0.28);
  background: #ffffff;
}

.hot-resource-card__rank {
  grid-area: rank;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  background: #163f8f;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 900;
}

.hot-resource-card__body {
  grid-area: body;
  min-width: 0;
  display: grid;
  gap: 2px;
}

.hot-resource-card__body strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 900;
}

.hot-resource-card__body small {
  color: #6c7e96;
  font-size: 11px;
  font-weight: 800;
}

.hot-resource-card__stats {
  grid-area: stats;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #55708d;
  font-size: 11px;
  font-weight: 900;
}

.hot-resource-card__stats span {
  display: inline-flex;
  align-items: center;
  gap: 3px;
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

