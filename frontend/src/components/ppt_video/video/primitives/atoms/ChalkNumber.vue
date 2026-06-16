<template>
  <b class="chalk-number">{{ value }}</b>
</template>

<script setup>
defineProps({
  value: {
    type: [String, Number],
    required: true
  }
})
</script>

<style scoped>
.chalk-number {
  width: var(--chalk-number-size, 34px);
  height: var(--chalk-number-size, 34px);
  border-radius: 999px;
  background: var(--video-number-bg);
  color: var(--video-number-text);
  display: inline-grid;
  place-items: center;
  font-size: 14px;
  line-height: 1;
  font-weight: 900;
  flex: 0 0 auto;
}
</style>
