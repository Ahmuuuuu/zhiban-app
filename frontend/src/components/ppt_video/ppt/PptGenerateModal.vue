<template>
  <Teleport to="body">
    <Transition name="ppt-gen-backdrop">
      <div v-if="visible" class="ppt-gen-overlay" @click.self="$emit('close')">
        <Transition name="ppt-gen-panel">
          <article v-if="visible" class="ppt-gen-panel">
            <!-- Header -->
            <header class="ppt-gen-panel__header">
              <div>
                <span class="ppt-gen-panel__eyebrow">PPT 生成</span>
                <h2>选择模板并描述需求</h2>
              </div>
              <button type="button" class="ppt-gen-panel__close" @click="$emit('close')">✕</button>
            </header>

            <!-- Body: split view -->
            <div class="ppt-gen-panel__body">
              <!-- Left: Template Picker -->
              <section class="ppt-gen-panel__templates">
                <div class="ppt-gen-panel__filters">
                  <button
                    v-for="cat in THEME_CATEGORIES"
                    :key="cat"
                    type="button"
                    class="filter-chip"
                    :class="{ active: activeCategory === cat }"
                    @click="activeCategory = cat"
                  >{{ cat }}</button>
                </div>
                <div class="ppt-gen-panel__grid">
                  <button
                    v-for="theme in filteredThemes"
                    :key="theme.id"
                    type="button"
                    class="theme-card"
                    :class="{ selected: selectedTheme === theme.id }"
                    @click="selectedTheme = theme.id"
                  >
                    <div class="theme-card__preview" :style="{ background: theme.palette[3] }">
                      <div class="theme-card__band" :style="{ background: theme.palette[0] }"></div>
                      <div class="theme-card__dots">
                        <span :style="{ background: theme.palette[1] }"></span>
                        <span :style="{ background: theme.palette[2] }"></span>
                      </div>
                    </div>
                    <span class="theme-card__label">{{ theme.label }}</span>
                    <span v-if="selectedTheme === theme.id" class="theme-card__check">✓</span>
                  </button>
                </div>
              </section>

              <!-- Right: Input area -->
              <section class="ppt-gen-panel__input">
                <div class="ppt-gen-panel__preview" v-if="previewTheme">
                  <div class="preview-thumb" :style="{ background: previewTheme.palette[3] }">
                    <div class="preview-thumb__band" :style="{ background: previewTheme.palette[0] }"></div>
                    <div class="preview-thumb__content">
                      <span class="preview-thumb__title" :style="{ color: previewTheme.dark ? '#e4e6ed' : '#1a1a1a' }">标题预览</span>
                      <span class="preview-thumb__dots">
                        <i v-for="(c, ci) in [1,2]" :key="ci" :style="{ background: previewTheme.palette[ci] }"></i>
                      </span>
                    </div>
                  </div>
                  <p>{{ previewTheme.label }} · {{ previewTheme.desc }}</p>
                </div>

                <label class="ppt-gen-panel__field">
                  <span>PPT 主题 / 课程名称</span>
                  <input
                    v-model="topic"
                    type="text"
                    placeholder="例如：高等数学第三章、Python入门教程..."
                    @keydown.enter="handleGenerate"
                  />
                </label>

                <label class="ppt-gen-panel__field">
                  <span>具体需求 <em>(可选)</em></span>
                  <textarea
                    v-model="requirements"
                    rows="3"
                    placeholder="例如：包含例题和练习题、适合初中生水平、多用图表..."
                  ></textarea>
                </label>

                <!-- Error -->
                <p v-if="error" class="ppt-gen-panel__error">{{ error }}</p>

                <!-- Actions -->
                <div class="ppt-gen-panel__actions">
                  <button type="button" class="btn-cancel" @click="$emit('close')">取消</button>
                  <button
                    type="button"
                    class="btn-generate"
                    :disabled="!topic.trim() || generating"
                    @click="handleGenerate"
                  >
                    {{ generating ? '生成中...' : '开始生成 PPT' }}
                  </button>
                </div>
              </section>
            </div>
          </article>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { PPT_THEMES, THEME_CATEGORIES, getThemeById, getDefaultTheme } from '../../../data/pptThemes'

const props = defineProps({
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'generate'])

const activeCategory = ref('全部')
const selectedTheme = ref(getDefaultTheme().id)
const topic = ref('')
const requirements = ref('')
const generating = ref(false)
const error = ref('')

