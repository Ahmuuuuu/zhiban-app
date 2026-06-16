<template>
  <div class="board-surface">
    <slot></slot>
  </div>
</template>

<style scoped>
.board-surface {
  position: relative;
  min-width: 0;
  min-height: 0;
  border: 1px solid color-mix(in srgb, var(--video-text) 18%, transparent);
  border-radius: 10px;
  background:
    linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    var(--video-card-bg);
  background-size: 26px 26px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    0 22px 54px var(--video-shadow);
  overflow: hidden;
}
</style>
