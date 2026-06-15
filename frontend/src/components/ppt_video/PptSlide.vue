<template>
  <article
    class="ppt-slide"
    :class="[
      `layout-${slide.layout || 'content_cards'}`,
      `theme-${slide.theme || 'academic_blue'}`,
      {
        editing,
        'custom-slide': styleSource === 'custom',
        'has-custom-subject': styleSource === 'custom' && Boolean(customAssets.subjectImage),
        'is-dense': slideTextLength > 420,
        'is-very-dense': slideTextLength > 800
      }
    ]"
    :style="slideVisualStyle(slide)"
  >
    <template v-if="styleSource === 'custom'">
      <img v-if="customAssets.tape" class="custom-decoration custom-decoration--tape" :src="customAssets.tape" alt="" />
      <img v-if="cornerDecoration" class="custom-decoration custom-decoration--corner" :src="cornerDecoration" alt="" />
      <img v-if="customAssets.highlight" class="custom-decoration custom-decoration--highlight" :src="customAssets.highlight" alt="" />
    </template>

    <div v-if="!editing" class="ppt-slide__kicker">
      <span>{{ layoutLabel(slide.layout) }}</span>
      <small>{{ visualLabel(slide.visual) }}</small>
    </div>
    <div
      v-if="!editing && styleSource === 'builtin' && slide.layout !== 'concept_visual'"
      class="ppt-slide__art"
      :style="visualImageStyle(slide)"
    ></div>

    <div class="ppt-slide__stage">
      <input
        v-if="editing"
        class="slide-title-input"
        :value="slide.title || title"
        @input="$emit('update-field', 'title', $event.target.value)"
      />
      <h3 v-else>{{ slide.title || title }}</h3>

      <textarea
        v-if="editing"
        class="slide-content-input"
        :value="slide.text"
        @input="$emit('update-field', 'text', $event.target.value)"
      ></textarea>

      <div v-else ref="contentRef" class="ppt-slide__content" @mouseup="handleTextSelection">
        <div v-if="slide.layout === 'concept_visual'" class="layout-grid layout-grid--visual">
          <div class="slide-rich-text">
            <template v-for="(segment, index) in slideSegments" :key="index">
              <mark
                v-if="segment.annotation"
                class="ppt-annotation-mark"
                :class="{ 'has-note': isNoteAnnotation(segment.annotation) }"
                :data-annotation-id="segment.annotation.id"
                :style="{ background: annotationBackground(segment.annotation) }"
                @click.stop="openAnnotation(segment.annotation)"
                v-html="renderMath(segment.text)"
              ></mark>
              <span v-else v-html="renderMath(segment.text)"></span>
            </template>
          </div>
          <aside v-if="styleSource === 'builtin'" class="visual-panel">
            <div class="visual-panel__image" :style="visualImageStyle(slide)"></div>
            <strong>{{ slide.visual?.query || slide.title }}</strong>
            <p>{{ slide.visual?.caption || firstBlockText }}</p>
          </aside>
          <aside v-else-if="customAssets.subjectImage" class="custom-subject-panel">
            <img :src="customAssets.subjectImage" :alt="customAssets.subject || slide.title" />
          </aside>
        </div>

        <PptSlideProcess
          v-else-if="slide.layout === 'process_steps'"
          :blocks="slideBlocks"
          :display-block-text="displayBlockText"
        />

        <PptSlideComparison
          v-else-if="slide.layout === 'comparison'"
          :blocks="slideBlocks"
          :display-block-text="displayBlockText"
        />

        <PptSlideFormula
          v-else-if="slide.layout === 'formula_focus'"
          :formula-text="formulaText"
          :formula-blocks="formulaBlocks"
          :display-block-text="displayBlockText"
        />

        <PptSlideContentCards
          v-else-if="slide.layout === 'content_cards'"
          :blocks="slideBlocks"
          :display-block-text="displayBlockText"
        />

        <template v-else>
          <template v-for="(segment, index) in slideSegments" :key="index">
            <mark
              v-if="segment.annotation"
              class="ppt-annotation-mark"
              :class="{ 'has-note': isNoteAnnotation(segment.annotation) }"
              :data-annotation-id="segment.annotation.id"
              :style="{ background: annotationBackground(segment.annotation) }"
              @click.stop="openAnnotation(segment.annotation)"
              v-html="renderMath(segment.text)"
            ></mark>
            <span v-else v-html="renderMath(segment.text)"></span>
          </template>
        </template>
      </div>
    </div>

    <img
      v-if="styleSource === 'custom' && slide.layout !== 'concept_visual' && customAssets.subjectImage"
      class="custom-subject-image"
      :src="customAssets.subjectImage"
      :alt="customAssets.subject || slide.title"
    />

    <aside class="ppt-slide__notes">
      <span>讲稿</span>
      <textarea
        v-if="editing"
        :value="slide.notes"
        @input="$emit('update-field', 'notes', $event.target.value)"
      ></textarea>
      <p v-else>{{ slide.notes || '暂无讲稿' }}</p>
    </aside>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import PptSlideComparison from './PptSlideComparison.vue'