const filteredThemes = computed(() =>
  activeCategory.value === '全部'
    ? PPT_THEMES
    : PPT_THEMES.filter(t => t.category === activeCategory.value)
)

const previewTheme = computed(() => getThemeById(selectedTheme.value))

const handleGenerate = () => {
  const t = topic.value.trim()
  if (!t) { error.value = '请输入 PPT 主题'; return }
  error.value = ''
  generating.value = true

  const theme = getThemeById(selectedTheme.value)
  const req = requirements.value.trim()

  // Send raw topic as the user-visible message, tool's prompt will prepend the generation prefix
  const userMessage = req ? `${t}（${req}）` : t

  emit('generate', {
    prompt: userMessage,
    topic: t,
    requirements: req,
    themeId: theme.id,
    theme
  })

  // Reset for next time
  setTimeout(() => {
    topic.value = ''
    requirements.value = ''
    generating.value = false
    selectedTheme.value = getDefaultTheme().id
  }, 600)
}
</script>

<style scoped>
/* ---- overlay ---- */
.ppt-gen-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(8, 18, 40, 0.55);
  backdrop-filter: blur(6px);
  display: grid;
  place-items: center;
  padding: 24px;
}

/* ---- panel ---- */
.ppt-gen-panel {
  width: min(960px, 100%);
  max-height: 85vh;
  background: var(--color-card, #ffffff);
  border-radius: 20px;
  box-shadow: 0 30px 80px rgba(0,0,0,0.3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ppt-gen-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 22px 26px 14px;
  border-bottom: 1px solid var(--color-border, #e5ded3);
}
.ppt-gen-panel__eyebrow {
  font-size: 11px;
  font-weight: 800;
  color: var(--color-muted, #7a756b);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.ppt-gen-panel__header h2 {
  margin: 4px 0 0;
  font-size: 20px;
  color: var(--color-text-heading, #143761);
}
.ppt-gen-panel__close {
  width: 32px; height: 32px;
  border: none; border-radius: 50%;
  background: var(--color-border, #e5ded3);
  color: var(--color-text, #1f1f1a);
  font-size: 14px;
  cursor: pointer;
  display: grid; place-items: center;
}

/* ---- body ---- */
.ppt-gen-panel__body {
  display: grid;
  grid-template-columns: 1fr 320px;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

/* ---- left: templates ---- */
.ppt-gen-panel__templates {
  overflow-y: auto;
  padding: 16px 20px;
}

.ppt-gen-panel__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 14px;
}
.filter-chip {
  min-height: 26px;
  padding: 0 10px;
  border: 1px solid var(--color-border, #e5ded3);
  border-radius: 999px;
  background: var(--color-card, #fff);
  color: var(--color-text, #1f1f1a);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}
.filter-chip:hover { border-color: #5f8fc3; }
.filter-chip.active { background: #163f8f; border-color: #163f8f; color: #fff; }

.ppt-gen-panel__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}

/* theme card (compact) */
.theme-card {
  position: relative;
  border: 2px solid var(--color-border, #e5ded3);
  border-radius: 10px;
  background: var(--color-card, #fff);
  cursor: pointer;
  font: inherit;
  text-align: left;
  padding: 0;
  overflow: hidden;
  transition: all 0.18s ease;
}
.theme-card:hover { border-color: #5f8fc3; transform: translateY(-1px); }
.theme-card.selected { border-color: #163f8f; box-shadow: 0 0 0 2px rgba(22,63,143,0.14); }
.theme-card__preview {
  height: 52px; position: relative; overflow: hidden;
}
.theme-card__band { height: 10px; }
.theme-card__dots {
  position: absolute; right: 4px; top: 16px; display: flex; gap: 3px;
}
.theme-card__dots span {
  width: 14px; height: 14px; border-radius: 50%; opacity: 0.55;
}
.theme-card__label {
  display: block; padding: 6px 8px 8px;
  font-size: 11px; font-weight: 700;
  color: var(--color-text, #1f1f1a);
}
.theme-card__check {
  position: absolute; top: 4px; right: 4px;
  width: 18px; height: 18px; border-radius: 50%;
  background: #163f8f; color: #fff;
  font-size: 11px; font-weight: 800;
  display: grid; place-items: center;
}

/* ---- right: input ---- */
.ppt-gen-panel__input {
  padding: 20px;
  border-left: 1px solid var(--color-border, #e5ded3);
  display: flex; flex-direction: column; gap: 16px;
  overflow-y: auto;
}

.ppt-gen-panel__preview {
  text-align: center;
}
.preview-thumb {
  width: 100%;
  height: 100px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border, #e5ded3);
  position: relative;
}
.preview-thumb__band { height: 24px; }
.preview-thumb__content {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; height: calc(100% - 24px); gap: 6px;
}
.preview-thumb__title { font-size: 14px; font-weight: 800; }
.preview-thumb__dots { display: flex; gap: 5px; }
.preview-thumb__dots i { width: 10px; height: 10px; border-radius: 50%; opacity: 0.7; }

.ppt-gen-panel__preview p {
  margin: 8px 0 0;
  font-size: 12px; color: var(--color-muted, #7a756b);
}

.ppt-gen-panel__field {
  display: grid; gap: 6px;
}
.ppt-gen-panel__field span {
  font-size: 12px; font-weight: 800;
  color: var(--color-text-heading, #143761);
}
.ppt-gen-panel__field em { font-weight: 400; color: var(--color-muted); }
.ppt-gen-panel__field input,
.ppt-gen-panel__field textarea {
  width: 100%; padding: 10px 12px;
  border: 1px solid var(--color-border, #e5ded3);
  border-radius: 10px;
  background: var(--color-card-hover, #f7fafd);
  color: var(--color-text, #1f1f1a);
  font: inherit; font-size: 13px;
  resize: vertical;
  outline: none;
}
.ppt-gen-panel__field input:focus,
.ppt-gen-panel__field textarea:focus {
  border-color: #5f8fc3;
  box-shadow: 0 0 0 3px rgba(95,143,195,0.1);
}

.ppt-gen-panel__error {
  margin: 0; color: #dc2626; font-size: 12px; font-weight: 700;
}

.ppt-gen-panel__actions {
  display: flex; gap: 10px; justify-content: flex-end;
  margin-top: auto; padding-top: 8px;
}
.btn-cancel, .btn-generate {
  min-height: 38px; padding: 0 20px; border-radius: 10px;
  font: inherit; font-size: 14px; font-weight: 800; cursor: pointer;
  transition: transform 0.15s ease;
}
.btn-cancel {
  border: 1px solid var(--color-border, #e5ded3);
  background: var(--color-card, #fff);
  color: var(--color-text, #1f1f1a);
}
.btn-generate {
  border: none;
  background: #163f8f;
  color: #fff;
  box-shadow: 0 6px 20px rgba(22,63,143,0.25);
}
.btn-generate:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-generate:not(:disabled):hover { transform: translateY(-1px); }

/* animations */
.ppt-gen-backdrop-enter-active, .ppt-gen-backdrop-leave-active {
  transition: opacity 0.25s ease;
}
.ppt-gen-backdrop-enter-from, .ppt-gen-backdrop-leave-to { opacity: 0; }
.ppt-gen-panel-enter-active, .ppt-gen-panel-leave-active {
  transition: opacity 0.25s ease, transform 0.3s cubic-bezier(0.22,1,0.36,1);
}
.ppt-gen-panel-enter-from, .ppt-gen-panel-leave-to {
  opacity: 0; transform: scale(0.94) translateY(20px);
}

/* dark */
html[data-theme="dark"] .ppt-gen-panel { background: #1a2535; }
html[data-theme="dark"] .ppt-gen-panel__header { border-color: #2a3546; }
html[data-theme="dark"] .ppt-gen-panel__input { border-color: #2a3546; }
html[data-theme="dark"] .filter-chip { background: #1a2535; border-color: #2a3546; color: #c8d6e5; }
html[data-theme="dark"] .filter-chip.active { background: #52b86f; border-color: #52b86f; }
html[data-theme="dark"] .theme-card { background: #1a2535; border-color: #2a3546; }
html[data-theme="dark"] .theme-card.selected { border-color: #52b86f; }
html[data-theme="dark"] .theme-card__check { background: #52b86f; }
html[data-theme="dark"] .btn-generate { background: #2f6b2f; }
html[data-theme="dark"] .ppt-gen-panel__field input,
html[data-theme="dark"] .ppt-gen-panel__field textarea { background: #0f1724; border-color: #2a3546; color: #e4e6ed; }

@media (max-width: 780px) {
  .ppt-gen-panel__body { grid-template-columns: 1fr; }
  .ppt-gen-panel__templates { max-height: 200px; }
  .ppt-gen-panel__input { border-left: none; border-top: 1px solid var(--color-border); }
}
</style>
