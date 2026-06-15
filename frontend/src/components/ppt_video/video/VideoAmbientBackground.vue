<template>
  <div class="video-ambient" :class="{ 'is-active': active }" :style="backgroundStyle" aria-hidden="true">
    <span class="video-ambient__shade"></span>
    <span class="video-ambient__scan"></span>
    <span class="video-ambient__ring video-ambient__ring--one"></span>
    <span class="video-ambient__ring video-ambient__ring--two"></span>
    <span class="video-ambient__grid"></span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  backgroundUrl: {
    type: String,
    default: ''
  },
  active: {
    type: Boolean,
    default: false
  }
})

const backgroundStyle = computed(() => ({
  backgroundImage: props.backgroundUrl
    ? `url("${props.backgroundUrl}")`
    : 'linear-gradient(135deg, #10213d, #1f6f8f 48%, #7bc6d8)'
}))
</script>

<style scoped>
.video-ambient {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background-position: center;
  background-size: cover;
  transform: scale(1.02);
}

.video-ambient::before {
  content: "";
  position: absolute;
  inset: -8%;
  background: inherit;
  filter: saturate(1.08) contrast(1.04);
  animation: ambient-drift 18s ease-in-out infinite alternate;
}

.video-ambient.is-active::before {
  animation-duration: 12s;
}

.video-ambient__shade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(6, 18, 32, 0.72), rgba(6, 18, 32, 0.24) 48%, rgba(6, 18, 32, 0.64)),
    radial-gradient(circle at 28% 24%, rgba(255, 255, 255, 0.18), transparent 34%),
    radial-gradient(circle at 78% 78%, rgba(111, 204, 221, 0.2), transparent 36%);
}

.video-ambient__scan {
  position: absolute;
  inset: 0;
  background: linear-gradient(115deg, transparent 22%, rgba(255, 255, 255, 0.14) 44%, transparent 62%);
  transform: translateX(-55%);
  animation: ambient-scan 7s ease-in-out infinite;
  opacity: 0.48;
}

.video-ambient.is-active .video-ambient__scan {
  opacity: 0.34;
  animation-duration: 5.8s;
}

.video-ambient__ring {
  position: absolute;
  width: 220px;
  height: 220px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  box-shadow: 0 0 34px rgba(112, 209, 225, 0.12);
  animation: ambient-pulse 5s ease-in-out infinite;
}

.video-ambient__ring--one {
  right: 9%;
  top: 12%;
}

.video-ambient__ring--two {
  left: 12%;
  bottom: 9%;
  width: 150px;
  height: 150px;
  animation-delay: -2s;
}

.video-ambient__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(90deg, transparent, #000 22%, #000 78%, transparent);
  opacity: 0.32;
}

.video-ambient.is-active .video-ambient__grid {
  opacity: 0.2;
}

@keyframes ambient-drift {
  from {
    transform: translate3d(-1.5%, -1%, 0) scale(1.04);
  }

  to {
    transform: translate3d(1.5%, 1%, 0) scale(1.08);
  }
}

@keyframes ambient-scan {
  0%, 24% {
    transform: translateX(-62%);
  }

  70%, 100% {
    transform: translateX(62%);
  }
}

@keyframes ambient-pulse {
  0%, 100% {
    opacity: 0.32;
    transform: scale(0.94);
  }

  50% {
    opacity: 0.72;
    transform: scale(1.05);
  }
}
</style>
