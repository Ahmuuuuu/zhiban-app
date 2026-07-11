<template>
  <div class="template-picker">
    <div class="template-picker__header">
      <h3>选择 PPT 模板</h3>
      <span class="template-picker__count">{{ PPT_THEMES.length }} 套模板</span>
    </div>

    <div class="template-picker__filters">
      <button
        v-for="cat in THEME_CATEGORIES"
        :key="cat"
        type="button"
        class="filter-chip"
        :class="{ active: activeCategory === cat }"
        @click="activeCategory = cat"
      >{{ cat }}</button>
    </div>

    <div class="template-picker__grid">
      <button
        v-for="theme in filteredThemes"
        :key="theme.id"
        type="button"
        class="theme-card"
        :class="{ selected: modelValue === theme.id, 'is-dark': theme.dark }"
        :title="theme.desc"
        @click="$emit('update:modelValue', theme.id)"
      >
        <div class="theme-card__preview" :style="{ background: theme.palette[3] }">
          <div class="theme-card__band" :style="{ background: theme.palette[0] }"></div>
          <div class="theme-card__deco">
            <span :style="{ background: theme.palette[1], opacity: 0.6 }"></span>
            <span :style="{ background: theme.palette[2], opacity: 0.5 }"></span>
          </div>
        </div>
        <div class="theme-card__info">
          <strong :style="{ color: theme.dark ? '#e4e6ed' : '#1f1f1a' }">{{ theme.label }}</strong>
          <span class="theme-card__swatches">
            <i v-for="(c, ci) in theme.palette" :key="ci" :style="{ background: c }"></i>
          </span>
        </div>
        <div v-if="modelValue === theme.id" class="theme-card__check">✓</div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { PPT_THEMES, THEME_CATEGORIES } from '../../../data/pptThemes'

defineProps({
  modelValue: { type: String, default: 'minimal-white' }
})

defineEmits(['update:modelValue'])

const activeCategory = ref('全部')

const filteredThemes = computed(() =>
  activeCategory.value === '全部'
    ? PPT_THEMES
    : PPT_THEMES.filter(t => t.category === activeCategory.value)
)
</script>

<style scoped>
.template-picker {
  width: 100%;
  max-height: 520px;
  overflow-y: auto;
  padding: 4px 2px;
}

.template-picker::-webkit-scrollbar { width: 6px; }
.template-picker::-webkit-scrollbar-thumb { border-radius: 999px; background: rgba(95,143,195,0.4); }

.template-picker__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}
.template-picker__header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: var(--color-text-heading, #143761);
}
.template-picker__count {
  font-size: 12px;
  color: var(--color-muted, #7a756b);
}

.template-picker__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}
.filter-chip {
  min-height: 28px;
  padding: 0 12px;
  border: 1px solid var(--color-border, #e5ded3);
  border-radius: 999px;
  background: var(--color-card, #fff);
  color: var(--color-text, #1f1f1a);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}
.filter-chip:hover { border-color: #5f8fc3; }
.filter-chip.active {
  background: #163f8f;
  border-color: #163f8f;
  color: #fff;
}

.template-picker__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 10px;
}

.theme-card {
  position: relative;
  border: 2px solid var(--color-border, #e5ded3);
  border-radius: 12px;
  background: var(--color-card, #fff);
  overflow: hidden;
  cursor: pointer;
  text-align: left;
  font: inherit;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
}
.theme-card:hover {
  border-color: #5f8fc3;
  box-shadow: 0 8px 24px var(--color-shadow, rgba(22,63,143,0.1));
  transform: translateY(-2px);
}
.theme-card.selected {
  border-color: #163f8f;
  box-shadow: 0 0 0 3px rgba(22,63,143,0.12);
}
.theme-card__preview {
  height: 72px;
  position: relative;
  overflow: hidden;
}
.theme-card__band {
  height: 18px;
  width: 100%;
}
.theme-card__deco {
  position: absolute;
  right: 6px;
  top: 28px;
  display: flex;
  gap: 4px;
}
.theme-card__deco span {
  width: 22px;
  height: 22px;
  border-radius: 50%;
}
.theme-card__info {
  padding: 8px 10px 10px;
}
.theme-card__info strong {
  display: block;
  font-size: 13px;
  font-weight: 800;
}
.theme-card__swatches {
  display: flex;
  gap: 4px;
  margin-top: 6px;
}
.theme-card__swatches i {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid rgba(0,0,0,0.08);
}

.theme-card__check {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #163f8f;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  display: grid;
  place-items: center;
}

/* dark mode */
html[data-theme="dark"] .theme-card { background: #1a2535; border-color: #2a3546; }
html[data-theme="dark"] .theme-card:hover { border-color: #5b9bd5; }
html[data-theme="dark"] .theme-card.selected { border-color: #52b86f; box-shadow: 0 0 0 3px rgba(82,184,111,0.15); }
html[data-theme="dark"] .theme-card__check { background: #52b86f; }
html[data-theme="dark"] .template-picker__header h3 { color: #c8d6e5; }
html[data-theme="dark"] .filter-chip { background: #1a2535; border-color: #2a3546; color: #c8d6e5; }
html[data-theme="dark"] .filter-chip.active { background: #52b86f; border-color: #52b86f; }
</style>
