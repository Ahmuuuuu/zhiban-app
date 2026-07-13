<template>
  <header class="board-header-block">
    <ChalkTag v-if="kicker">{{ kicker }}</ChalkTag>
    <h2>{{ title }}</h2>
    <ChalkLine />
    <p v-if="summary">{{ summary }}</p>
  </header>
</template>

<script setup>
import ChalkLine from '../atoms/ChalkLine.vue'
import ChalkTag from '../atoms/ChalkTag.vue'

defineProps({
  kicker: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  },
  summary: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.board-header-block {
  min-width: 0;
  min-height: 0;
  display: grid;
  align-content: end;
  gap: 12px;
  color: var(--video-text);
  overflow: hidden;
}

.board-header-block h2 {
  max-width: 820px;
  margin: 0;
  font-size: var(--video-title-size, clamp(30px, 3.7vw, 54px));
  line-height: 1.1;
  text-shadow: 0 4px 24px var(--video-shadow);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.board-header-block p {
  max-width: 780px;
  margin: 0;
  color: var(--video-muted);
  font-size: var(--video-body-size, clamp(13px, 1.02vw, 18px));
  line-height: 1.52;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

</style>
