<template>
  <section class="video-transcript">
    <button class="video-transcript__toggle" type="button" @click="open = !open">
      <span>讲稿摘录</span>
      <b>{{ open ? '收起' : '展开' }}</b>
    </button>

    <div v-if="open" class="video-transcript__body">
      <article
        v-for="(paragraph, index) in paragraphs"
        :key="index"
        class="video-transcript__item"
      >
        <span>{{ index + 1 }}</span>
        <p>{{ paragraph }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  paragraphs: {
    type: Array,
    default: () => []
  }
})

const open = ref(false)
</script>

<style scoped>
.video-transcript {
  min-height: 0;
}

.video-transcript__toggle {
  width: 100%;
  min-height: 38px;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  color: #163f8f;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 11px;
  font-weight: 900;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.video-transcript__toggle:hover {
  border-color: rgba(47, 125, 225, 0.36);
  background: rgba(255, 255, 255, 0.92);
}

.video-transcript__toggle b {
  color: #5f8fc3;
  font-size: 12px;
}

.video-transcript__body {
  max-height: 210px;
  margin-top: 8px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.58);
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.video-transcript__item {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.video-transcript__item span {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: rgba(201, 220, 233, 0.7);
  color: #5f8fc3;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 900;
}

.video-transcript__item p {
  margin: 0;
  color: rgba(31, 51, 86, 0.76);
  line-height: 1.65;
  font-size: 13px;
}
</style>