import PptSlideContentCards from './PptSlideContentCards.vue'
import PptSlideFormula from './PptSlideFormula.vue'
import PptSlideProcess from './PptSlideProcess.vue'
import { selectCustomPptAssets } from './pptAssets'
import { renderMath } from '../../utils/renderMath'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  },
  title: {
    type: String,
    default: ''
  },
  editing: {
    type: Boolean,
    default: false
  },
  annotatable: {
    type: Boolean,
    default: false
  },
  annotationTool: {
    type: String,
    default: ''
  },
  activeHighlightColor: {
    type: String,
    default: '#ffe159'
  },
  styleSource: {
    type: String,
    default: 'builtin'
  },
  annotations: {
    type: Array,
    default: () => []
  },
  slideIndex: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update-field', 'select-text', 'open-annotation'])
const contentRef = ref(null)
const customAssets = computed(() => selectCustomPptAssets(props.slide, props.slideIndex))
const cornerDecoration = computed(() => customAssets.value.pin || customAssets.value.clip || customAssets.value.note || '')

const layoutLabels = {
  title_cover: '封面',
  concept_visual: '图文讲解',
  process_steps: '流程步骤',
  comparison: '对比分析',
  formula_focus: '公式推导',
  content_cards: '重点卡片'
}

const themePalettes = {
  academic_blue: ['#163f8f', '#5f8fc3', '#c9dce9', '#fafafa'],
  aurora: ['#115e59', '#0f766e', '#99f6e4', '#f0fdfa'],
  coral: ['#9f1239', '#fb7185', '#fecdd3', '#fff1f2'],
  violet: ['#5b21b6', '#8b5cf6', '#ddd6fe', '#f5f3ff'],
  science_green: ['#166534', '#22c55e', '#bbf7d0', '#f0fdf4'],
  warm_case: ['#92400e', '#f97316', '#fed7aa', '#fff7ed'],
  graphite: ['#1f2937', '#64748b', '#cbd5e1', '#f8fafc'],
  sunlit: ['#854d0e', '#f59e0b', '#84cc16', '#fffbeb']
}

const layoutLabel = layout => layoutLabels[layout] || '内容讲解'

const visualLabel = visual => {
  const type = visual?.type || 'diagram'
  const labels = {
    timeline: '时间线',
    comparison: '对比图',
    diagram: '结构图',
    formula: '公式图',
    experiment: '实验图',
    map: '地图',
    chart: '图表'
  }
  return labels[type] || '视觉辅助'
}

const visualGlyph = visual => {
  const glyphs = {
    timeline: '1-2-3',
    comparison: 'A/B',
    formula: 'f(x)',
    experiment: 'LAB',
    map: 'MAP',
    chart: 'DATA',
    diagram: 'IDEA'
  }
  return glyphs[visual?.type] || glyphs.diagram
}

const slidePalette = slide => {
  if (Array.isArray(slide?.palette) && slide.palette.length >= 4) return slide.palette
  return themePalettes[slide?.theme] || themePalettes.academic_blue
}

const svgUrl = svg => `url("data:image/svg+xml,${encodeURIComponent(svg)}")`

