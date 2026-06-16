<template>
  <button
    class="video-poster"
    type="button"
    :style="posterStyle"
    :aria-label="title ? `播放 ${title}` : '播放视频'"
    @click="$emit('play')"
  >
    <span class="video-poster__veil"></span>
    <span class="video-poster__grain"></span>

    <span class="video-poster__content">
      <span class="video-poster__kicker">AI 课程视频</span>
      <span class="video-poster__title">{{ title || '课程视频' }}</span>
      <span v-if="summary" class="video-poster__summary">{{ summary }}</span>
    </span>

    <span class="video-poster__play">
      <span class="video-poster__play-halo"></span>
      <img
        v-if="playIconUrl"
        class="video-poster__play-image"
        :src="playIconUrl"
        alt=""
      >
      <Play v-else :size="34" fill="currentColor" />
    </span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { Play } from 'lucide-vue-next'

const sharedIconModules = import.meta.glob('../../../assets/ppt_video/shared/icons/*.{png,jpg,jpeg,webp,svg}', {
  eager: true,
  import: 'default'
})

const videoOverlayModules = import.meta.glob('../../../assets/ppt_video/video/overlays/*.{png,jpg,jpeg,webp,svg}', {
  eager: true,
  import: 'default'
})

const playIconUrl = Object.entries({
  ...sharedIconModules,
  ...videoOverlayModules
}).find(([path]) => /(?:play|播放)/i.test(path))?.[1] || ''

const props = defineProps({
  posterUrl: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: ''
  },
  summary: {
    type: String,
    default: ''
  }
})

defineEmits(['play'])

const posterStyle = computed(() => ({
  backgroundImage: props.posterUrl
    ? `url("${props.posterUrl}")`
    : 'linear-gradient(135deg, #10213d, #225b8f 48%, #7bc6d8)'
}))
</script>

<style scoped>
.video-poster {
  position: absolute;
  z-index: 2;
  inset: 0;
  border: 0;
  padding: 0;
  border-radius: 8px;
  overflow: hidden;
  background-position: center;
  background-size: cover;
  color: #ffffff;
  cursor: pointer;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 148px;
  align-items: end;
  gap: 24px;
  text-align: left;
}

.video-poster__veil,
.video-poster__grain {
  position: absolute;
  inset: 0;
}

.video-poster__veil {
  background:
    linear-gradient(90deg, rgba(8, 21, 38, 0.78), rgba(8, 21, 38, 0.34) 52%, rgba(8, 21, 38, 0.7)),
    radial-gradient(circle at 64% 42%, rgba(255, 255, 255, 0.2), transparent 35%);
}

.video-poster__grain {
  opacity: 0.2;
  background-image:
    linear-gradient(90deg, rgba(255, 255, 255, 0.12) 1px, transparent 1px),
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(180deg, transparent, #000 26%, #000 92%);
}

.video-poster__content {
  position: relative;
  z-index: 1;
  min-width: 0;
  padding: 72px 0 34px 34px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.video-poster__kicker {
  width: fit-content;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  display: inline-flex;
  align-items: center;
  color: rgba(215, 242, 246, 0.92);
  font-size: 12px;
  font-weight: 900;
  backdrop-filter: blur(10px);
}

.video-poster__title {
  max-width: 720px;
  font-size: clamp(24px, 3.4vw, 44px);
  font-weight: 900;
  line-height: 1.12;
  text-shadow: 0 2px 16px rgba(0, 0, 0, 0.38);
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.video-poster__summary {
  max-width: 620px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  line-height: 1.7;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.video-poster__play {
  position: relative;
  z-index: 1;
  width: 92px;
  height: 92px;
  margin: 0 34px 42px 0;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(250, 250, 250, 0.94);
  color: #163f8f;
  box-shadow: 0 20px 48px rgba(8, 21, 38, 0.32);
}

.video-poster__play-halo {
  position: absolute;
  inset: -12px;
  border-radius: inherit;
  border: 1px solid rgba(255, 255, 255, 0.36);
  animation: poster-halo 1.9s ease-in-out infinite;
}

.video-poster__play-image {
  width: 52%;
  height: 52%;
  object-fit: contain;
  display: block;
}

.video-poster:hover .video-poster__play {
  transform: scale(1.04);
}

@keyframes poster-halo {
  0%, 100% {
    opacity: 0.72;
    transform: scale(0.92);
  }

  50% {
    opacity: 0.18;
    transform: scale(1.14);
  }
}

@media (max-width: 720px) {
  .video-poster {
    grid-template-columns: 1fr;
    align-items: end;
  }

  .video-poster__content {
    padding: 70px 22px 112px;
  }

  .video-poster__play {
    position: absolute;
    right: 22px;
    bottom: 24px;
    width: 72px;
    height: 72px;
    margin: 0;
  }
}
</style>
