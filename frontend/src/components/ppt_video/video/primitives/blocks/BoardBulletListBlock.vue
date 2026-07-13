<template>
  <div class="board-bullet-list-block" :class="{ 'is-dense': dense }">
    <article
      v-for="(item, index) in items"
      :key="`${index}-${item}`"
      :style="{ '--delay': index }"
    >
      <ChalkNumber :value="index + 1" />
      <span v-html="renderedItems[index] || renderMath(item)"></span>
    </article>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { renderMath } from '../../../../../utils/renderMath'
import ChalkNumber from '../atoms/ChalkNumber.vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  renderedItems: {
    type: Array,
    default: () => []
  }
})

const dense = computed(() => props.items.length > 4)
</script>

<style scoped>
.board-bullet-list-block {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: clamp(8px, 1.1cqw, 12px);
  align-content: center;
  overflow: visible;
}

.board-bullet-list-block.is-dense {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 10px;
  align-content: start;
}

.board-bullet-list-block article {
  min-width: 0;
  min-height: 0;
  padding: 13px 15px;
  border: 1px solid var(--video-card-border);
  border-radius: 10px;
  background: var(--video-card-bg);
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 11px;
  align-items: start;
  overflow: visible;
  box-shadow: 0 16px 36px var(--video-shadow);
  animation: bullet-in 0.48s ease both;
  animation-delay: calc(var(--delay) * 0.08s + 0.1s);
}

.board-bullet-list-block.is-dense article {
  padding: 10px 12px;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 8px;
  --chalk-number-size: 30px;
}

.board-bullet-list-block span {
  min-width: 0;
  color: var(--video-muted);
  font-size: clamp(12px, 1.12cqw, 17px);
  line-height: 1.36;
  overflow-wrap: anywhere;
}

.board-bullet-list-block.is-dense span {
  font-size: var(--video-body-tight-size, clamp(11px, 0.82vw, 14px));
  line-height: 1.34;
}

@keyframes bullet-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