const cleanDisplayText = value => String(value || '')
  .replace(/<!--[\s\S]*?-->/g, ' ')
  .replace(/<\/?[^>\n]+>/g, ' ')
  .replace(/<[^>\n]*$/g, ' ')
  .replace(/```[\s\S]*?```/g, ' ')
  .replace(/^#{1,6}\s+/gm, '')
  .replace(/^[\-*+]\s+/gm, '')
  .replace(/\*\*(.*?)\*\*/g, '$1')
  .replace(/\n{3,}/g, '\n\n')
  .trim()

const compactDisplayText = (value, limit = 180) => {
  const text = cleanDisplayText(value).replace(/\s+/g, ' ').trim()
  return text.length > limit ? `${text.slice(0, limit - 1)}...` : text
}

const displayBlockText = (value, limit = 150) => compactDisplayText(value, limit)

const visualSvgData = slide => {
  const [primary, secondary, accent, paper] = slidePalette(slide)
  const type = slide?.visual?.type || 'diagram'
  const label = visualGlyph(slide?.visual)
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 360"><defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="${paper}"/><stop offset="1" stop-color="${accent}"/></linearGradient></defs><rect width="520" height="360" rx="34" fill="url(#g)"/><circle cx="404" cy="86" r="58" fill="${secondary}" opacity=".22"/><circle cx="105" cy="270" r="78" fill="${primary}" opacity=".1"/><path d="M85 240C158 124 253 110 337 177c43 34 78 46 118 31" fill="none" stroke="${primary}" stroke-width="16" stroke-linecap="round" opacity=".72"/><rect x="74" y="76" width="144" height="84" rx="24" fill="${primary}" opacity=".9"/><rect x="244" y="210" width="196" height="74" rx="22" fill="${secondary}" opacity=".86"/><text x="146" y="129" text-anchor="middle" font-family="Arial" font-size="34" font-weight="800" fill="#fff">${type === 'formula' ? 'Σ' : label}</text><text x="342" y="257" text-anchor="middle" font-family="Arial" font-size="22" font-weight="800" fill="#fff">${compactDisplayText(slide?.visual?.caption || slide?.title || 'Key Point', 16)}</text></svg>`
}

const visualImageStyle = slide => ({
  backgroundImage: svgUrl(visualSvgData(slide))
})

const slideVisualStyle = slide => {
  const [primary, secondary, accent, paper] = slidePalette(slide)
  if (props.styleSource === 'custom') {
    const backgroundUrl = slide?.backgroundUrl || slide?.background_url || slide?.assetUrl || slide?.asset_url || customAssets.value.background || ''
    return {
      '--slide-primary': primary,
      '--slide-secondary': secondary,
      '--slide-accent': accent,
      '--slide-paper': paper,
      backgroundColor: paper,
      backgroundImage: backgroundUrl ? `url("${backgroundUrl}")` : 'none',
      backgroundSize: 'cover',
      backgroundPosition: 'center'
    }
  }

  const bg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720"><defs><linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop stop-color="${paper}"/><stop offset=".56" stop-color="${paper}"/><stop offset="1" stop-color="${accent}" stop-opacity=".42"/></linearGradient></defs><rect width="1200" height="720" fill="url(#bg)"/><path d="M0 0H1200V95C930 136 716 46 457 92 269 125 123 174 0 136Z" fill="${primary}" opacity=".94"/><path d="M810 0c156 44 262 132 390 92V0Z" fill="${secondary}" opacity=".9"/><circle cx="1030" cy="154" r="118" fill="${accent}" opacity=".24"/><circle cx="930" cy="210" r="76" fill="${secondary}" opacity=".18"/></svg>`
  return {
    '--slide-primary': primary,
    '--slide-secondary': secondary,
    '--slide-accent': accent,
    '--slide-paper': paper,
    backgroundImage: svgUrl(bg)
  }
}

const normalizeBlocks = slide => {
  const blocks = Array.isArray(slide?.blocks) ? slide.blocks : []
  if (blocks.length) {
    return blocks
      .map(block => ({
        ...block,
        text: cleanDisplayText(block?.text || block?.content)
      }))
      .filter(block => block.text)
  }
  return cleanDisplayText(slide?.text || '')
    .split(/\n+/)
    .map(text => ({ type: 'key_point', text: cleanDisplayText(text) }))
    .filter(block => block.text)
}

const slideBlocks = computed(() => normalizeBlocks(props.slide))
const firstBlockText = computed(() => slideBlocks.value[0]?.text || '')
const formulaText = computed(() => slideBlocks.value.find(block => /=|\$|\\sum|\\frac|\^|_/.test(block.text))?.text || firstBlockText.value)
const formulaBlocks = computed(() => slideBlocks.value.filter(block => block.text !== formulaText.value).slice(0, 5))

const slideTextLength = computed(() => {
  const slide = props.slide || {}
  return String(`${slide.title || ''}\n${slide.text || ''}\n${slide.notes || ''}`).length
})

const getAnnotationColor = annotation => annotation?.position?.color || '#ffe159'
const isNoteAnnotation = annotation => annotation?.position?.tool === 'note' || Boolean(annotation?.note || annotation?.note_text)
const annotationBackground = annotation => {
  if (isNoteAnnotation(annotation)) return 'rgba(237, 249, 252, 0.66)'
  const color = getAnnotationColor(annotation)
  return `linear-gradient(transparent 18%, ${color} 18%, ${color} 88%, transparent 88%)`
}

const slideSegments = computed(() => {
  const text = cleanDisplayText(props.slide.text || '')
  const result = []
  let cursor = 0

  props.annotations.forEach(annotation => {
    const start = Number(annotation.position?.start)
    const end = Number(annotation.position?.end)
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return
    if (start > cursor) result.push({ text: text.slice(cursor, start) })
    result.push({ text: text.slice(start, end), annotation })
    cursor = end
  })

  if (cursor < text.length) result.push({ text: text.slice(cursor) })
  return result.length ? result : [{ text }]
})

const getOffset = (container, targetNode, targetOffset) => {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT)
  let offset = 0
  let node = walker.nextNode()
  while (node) {
    if (node === targetNode) return offset + targetOffset
    offset += node.textContent?.length || 0
    node = walker.nextNode()
  }
  return offset
}

const handleTextSelection = () => {
  if (!props.annotatable || !props.annotationTool || props.editing || !contentRef.value) return
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return

  const range = selection.getRangeAt(0)
  if (!contentRef.value.contains(range.commonAncestorContainer)) return

  const selectedText = selection.toString().trim()
  if (!selectedText) return

  const start = getOffset(contentRef.value, range.startContainer, range.startOffset)
  const end = getOffset(contentRef.value, range.endContainer, range.endOffset)
  const rect = range.getBoundingClientRect()

  emit('select-text', {
    selectedText,
    rect,
    position: {
      kind: 'ppt',
      slideIndex: props.slideIndex,
      start,
      end,
      color: props.activeHighlightColor,
      tool: props.annotationTool
    }
  })
}

const openAnnotation = annotation => {
  const el = contentRef.value?.querySelector(`[data-annotation-id="${CSS.escape(String(annotation.id))}"]`)
  emit('open-annotation', {
    annotation,
    rect: el?.getBoundingClientRect()
  })
}
</script>

<style scoped>
.custom-decoration,
.custom-subject-image,
.custom-subject-panel {
  pointer-events: none;
  user-select: none;
}

.ppt-slide.custom-slide::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  background: rgba(255, 255, 255, 0.18);
  pointer-events: none;
}

.custom-decoration {
  position: absolute;
  z-index: 1;
  object-fit: contain;
}

.custom-decoration--tape {
  top: clamp(30px, 4.2vh, 48px);
  left: 50%;
  width: clamp(92px, 9vw, 138px);
  transform: translateX(-50%) rotate(-3deg);
  opacity: 0.78;
}

.custom-decoration--corner {
  top: clamp(58px, 7vh, 86px);
  right: clamp(48px, 6vw, 78px);
  width: clamp(28px, 3.4vw, 48px);
  transform: rotate(7deg);
  opacity: 0.78;
}

.custom-decoration--highlight {
  left: clamp(78px, 9vw, 128px);
  top: clamp(146px, 18vh, 182px);
  width: min(32%, 320px);
  transform: rotate(-1deg);
  opacity: 0.22;
  z-index: 0;
}

.custom-subject-image {
  position: absolute;
  right: clamp(42px, 5vw, 74px);
  bottom: clamp(72px, 9vh, 112px);
  width: clamp(96px, 13vw, 172px);
  max-height: 26%;
  object-fit: contain;
  z-index: 1;
  opacity: 0.68;
  filter: drop-shadow(0 12px 20px rgba(22, 63, 143, 0.12));
}

.ppt-slide.custom-slide .ppt-slide__stage,
.ppt-slide.custom-slide .ppt-slide__notes,
.ppt-slide.custom-slide .ppt-slide__kicker {
  z-index: 2;
}

.ppt-slide.custom-slide.has-custom-subject:not(.layout-concept_visual) .ppt-slide__content {
  width: min(84%, 940px);
}

.custom-subject-panel {
  min-height: 0;
  display: grid;
  place-items: center;
  padding: clamp(8px, 1.4vw, 18px);
}

.custom-subject-panel img {
  max-width: min(100%, 260px);
  max-height: 82%;
  object-fit: contain;
  opacity: 0.88;
  filter: drop-shadow(0 12px 22px rgba(22, 63, 143, 0.14));
}

.ppt-slide.layout-concept_visual .custom-subject-panel {
  padding: clamp(8px, 1.5vw, 18px);
}

.ppt-slide.layout-concept_visual .custom-decoration--highlight {
  display: none;
}

.ppt-slide.is-dense .custom-subject-image,
.ppt-slide.is-very-dense .custom-subject-image {
  opacity: 0.32;
  width: clamp(78px, 10vw, 132px);
}
</style>
