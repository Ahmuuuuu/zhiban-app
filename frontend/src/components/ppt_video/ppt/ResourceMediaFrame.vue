<template>
  <div class="resource-media-frame" :class="{ 'resource-media-frame--compact': compact }">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  compact: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.resource-media-frame {
  min-height: 0;
  height: 100%;
  display: flex;
  align-items: stretch;
  justify-content: center;
}

.resource-media-frame--compact {
  align-items: center;
}
</style>
