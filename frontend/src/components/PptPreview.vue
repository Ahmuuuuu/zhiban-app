<template>
  <section v-if="localSlides.length" class="ppt-preview">
    <div class="ppt-toolbar">
      <div class="ppt-toolbar__title">
        <span>{{ activeIndex + 1 }} / {{ localSlides.length }}</span>
        <strong>{{ title || 'PPT Preview' }}</strong>
      </div>

      <button class="edit-toggle" type="button" @click="editing = !editing">
        {{ editing ? '&#x5B8C;&#x6210;&#x7F16;&#x8F91;' : '&#x7F16;&#x8F91;&#x5185;&#x5BB9;' }}
      </button>
    </div>

    <article class="ppt-slide" :class="{ editing }">
      <div class="ppt-slide__stage">
        <input
          v-if="editing"
          class="slide-title-input"
          :value="currentSlide.title || title"
          @input="updateSlideField('title', $event.target.value)"
        />
        <h3 v-else>{{ currentSlide.title || title }}</h3>

        <textarea
          v-if="editing"
          class="slide-content-input"
          :value="currentSlide.text"
          @input="updateSlideField('text', $event.target.value)"
        ></textarea>

        <div v-else class="ppt-slide__content">
          <p v-for="(line, index) in slideLines" :key="index">{{ line }}</p>
        </div>
      </div>

      <aside class="ppt-slide__notes">
        <span>&#x8BB2;&#x7A3F;</span>
        <textarea
          v-if="editing"
          :value="currentSlide.notes"
          @input="updateSlideField('notes', $event.target.value)"
        ></textarea>
        <p v-else>{{ currentSlide.notes || '&#x6682;&#x65E0;&#x8BB2;&#x7A3F;' }}</p>
      </aside>
    </article>

    <div class="ppt-controls">
      <button type="button" :disabled="activeIndex <= 0" @click="activeIndex -= 1">&#x4E0A;&#x4E00;&#x9875;</button>
      <div class="ppt-dots">
        <button
          v-for="(slide, index) in localSlides"
          :key="slide.index ?? index"
          type="button"
          :class="{ active: index === activeIndex }"
          :aria-label="`slide ${index + 1}`"
          @click="activeIndex = index"
        ></button>
      </div>
      <button type="button" :disabled="activeIndex >= localSlides.length - 1" @click="activeIndex += 1">&#x4E0B;&#x4E00;&#x9875;</button>
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

const emit = defineEmits(['update:slides', 'change'])

const activeIndex = ref(0)
const editing = ref(false)
const localSlides = ref([])

const normalizeSlide = (slide, index) => ({
  ...slide,
  index: Number(slide?.index ?? index),
  title: slide?.title || '',
  text: slide?.text || slide?.content || '',
  content: slide?.content || slide?.text || '',
  notes: slide?.notes || slide?.speaker_notes || '',
  speaker_notes: slide?.speaker_notes || slide?.notes || ''
})

const syncLocalSlides = slides => {
  localSlides.value = (Array.isArray(slides) ? slides : []).map(normalizeSlide)
  if (activeIndex.value >= localSlides.value.length) {
    activeIndex.value = Math.max(localSlides.value.length - 1, 0)
  }
}

const currentSlide = computed(() => localSlides.value[activeIndex.value] || localSlides.value[0] || {})

const slideLines = computed(() => {
  return String(currentSlide.value.text || '')
    .split(/\r?\n|[;；]/)
    .map(line => line.replace(/^[-*•\s]+/, '').trim())
    .filter(Boolean)
})

const publishSlides = () => {
  const slides = localSlides.value.map(slide => ({
    ...slide,
    content: slide.text,
    speaker_notes: slide.notes
  }))
  emit('update:slides', slides)
  emit('change', slides)
}

const updateSlideField = (field, value) => {
  const slide = localSlides.value[activeIndex.value]
  if (!slide) return

  localSlides.value[activeIndex.value] = {
    ...slide,
    [field]: value,
    ...(field === 'text' ? { content: value } : {}),
    ...(field === 'notes' ? { speaker_notes: value } : {})
  }
  publishSlides()
}

watch(
  () => props.slides,
  slides => {
    syncLocalSlides(slides)
    activeIndex.value = 0
  },
  { immediate: true, deep: true }
)
</script>

<style scoped>
.ppt-preview {
  display: grid;
  gap: 14px;
}

.ppt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ppt-toolbar__title {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.ppt-toolbar__title strong {
  max-width: 420px;
  overflow: hidden;
  color: #163f8f;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edit-toggle,
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

.edit-toggle {
  border-color: rgba(22, 63, 143, 0.9);
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

.ppt-slide.editing {
  outline: 2px solid rgba(95, 143, 195, 0.36);
  outline-offset: 3px;
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

.slide-title-input,
.slide-content-input,
.ppt-slide__notes textarea {
  width: 100%;
  border: 1px solid rgba(95, 143, 195, 0.42);
  border-radius: 8px;
  background: rgba(237, 249, 252, 0.46);
  color: #163f8f;
  font: inherit;
  outline: none;
}

.slide-title-input {
  min-height: 58px;
  padding: 0 16px;
  font-size: clamp(24px, 4vw, 46px);
  font-weight: 900;
  text-align: center;
}

.slide-content-input {
  min-height: 150px;
  padding: 14px 16px;
  resize: vertical;
  font-size: 18px;
  line-height: 1.6;
}

.ppt-slide__notes {
  max-height: 26%;
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

.ppt-slide__notes textarea {
  min-height: 74px;
  margin-top: 6px;
  padding: 10px 12px;
  resize: vertical;
  line-height: 1.6;
}

.ppt-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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
