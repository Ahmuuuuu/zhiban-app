<template>
  <span class="chalk-tag"><slot></slot></span>
</template>

<style scoped>
.chalk-tag {
  width: fit-content;
  min-height: 28px;
  padding: 0 11px;
  border: 1px solid var(--video-card-border);
  border-radius: 999px;
  background: var(--video-chip-bg);
  color: var(--video-chip-text);
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}
</style>
