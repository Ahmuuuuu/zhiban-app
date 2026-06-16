<template>
  <div
    v-if="hasAssets"
    class="video-subject-assets"
    :class="[slotClass, densityClass]"
    aria-hidden="true"
  >
    <figure class="subject-asset-card">
      <img
        class="subject-image subject-image--main"
        :src="assets.subjectImage"
        alt=""
      />
      <img
        v-if="supportDecoration"
        class="subject-decoration subject-decoration--support"
        :src="supportDecoration"
        alt=""
      />
    </figure>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { selectCustomPptAssets } from '../../pptAssets'

const props = defineProps({
  slide: {
    type: Object,
    required: true
  },
  variant: {
    type: String,
    default: 'keypoint'
  },
  layoutSeed: {
    type: Number,
    default: 0
  }
})

const slideText = computed(() => [
  props.slide?.subject,
  props.slide?.discipline,
  props.slide?.chapterTitle,
  props.slide?.title,
  props.slide?.summary,
  ...(props.slide?.items || [])
].filter(Boolean).join('\n'))

const assetSlide = computed(() => ({
  ...props.slide,
  text: slideText.value,
  content: slideText.value
}))

const assets = computed(() => selectCustomPptAssets(assetSlide.value, props.slide?.index || 0))
const supportDecoration = computed(() => assets.value.pin || assets.value.clip || '')
const hasAssets = computed(() => Boolean(assets.value.subjectImage))
const itemCount = computed(() => Array.isArray(props.slide?.items) ? props.slide.items.length : 0)
const isDense = computed(() => itemCount.value > 4 || String(props.slide?.summary || '').length > 180)
const densityClass = computed(() => isDense.value ? 'is-dense' : '')

const slotClass = computed(() => {
  if (props.variant === 'intro') return 'slot-intro-relation'

  if (props.variant === 'formula') {
    return [
      'slot-formula-right',
      'slot-formula-left',
      'slot-formula-bottom',
      'slot-formula-left',
      'slot-formula-right',
      'slot-formula-right',
      'slot-formula-bottom'
    ][props.layoutSeed % 7]
  }

  if (props.variant === 'vocabulary') {
    return [
      'slot-scene-right',
      'slot-scene-left',
      'slot-scene-band',
      'slot-scene-left',
      'slot-scene-right',
      'slot-corner-right',
      'slot-scene-right'
    ][props.layoutSeed % 7]
  }

  return [
    'slot-visual-right',
    'slot-visual-left',
    'slot-visual-band',
    'slot-visual-bottom-left',
    'slot-visual-right',
    'slot-corner-right',
    'slot-visual-right'
  ][props.layoutSeed % 7]
})
</script>

<style scoped>
.video-subject-assets {
  position: absolute;
  inset: 0;
  z-index: 3;
  overflow: hidden;
  pointer-events: none;
}

.subject-asset-card {
  position: absolute;
  width: clamp(124px, 15vw, 230px);
  height: clamp(112px, 18vh, 210px);
  margin: 0;
  display: grid;
  place-items: center;
}

.subject-image,
.subject-decoration {
  position: absolute;
  display: block;
  user-select: none;
  -webkit-user-drag: none;
}

.subject-image--main {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  opacity: 0.92;
  filter: drop-shadow(0 18px 26px var(--video-shadow));
  animation: subject-float 5.4s ease-in-out infinite;
}

.subject-decoration--support {
  right: 2%;
  top: 5%;
  width: 34%;
  max-width: 72px;
  opacity: 0.78;
  transform: rotate(8deg);
  animation: support-pop 4.6s ease-in-out infinite;
}

.is-dense .subject-asset-card {
  width: clamp(92px, 11vw, 162px);
  height: clamp(82px, 14vh, 144px);
}

.is-dense .subject-decoration--support {
  display: none;
}

.slot-visual-right .subject-asset-card,
.slot-scene-right .subject-asset-card {
  right: clamp(78px, 6vw, 120px);
  top: clamp(178px, 31vh, 260px);
}

.slot-visual-left .subject-asset-card,
.slot-scene-left .subject-asset-card {
  left: clamp(78px, 6vw, 120px);
  top: clamp(178px, 31vh, 260px);
}

.slot-visual-band .subject-asset-card,
.slot-scene-band .subject-asset-card {
  right: clamp(92px, 8vw, 154px);
  top: clamp(236px, 39vh, 326px);
  width: clamp(104px, 12vw, 178px);
  height: clamp(88px, 13vh, 150px);
}

.slot-visual-bottom-left .subject-asset-card {
  left: clamp(96px, 8vw, 160px);
  bottom: clamp(132px, 16vh, 210px);
  width: clamp(100px, 12vw, 174px);
  height: clamp(88px, 13vh, 152px);
}

.slot-corner-right .subject-asset-card {
  right: clamp(70px, 6vw, 112px);
  bottom: clamp(128px, 14vh, 188px);
  width: clamp(92px, 10vw, 154px);
  height: clamp(80px, 12vh, 136px);
}

.slot-intro-relation .subject-asset-card {
  right: clamp(88px, 7vw, 144px);
  top: clamp(160px, 28vh, 236px);
  width: clamp(132px, 16vw, 250px);
  height: clamp(116px, 20vh, 224px);
}

.slot-formula-right .subject-asset-card {
  right: clamp(82px, 6vw, 130px);
  bottom: clamp(134px, 16vh, 220px);
  width: clamp(92px, 10vw, 158px);
  height: clamp(80px, 12vh, 138px);
}

.slot-formula-left .subject-asset-card {
  left: clamp(82px, 6vw, 130px);
  bottom: clamp(134px, 16vh, 220px);
  width: clamp(92px, 10vw, 158px);
  height: clamp(80px, 12vh, 138px);
}

.slot-formula-bottom .subject-asset-card {
  right: clamp(86px, 8vw, 150px);
  bottom: clamp(126px, 15vh, 198px);
  width: clamp(88px, 10vw, 150px);
  height: clamp(78px, 11vh, 132px);
}

@media (max-width: 980px) {
  .subject-asset-card {
    right: 26px !important;
    left: auto !important;
    top: auto !important;
    bottom: 112px !important;
    width: 86px !important;
    height: 78px !important;
  }
}

@keyframes subject-float {
  0%, 100% { transform: translateY(0) rotate(-1deg); }
  50% { transform: translateY(-14px) rotate(1.4deg); }
}

@keyframes support-pop {
  0%, 100% { transform: rotate(8deg) scale(0.96); }
  50% { transform: rotate(12deg) scale(1.04); }
}
</style>
