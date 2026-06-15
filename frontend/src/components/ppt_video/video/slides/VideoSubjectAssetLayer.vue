<template>
  <div
    v-if="hasAssets"
    class="video-subject-assets"
    :class="[placementClass, densityClass, `subject-${subjectClass}`]"
    aria-hidden="true"
  >
    <img
      v-if="assets.subjectImage"
      class="subject-image subject-image--main"
      :src="assets.subjectImage"
      alt=""
    />
    <img
      v-if="assets.note"
      class="subject-decoration subject-decoration--note"
      :src="assets.note"
      alt=""
    />
    <img
      v-if="assets.tape"
      class="subject-decoration subject-decoration--tape"
      :src="assets.tape"
      alt=""
    />
    <img
      v-if="assets.highlight"
      class="subject-decoration subject-decoration--highlight"
      :src="assets.highlight"
      alt=""
    />
    <img
      v-if="cornerDecoration"
      class="subject-decoration subject-decoration--corner"
      :src="cornerDecoration"
      alt=""
    />
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

const assetSlide = computed(() => ({
  ...props.slide,
  text: [
    props.slide?.subject,
    props.slide?.summary,
    props.slide?.chapterTitle,
    ...(props.slide?.items || [])
  ].filter(Boolean).join('\n'),
  content: [
    props.slide?.subject,
    props.slide?.summary,
    ...(props.slide?.items || [])
  ].filter(Boolean).join('\n')
}))

const assets = computed(() => selectCustomPptAssets(assetSlide.value, props.slide?.index || 0))
const cornerDecoration = computed(() => assets.value.pin || assets.value.clip || '')
const hasAssets = computed(() => Boolean(assets.value.subjectImage || assets.value.note || assets.value.tape || assets.value.highlight || cornerDecoration.value))
const subjectClass = computed(() => String(assets.value.subject || 'general').replace(/\s+/g, '-'))
const itemCount = computed(() => Array.isArray(props.slide?.items) ? props.slide.items.length : 0)
const isDense = computed(() => itemCount.value > 4 || String(props.slide?.summary || '').length > 180)
const densityClass = computed(() => isDense.value ? 'is-dense' : '')

const placementClass = computed(() => {
  if (isDense.value) return 'placement-watermark'
  if (props.variant === 'intro') return 'placement-intro'
  if (props.variant === 'formula') {
    return ['placement-right', 'placement-left', 'placement-bottom', 'placement-right', 'placement-left', 'placement-watermark', 'placement-bottom'][props.layoutSeed % 7]
  }
  if (props.variant === 'vocabulary') {
    return ['placement-right', 'placement-left', 'placement-top-right', 'placement-left', 'placement-right', 'placement-watermark', 'placement-bottom'][props.layoutSeed % 7]
  }
  return ['placement-right', 'placement-left', 'placement-top-right', 'placement-left', 'placement-bottom', 'placement-watermark', 'placement-right'][props.layoutSeed % 7]
})
</script>

<style scoped>
.video-subject-assets {
  position: absolute;
  inset: 0;
  z-index: 1;
  overflow: hidden;
  pointer-events: none;
}

.subject-image,
.subject-decoration {
  position: absolute;
  display: block;
  user-select: none;
  -webkit-user-drag: none;
}

.subject-image--main {
  width: clamp(112px, 15vw, 230px);
  max-height: 30vh;
  object-fit: contain;
  opacity: 0.74;
  filter: drop-shadow(0 18px 26px var(--video-shadow));
  animation: subject-float 5.4s ease-in-out infinite;
}

.placement-right .subject-image--main {
  right: clamp(34px, 5vw, 86px);
  top: clamp(180px, 32vh, 260px);
}

.placement-left .subject-image--main {
  left: clamp(34px, 5vw, 86px);
  top: clamp(180px, 32vh, 260px);
}

.placement-top-right .subject-image--main {
  right: clamp(44px, 7vw, 118px);
  top: clamp(92px, 15vh, 150px);
  opacity: 0.66;
}

.placement-bottom .subject-image--main {
  right: clamp(52px, 8vw, 140px);
  bottom: clamp(112px, 14vh, 172px);
  width: clamp(104px, 13vw, 200px);
}

.placement-intro .subject-image--main {
  right: clamp(46px, 6vw, 108px);
  bottom: clamp(118px, 14vh, 172px);
  width: clamp(140px, 20vw, 300px);
  opacity: 0.72;
}

