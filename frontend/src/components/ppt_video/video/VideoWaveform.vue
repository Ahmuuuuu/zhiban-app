<template>
  <div class="video-waveform" :class="{ 'is-active': active }" aria-hidden="true">
    <span
      v-for="bar in bars"
      :key="bar"
      class="video-waveform__bar"
      :style="{ '--bar': bar }"
    ></span>
  </div>
</template>

<script setup>
defineProps({
  active: {
    type: Boolean,
    default: false
  }
})

const bars = Array.from({ length: 28 }, (_, index) => index + 1)
</script>

<style scoped>
.video-waveform {
  position: absolute;
  left: 24px;
  right: auto;
  bottom: 22px;
  width: min(380px, calc(100% - 48px));
  height: 34px;
  display: flex;
  align-items: center;
  gap: 5px;
  pointer-events: none;
  opacity: 0.82;
}

.video-waveform__bar {
  width: 100%;
  max-width: 9px;
  height: calc(8px + (var(--bar) % 7) * 5px);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 0 18px rgba(31, 99, 214, 0.2);
  transform-origin: center bottom;
  animation: waveform-idle 2.8s ease-in-out infinite;
  animation-delay: calc(var(--bar) * -0.08s);
}

.video-waveform.is-active .video-waveform__bar {
  animation-name: waveform-active;
  animation-duration: 1.15s;
}

@keyframes waveform-idle {
  0%, 100% {
    transform: scaleY(0.62);
    opacity: 0.46;
  }

  50% {
    transform: scaleY(0.9);
    opacity: 0.78;
  }
}

@keyframes waveform-active {
  0%, 100% {
    transform: scaleY(0.48);
  }

  35% {
    transform: scaleY(1.18);
  }

  65% {
    transform: scaleY(0.76);
  }
}
</style>
