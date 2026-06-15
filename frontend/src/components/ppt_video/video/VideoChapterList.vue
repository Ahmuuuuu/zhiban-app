<template>
  <section class="video-chapters">
    <header class="video-chapters__header">
      <span>章节导航</span>
      <small>{{ chapters.length }} 段</small>
    </header>

    <div class="video-chapters__list">
      <button
        v-for="chapter in chapters"
        :key="chapter.id"
        class="video-chapter"
        type="button"
        :class="{ active: chapter.id === activeChapterId }"
        @click="$emit('select', chapter)"
      >
        <span class="video-chapter__marker">{{ chapter.index + 1 }}</span>
        <span class="video-chapter__content">
          <b>{{ chapter.title }}</b>
          <small>点击播放此段内容</small>
        </span>
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  chapters: {
    type: Array,
    default: () => []
  },
  activeChapterId: {
    type: String,
    default: ''
  }
})

defineEmits(['select'])
</script>

<style scoped>
.video-chapters {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.video-chapters__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.video-chapters__header small {
  color: rgba(31, 51, 86, 0.46);
}

.video-chapters__list {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.video-chapters__list::before {
  content: "";
  position: absolute;
  top: 18px;
  bottom: 18px;
  left: 15px;
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(47, 125, 225, 0.24), rgba(91, 201, 188, 0.08));
}

.video-chapter {
  position: relative;
  width: 100%;
  min-height: 52px;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.68);
  color: #163f8f;
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.video-chapter:hover {
  border-color: rgba(47, 125, 225, 0.42);
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
}

.video-chapter__marker {
  position: relative;
  z-index: 1;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid rgba(201, 220, 233, 0.9);
  display: grid;
  place-items: center;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
  box-shadow: 0 6px 16px rgba(31, 51, 86, 0.08);
}

.video-chapter__content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.video-chapter__content b {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 13px;
}

.video-chapter__content small {
  color: rgba(31, 51, 86, 0.46);
  font-size: 11px;
}

.video-chapter.active {
  border-color: rgba(47, 125, 225, 0.56);
  background: linear-gradient(135deg, rgba(47, 125, 225, 0.14), rgba(91, 201, 188, 0.12));
}

.video-chapter.active .video-chapter__marker {
  background: linear-gradient(135deg, #2f7de1, #5bc9bc);
  border-color: transparent;
  color: #ffffff;
}
</style>
