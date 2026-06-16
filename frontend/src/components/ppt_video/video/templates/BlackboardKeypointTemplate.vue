<template>
  <section
    class="blackboard-keypoint-template"
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
    />

    <BoardVisualBlock
      class="blackboard-keypoint-template__visual"
      :terms="terms"
    />
  </section>
</template>

<script setup>
import { computed } from 'vue'
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
  }
})

const displayItems = computed(() => {
  const items = Array.isArray(props.slide.items) ? props.slide.items : []
  return items.length ? items : [props.slide.summary].filter(Boolean)
})

const terms = computed(() => getSlideTerms(props.slide))
const flip = computed(() => Number(props.slide?.index || 0) % 2 === 1)
</script>

<style scoped>
.blackboard-keypoint-template {
  position: absolute;
  inset: 82px 54px 104px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  grid-template-rows: minmax(0, 0.72fr) minmax(160px, 0.9fr);
  grid-template-areas:
    "header visual"
    "body   visual";
  gap: 22px 28px;
  color: var(--video-text);
}

.blackboard-keypoint-template *,
.blackboard-keypoint-template *::before,
.blackboard-keypoint-template *::after {
  box-sizing: border-box;
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
  gap: 16px 22px;
}

.blackboard-keypoint-template.is-dense :deep(.board-header-block h2) {
  font-size: clamp(24px, 2.6vw, 38px);
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
    inset: 72px 24px 104px;
    grid-template-columns: 1fr;
    grid-template-rows: auto auto minmax(160px, 1fr);
    grid-template-areas:
      "header"
      "body"
      "visual";
  }
}
</style>
