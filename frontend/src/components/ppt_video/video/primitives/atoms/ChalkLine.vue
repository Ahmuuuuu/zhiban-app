<template>
  <span class="chalk-line" :class="`chalk-line--${tone}`"></span>
</template>

<script setup>
defineProps({
  tone: {
    type: String,
    default: 'accent'
  }
})
</script>

<style scoped>
.chalk-line {
  display: block;
  width: min(420px, 72%);
  height: 4px;
  border-radius: 999px;
  background: var(--video-line);
  opacity: 0.82;
  box-shadow: 0 0 14px color-mix(in srgb, var(--video-line) 36%, transparent);
}

.chalk-line--warm {
  background: var(--video-warm);
}

.chalk-line--soft {
  background: var(--video-soft);
}
</style>
