<template>
  <ResourceMediaFrame :compact="!isPpt && !isVideo && !isHtml">
    <img
      v-if="isImage && resource.previewUrl"
      class="presentation-preview__image"
      :src="resource.previewUrl"
      :alt="resource.title"
      @error="$emit('image-error', $event)"
    />

    <iframe
      v-else-if="isHtml && resource.previewUrl"
      class="presentation-preview__iframe"
      :src="resource.previewUrl"
      frameborder="0"
      allowfullscreen
    ></iframe>

    <p v-else-if="isHtml" class="presentation-preview__empty">视频加载中，请稍后...</p>

    <VideoPreview
      v-else-if="isVideo"
      :src="resource.previewUrl"
      :title="resource.title"
      :content="resource.content"
      :fallback-text="resource.content || '暂无视频内容'"
    />

    <template v-else-if="isMindmap">
      <MindmapPreview
        :content="resource.fullContent || resource.content"
        :title="resource.title"
      />
      <div class="presentation-preview__actions">
        <button
          v-if="resource.downloadUrl"
          class="presentation-preview__download"
          type="button"
          @click="$emit('download', resource)"
        >
          下载思维导图文件
        </button>
      </div>
    </template>

    <template v-else-if="isPpt">
      <PptDeckPreview
        v-if="resource.slides?.length"
        v-model:slides="resource.slides"
        :title="resource.title"
        :editable="editable"
        :exporting="exporting"
        :annotatable="annotatable"
        :annotations="annotations"
        @export-pptx="$emit('export-pptx', $event)"
        @create-note="$emit('create-note', $event)"
        @update-note="(id, payload) => $emit('update-note', id, payload)"
        @delete-note="$emit('delete-note', $event)"
      />
      <div v-else-if="resource.previewUrl" class="presentation-preview__file-wrap">
        <img
          class="presentation-preview__image"
          :src="resource.previewUrl"
          :alt="resource.title"
          @error="$emit('image-error', $event)"
        />
      </div>
      <div v-else class="presentation-preview__placeholder">
        <Presentation :size="48" />
        <p>{{ resource.title || 'PPT 文件' }}</p>
        <button
          v-if="resource.downloadUrl"
          class="presentation-preview__download"
          type="button"
          @click="$emit('download', resource)"
        >
          下载 PPT 文件
        </button>
      </div>
    </template>

    <p v-else class="presentation-preview__empty">{{ resource.content || '暂无内容可展示' }}</p>
  </ResourceMediaFrame>
</template>

<script setup>
import { computed } from 'vue'
import { Presentation } from 'lucide-vue-next'
import MindmapPreview from '../../MindmapPreview.vue'
import PptDeckPreview from './PptDeckPreview.vue'
import ResourceMediaFrame from './ResourceMediaFrame.vue'
import VideoPreview from '../video/VideoPreview.vue'

const props = defineProps({
  resource: {
    type: Object,
    required: true
  },
  editable: {
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
  annotations: {
    type: Array,
    default: () => []
  }
})

defineEmits(['download', 'export-pptx', 'image-error', 'create-note', 'update-note', 'delete-note'])

const resourceText = computed(() => String([
  props.resource?.type,
  props.resource?.fileType,
  props.resource?.category,
  props.resource?.filename,
  props.resource?.title,
  props.resource?.previewUrl,
  props.resource?.downloadUrl
].filter(Boolean).join(' ')).toLowerCase())

const isImage = computed(() => props.resource?.type === 'image')
const isPpt = computed(() => /ppt|powerpoint|presentation|slide/.test(resourceText.value))
const isVideo = computed(() => /video|mp4|webm|ogg/.test(resourceText.value))
const isMindmap = computed(() => /mindmap|mind_map|mind-map|思维导图/.test(resourceText.value))
const isHtml = computed(() => !isPpt.value && /html|interactive|presentation-player|视频/.test(resourceText.value))
</script>

<style scoped>
.presentation-preview__image {
  width: 100%;
  max-height: 100%;
  border-radius: 8px;
  object-fit: contain;
  background: #e9eff3;
}

.presentation-preview__iframe {
  width: 100%;
  height: 100%;
  min-height: 520px;
  border: 0;
  border-radius: 8px;
  background: #ffffff;
}

.presentation-preview__file-wrap {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.presentation-preview__placeholder {
  width: min(100%, 520px);
  min-height: 300px;
  margin: auto;
  border: 1px dashed rgba(95, 143, 195, 0.5);
  border-radius: 8px;
  color: #5f8fc3;
  display: grid;
  place-items: center;
  gap: 12px;
  align-content: center;
  background: rgba(250, 250, 250, 0.72);
}

.presentation-preview__placeholder p,
.presentation-preview__empty {
  margin: 0;
  color: #5f8fc3;
  text-align: center;
}

.presentation-preview__actions {
  width: 100%;
  display: flex;
  justify-content: flex-end;
}

.presentation-preview__download {
  border: none;
  border-radius: 8px;
  padding: 10px 16px;
  background: #163f8f;
  color: #ffffff;
  cursor: pointer;
}
</style>