.placement-watermark .subject-image--main {
  left: 50%;
  top: 50%;
  width: clamp(190px, 28vw, 420px);
  max-height: 42vh;
  opacity: 0.16;
  transform: translate(-50%, -50%);
  filter: grayscale(0.08) drop-shadow(0 20px 34px var(--video-shadow));
  animation: watermark-float 7s ease-in-out infinite;
}

.is-dense .subject-decoration--note,
.is-dense .subject-decoration--tape,
.is-dense .subject-decoration--corner {
  opacity: 0.18;
}

.subject-decoration--note {
  left: clamp(24px, 4vw, 66px);
  top: clamp(82px, 13vh, 126px);
  width: clamp(72px, 8vw, 124px);
  opacity: 0.34;
  transform: rotate(-7deg);
  animation: note-drift 6.2s ease-in-out infinite;
}

.placement-left .subject-decoration--note,
.placement-intro .subject-decoration--note {
  left: auto;
  right: clamp(28px, 5vw, 74px);
}

.subject-decoration--tape {
  right: clamp(96px, 18vw, 270px);
  top: clamp(70px, 12vh, 116px);
  width: clamp(86px, 11vw, 168px);
  opacity: 0.36;
  transform: rotate(5deg);
  animation: tape-sway 4.8s ease-in-out infinite;
}

.placement-right .subject-decoration--tape,
.placement-top-right .subject-decoration--tape {
  right: clamp(34px, 6vw, 86px);
}

.placement-left .subject-decoration--tape {
  left: clamp(38px, 6vw, 90px);
  right: auto;
}

.subject-decoration--highlight {
  left: clamp(80px, 12vw, 210px);
  bottom: clamp(104px, 13vh, 166px);
  width: clamp(150px, 22vw, 330px);
  opacity: 0.26;
  transform: rotate(-2deg);
  mix-blend-mode: multiply;
  animation: highlight-scan 3.8s ease-in-out infinite;
}

.placement-left .subject-decoration--highlight {
  left: auto;
  right: clamp(78px, 12vw, 210px);
}

.placement-watermark .subject-decoration--highlight {
  left: 50%;
  bottom: clamp(96px, 12vh, 150px);
  transform: translateX(-50%) rotate(-2deg);
}

.subject-decoration--corner {
  right: clamp(38px, 6vw, 92px);
  top: clamp(82px, 13vh, 138px);
  width: clamp(38px, 4.6vw, 70px);
  opacity: 0.54;
  animation: corner-pop 4.6s ease-in-out infinite;
}

.placement-left .subject-decoration--corner {
  left: clamp(38px, 6vw, 92px);
  right: auto;
}

.subject-数学 .subject-image--main,
.subject-物理 .subject-image--main,
.subject-化学 .subject-image--main {
  opacity: 0.82;
}

.subject-英语 .subject-image--main,
.subject-生物 .subject-image--main {
  width: clamp(130px, 18vw, 280px);
}

.placement-watermark.subject-数学 .subject-image--main,
.placement-watermark.subject-物理 .subject-image--main,
.placement-watermark.subject-化学 .subject-image--main,
.placement-watermark.subject-英语 .subject-image--main,
.placement-watermark.subject-生物 .subject-image--main {
  opacity: 0.14;
}

@keyframes subject-float {
  0%, 100% { transform: translateY(0) rotate(-1deg); }
  50% { transform: translateY(-14px) rotate(1.4deg); }
}

@keyframes watermark-float {
  0%, 100% { transform: translate(-50%, -50%) scale(1) rotate(-1deg); }
  50% { transform: translate(-50%, calc(-50% - 12px)) scale(1.02) rotate(1deg); }
}

@keyframes note-drift {
  0%, 100% { transform: rotate(-7deg) translateY(0); }
  50% { transform: rotate(-4deg) translateY(-10px); }
}

@keyframes tape-sway {
  0%, 100% { transform: rotate(5deg) translateX(0); }
  50% { transform: rotate(8deg) translateX(8px); }
}

@keyframes highlight-scan {
  0%, 100% { opacity: 0.16; transform: rotate(-2deg) scaleX(0.92); }
  50% { opacity: 0.34; transform: rotate(-2deg) scaleX(1); }
}

@keyframes corner-pop {
  0%, 100% { transform: scale(0.96) rotate(0); }
  50% { transform: scale(1.05) rotate(5deg); }
}
</style>
