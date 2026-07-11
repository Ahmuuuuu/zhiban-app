<template>
  <div class="video-style-selector">
    <span class="video-style-selector__label">视频风格</span>
    <div class="video-style-selector__chips">
      <button
        v-for="variant in variants"
        :key="variant.key"
        type="button"
        class="video-style-selector__chip"
        :class="{ active: modelValue === variant.key }"
        :style="chipStyle(variant)"
        :title="variant.label"
        @click="$emit('update:modelValue', variant.key)"
      >
        <span class="video-style-selector__swatch" :style="{ background: variant.swatch }"></span>
        <span class="video-style-selector__name">{{ variant.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

defineEmits(['update:modelValue'])

const variants = [
  { key: '',          label: '默认深蓝',   swatch: 'linear-gradient(135deg, #0e2444, #1f63d6)' },
  { key: 'chalkboard', label: '黑板粉笔',   swatch: 'linear-gradient(135deg, #1a3a2a, #3a6a4a)' },
  { key: 'glass',     label: '毛玻璃',     swatch: 'linear-gradient(135deg, #eef3f8, #c8ddf0)' },
  { key: 'neon',      label: '赛博霓虹',   swatch: 'linear-gradient(135deg, #0a0a14, #5064ff)' },
  { key: 'paper',     label: '纸质笔记',   swatch: 'linear-gradient(135deg, #faf6ed, #e8dcc8)' },
  { key: 'midnight',  label: '午夜金辉',   swatch: 'linear-gradient(135deg, #0b1525, #c9a84c)' },
]

const chipStyle = variant => ({
  '--variant-swatch': variant.swatch
})
</script>

<style scoped>
.video-style-selector {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.video-style-selector__label {
  font-size: 12px;
  font-weight: 800;
  color: var(--color-muted, #7a756b);
  white-space: nowrap;
}

.video-style-selector__chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.video-style-selector__chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 0 10px;
  border: 2px solid rgba(201, 220, 233, 0.6);
  border-radius: 999px;
  background: var(--color-card, #fff);
  color: var(--color-text, #1f1f1a);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
}

.video-style-selector__chip:hover {
  border-color: rgba(22, 63, 143, 0.35);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--color-shadow, rgba(22, 63, 143, 0.08));
}

.video-style-selector__chip.active {
  border-color: #163f8f;
  background: #eef4fa;
  box-shadow: 0 0 0 3px rgba(22, 63, 143, 0.1);
}

html[data-theme="dark"] .video-style-selector__chip.active {
  border-color: #5b9bd5;
  background: rgba(91, 155, 213, 0.15);
  box-shadow: 0 0 0 3px rgba(91, 155, 213, 0.15);
}

.video-style-selector__swatch {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1px solid rgba(0,0,0,0.1);
  flex-shrink: 0;
  background: var(--variant-swatch);
}

.video-style-selector__name {
  white-space: nowrap;
}
</style>
