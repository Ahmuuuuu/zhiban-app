<template>
  <section
    class="blackboard-keypoint-template video-fit-stage"
    :class="{ 'is-dense': displayItems.length > 4, 'is-flipped': flip }"
  >
    <BoardHeaderBlock
      class="blackboard-keypoint-template__header"
      :kicker="slide.chapterTitle"
      :title="slide.title || '课程讲解'"
      :summary="slide.summary"
    />

    <BoardBulletListBlock
      class="blackboard-keypoint-template__body"
      :items="displayItems"
      :rendered-items="karaokeItems"
    />

    <BoardVisualBlock
      class="blackboard-keypoint-template__visual"
      :terms="terms"
    />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath, renderKaraokeHTML } from '../../../../utils/renderMath'
import { getSlideTerms } from '../logic/videoSlideClassifier'
import BoardBulletListBlock from '../primitives/blocks/BoardBulletListBlock.vue'
import BoardHeaderBlock from '../primitives/blocks/BoardHeaderBlock.vue'
import BoardVisualBlock from '../primitives/blocks/BoardVisualBlock.vue'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  },
  layoutSeed: {
    type: Number,
    default: 0
  },
  timedWords: {
    type: Array,
    default: () => []
  }
})

const displayItems = computed(() => {
  const items = Array.isArray(props.slide.items) ? props.slide.items : []
  return items.length ? items : [props.slide.summary].filter(Boolean)
})

const terms = computed(() => getSlideTerms(props.slide))
const flip = computed(() => Number(props.slide?.index || 0) % 2 === 1)

const karaokeItems = computed(() => {
  const words = props.timedWords || []
  if (!words.length) return displayItems.value.map(item => renderMath(item))

  let offset = 0
  offset += renderKaraokeHTML(props.slide.title || '', words, offset).consumed

  const summaryText = props.slide.summary || ''
  const itemsText = displayItems.value.join(' ')
  if (summaryText && !itemsText.includes(summaryText.slice(0, 10))) {
    offset += renderKaraokeHTML(summaryText, words, offset).consumed
  }

  return displayItems.value.map(item => {
    const { html, consumed } = renderKaraokeHTML(item, words, offset)
    offset += consumed
    return html
  })
})
</script>

<style scoped>
.blackboard-keypoint-template {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-areas:
    "header visual"
    "body   visual";
  gap: calc(var(--video-gap) * 0.8) var(--video-gap);
}

/* ===== grid areas ===== */
.blackboard-keypoint-template__header { grid-area: header; }
.blackboard-keypoint-template__body   { grid-area: body; }
.blackboard-keypoint-template__visual { grid-area: visual; }

/* ===== flip: visual panel on left ===== */
.blackboard-keypoint-template.is-flipped {
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  grid-template-areas:
    "visual header"
    "visual body";
}

/* ===== Dense — only shrink, keep layout ===== */
.blackboard-keypoint-template.is-dense {
  gap: calc(var(--video-gap) * 0.62) calc(var(--video-gap) * 0.78);
}

.blackboard-keypoint-template.is-dense :deep(.board-header-block h2) {
  font-size: var(--video-title-tight-size);
}

.blackboard-keypoint-template.is-dense :deep(.board-header-block p) {
  max-width: 100%;
  font-size: clamp(12px, 0.94vw, 16px);
  line-height: 1.45;
}

/* ===== Animations ===== */
.blackboard-keypoint-template__header {
  animation: header-in 0.58s ease both;
}

@keyframes header-in {
  from { opacity: 0; transform: translateY(18px); }
  to   { opacity: 1; transform: translateY(0); }
}

@media (max-width: 980px) {
  .blackboard-keypoint-template {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto minmax(160px, 1fr);
    grid-template-areas:
      "header"
      "body"
      "visual";
  }
}
</style>
