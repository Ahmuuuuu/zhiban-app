<template>
  <section v-if="slides.length" class="ppt-preview">
    <article class="ppt-slide">
      <div class="ppt-slide__meta">
        <span>{{ activeIndex + 1 }} / {{ slides.length }}</span>
        <strong>{{ title || 'PPT Preview' }}</strong>
      </div>

      <div class="ppt-slide__stage">
        <h3>{{ currentSlide.title || title }}</h3>

        <div class="ppt-slide__content">
          <p v-for="(line, index) in slideLines" :key="index">{{ line }}</p>
        </div>
      </div>

      <aside v-if="currentSlide.notes" class="ppt-slide__notes">
        <span>讲稿</span>
        <p>{{ currentSlide.notes }}</p>
      </aside>
    </article>

    <div class="ppt-controls">
      <button type="button" :disabled="activeIndex <= 0" @click="activeIndex -= 1">上一页</button>
      <div class="ppt-dots">
        <button
          v-for="(slide, index) in slides"
          :key="slide.index ?? index"
          type="button"
          :class="{ active: index === activeIndex }"
          :aria-label="`第 ${index + 1} 页`"
          @click="activeIndex = index"
        ></button>
      </div>
      <button type="button" :disabled="activeIndex >= slides.length - 1" @click="activeIndex += 1">下一页</button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  slides: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: ''
  }
})

const activeIndex = ref(0)

const currentSlide = computed(() => {
  const slide = props.slides[activeIndex.value] || props.slides[0] || {}
  return {
    index: Number(slide.index ?? activeIndex.value),
    title: slide.title || '',
    text: slide.text || slide.content || '',
    notes: slide.notes || slide.speaker_notes || ''
  }
})

const slideLines = computed(() => {
  return String(currentSlide.value.text || '')
    .split(/\r?\n|[;；]/)
    .map(line => line.replace(/^[-*•]\s+/, '').trim())
    .filter(Boolean)
})

watch(
  () => props.slides,
  () => {
    activeIndex.value = 0
  }
)
</script>

<style scoped>
.ppt-preview {
  display: grid;
  gap: 16px;
}

.ppt-slide {
  aspect-ratio: 16 / 9;
  min-height: 0;
  padding: clamp(20px, 3vw, 42px);
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 20px 50px rgba(22, 63, 143, 0.16);
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: hidden;
}

.ppt-slide__meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
  text-transform: uppercase;
}

.ppt-slide__stage {
  min-height: 0;
  flex: 1;
  display: grid;
  align-content: center;
  gap: clamp(18px, 3vw, 34px);
}

.ppt-slide h3 {
  margin: 0;
  color: #163f8f;
  font-size: clamp(28px, 5vw, 56px);
  line-height: 1.12;
  text-align: center;
}

.ppt-slide__content {
  width: min(78%, 760px);
  margin: 0 auto;
  color: rgba(22, 63, 143, 0.82);
  font-size: clamp(16px, 2.1vw, 25px);
  line-height: 1.55;
}

.ppt-slide__content p {
  position: relative;
  margin: 0 0 12px;
  padding-left: 1.1em;
}

.ppt-slide__content p::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 0.38em;
  height: 0.38em;
  border-radius: 50%;
  background: #5f8fc3;
}

.ppt-slide__notes {
  max-height: 24%;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(201, 220, 233, 0.24);
  color: rgba(22, 63, 143, 0.72);
  overflow: auto;
}

.ppt-slide__notes span {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.ppt-slide__notes p {
  margin: 5px 0 0;
  line-height: 1.65;
}

.ppt-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ppt-controls > button {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: #fff;
  color: #163f8f;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.ppt-controls > button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ppt-dots {
  min-width: 0;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
}

.ppt-dots button {
  width: 9px;
  height: 9px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(95, 143, 195, 0.32);
  cursor: pointer;
}

.ppt-dots button.active {
  background: #163f8f;
}
</style>
