<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import PetCharacter from "./PetCharacter.vue";
import PetPortrait from "./PetPortrait.vue";
import PetChat from "./PetChat.vue";

const PET_ASPECT_RATIO = 1;
type PetState =
  | "idle" | "waiting" | "thinking" | "greeting" | "loading" | "studying" | "failed" | "success";

const demoStates: PetState[] = [
  "idle", "waiting", "thinking", "greeting", "loading", "studying", "failed", "success",
];

const props = withDefaults(
  defineProps<{
    size?: number;
    floating?: boolean;
    side?: "left" | "right";
    bottom?: number;
    state?: PetState;
    autoPlayActions?: boolean;
  }>(),
  {
    size: 180,
    floating: false,
    side: "right",
    bottom: 28,
    state: "idle",
    autoPlayActions: false,
  },
);

const petRef = ref<HTMLElement | null>(null);
const dragPosition = ref<{ x: number; y: number } | null>(null);
const dragOffset = ref({ x: 0, y: 0 });
const pointerStart = ref({ x: 0, y: 0 });
const isDragging = ref(false);
const hasDragged = ref(false);
const suppressNextClick = ref(false);
const demoIndex = ref(0);
const chatOpen = ref(false);
const chatExpanded = ref(false);
const chatLoading = ref(false);
const noticeMessage = ref("");
const noticeVisible = ref(false);
let demoTimer: ReturnType<typeof window.setInterval> | undefined;
let noticeTimer: ReturnType<typeof window.setTimeout> | undefined;

const clampPosition = (x: number, y: number) => {
  const rect = petRef.value?.getBoundingClientRect();
  const width = rect?.width ?? props.size;
  const height = rect?.height ?? props.size * PET_ASPECT_RATIO;
  return {
    x: Math.max(8, Math.min(window.innerWidth - width - 8, x)),
    y: Math.max(8, Math.min(window.innerHeight - height - 8, y)),
  };
};

const startDrag = (event: PointerEvent) => {
  if (!props.floating || !petRef.value) return;
  event.preventDefault();
  const rect = petRef.value.getBoundingClientRect();
  isDragging.value = true;
  hasDragged.value = false;
  pointerStart.value = { x: event.clientX, y: event.clientY };
  dragOffset.value = { x: event.clientX - rect.left, y: event.clientY - rect.top };
  dragPosition.value = { x: rect.left, y: rect.top };
  petRef.value.setPointerCapture(event.pointerId);
};

const moveDrag = (event: PointerEvent) => {
  if (!isDragging.value) return;
  const movedDistance = Math.hypot(event.clientX - pointerStart.value.x, event.clientY - pointerStart.value.y);
  if (movedDistance > 6) hasDragged.value = true;
  dragPosition.value = clampPosition(event.clientX - dragOffset.value.x, event.clientY - dragOffset.value.y);
};

const stopDrag = (event: PointerEvent) => {
  if (!isDragging.value) return;
  isDragging.value = false;
  suppressNextClick.value = true;
  if (!hasDragged.value) toggleChat();
  if (petRef.value?.hasPointerCapture(event.pointerId)) petRef.value.releasePointerCapture(event.pointerId);
};

const handleResize = () => {
  if (!dragPosition.value) return;
  dragPosition.value = clampPosition(dragPosition.value.x, dragPosition.value.y);
};

const activeState = computed(() => {
  if (chatLoading.value) return "thinking";
  if (noticeVisible.value) return "greeting";
  if (chatOpen.value) return "greeting";
  return props.autoPlayActions ? demoStates[demoIndex.value] : props.state;
});

const petStyle = computed(() => ({
  "--pet-size": `${props.size}px`,
  "--pet-bottom": `${props.bottom}px`,
  ...(dragPosition.value
    ? { left: `${dragPosition.value.x}px`, top: `${dragPosition.value.y}px`, right: "auto", bottom: "auto" }
    : {}),
}));

const toggleChat = () => {
  const nextOpen = !chatOpen.value;
  chatOpen.value = nextOpen;
  if (!nextOpen) {
    chatExpanded.value = false;
    chatLoading.value = false;
  }
};

const handlePetClick = () => {
  if (suppressNextClick.value) { suppressNextClick.value = false; return; }
  toggleChat();
};

const handlePetKeydown = (event: KeyboardEvent) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  toggleChat();
};

const startActionDemo = () => {
  if (demoTimer) window.clearInterval(demoTimer);
  if (!props.autoPlayActions) return;
  demoTimer = window.setInterval(() => {
    demoIndex.value = (demoIndex.value + 1) % demoStates.length;
  }, 2600);
};

const showNotice = (message: string, duration = 5200) => {
  if (!message.trim()) return;
  if (noticeTimer) window.clearTimeout(noticeTimer);
  noticeMessage.value = message;
  noticeVisible.value = true;
  noticeTimer = window.setTimeout(() => {
    noticeVisible.value = false;
  }, duration);
};

const handlePetNotice = (event: Event) => {
  const detail = (event as CustomEvent<{ message?: string; duration?: number }>).detail || {};
  showNotice(detail.message || "", detail.duration);
};

onMounted(() => {
  window.addEventListener("resize", handleResize);
  window.addEventListener("zhiban-pet-notice", handlePetNotice as EventListener);
  startActionDemo();
  nextTick(() => {
    if (!props.floating || !petRef.value) return;
    const rect = petRef.value.getBoundingClientRect();
    dragPosition.value = clampPosition(rect.left, rect.top);
  });
});

watch(() => props.autoPlayActions, startActionDemo);

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  window.removeEventListener("zhiban-pet-notice", handlePetNotice as EventListener);
  if (demoTimer) window.clearInterval(demoTimer);
  if (noticeTimer) window.clearTimeout(noticeTimer);
});
</script>

<template>
  <div
    ref="petRef"
    class="study-pet"
    :class="{
      [`study-pet--${activeState}`]: true,
      'study-pet--floating': floating,
      'study-pet--left': floating && side === 'left',
      'study-pet--right': floating && side === 'right',
      'study-pet--dragging': isDragging,
      'study-pet--chat-expanded': chatExpanded,
      'study-pet--notice-visible': noticeVisible,
    }"
    :style="petStyle"
    @pointerdown="startDrag"
    @pointermove="moveDrag"
    @pointerup="stopDrag"
    @pointercancel="stopDrag"
    @click="handlePetClick"
    @keydown="handlePetKeydown"
    role="button"
    tabindex="0"
    aria-label="打开小知对话"
  >
    <PetCharacter :state="activeState" :dragging="isDragging" />
    <Transition name="pet-notice">
      <div v-if="noticeVisible" class="study-pet__notice" @click.stop>
        {{ noticeMessage }}
      </div>
    </Transition>
    <PetPortrait />
    <PetChat v-model="chatOpen" v-model:expanded="chatExpanded" v-model:loading="chatLoading" />
  </div>
</template>

<style scoped>
.study-pet {
  position: relative;
  width: var(--pet-size);
  aspect-ratio: 1;
  user-select: none;
  pointer-events: none;
  touch-action: none;
  filter: drop-shadow(0 18px 24px rgba(28, 112, 183, 0.2));
}

.study-pet--floating {
  position: fixed;
  right: 28px;
  bottom: var(--pet-bottom);
  z-index: 20;
  pointer-events: auto;
  cursor: grab;
}

.study-pet--left {
  left: 28px;
  right: auto;
}

.study-pet--right {
  right: 28px;
}

.study-pet--dragging {
  cursor: grabbing;
}

.study-pet--chat-expanded {
  filter: none;
  z-index: 1200;
}

.study-pet--notice-visible {
  z-index: 5200;
}

.study-pet__notice {
  position: absolute;
  right: calc(100% - 22px);
  bottom: 70%;
  z-index: 8;
  width: min(270px, calc(100vw - 48px));
  padding: 14px 16px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 18px 18px 6px 18px;
  background: rgba(255, 255, 255, 0.94);
  color: #163f8f;
  box-shadow: 0 16px 36px rgba(22, 63, 143, 0.16);
  font-size: 14px;
  font-weight: 850;
  line-height: 1.55;
  pointer-events: auto;
  backdrop-filter: blur(14px) saturate(145%);
  -webkit-backdrop-filter: blur(14px) saturate(145%);
}

.study-pet__notice::after {
  content: "";
  position: absolute;
  right: -8px;
  bottom: 18px;
  width: 16px;
  height: 16px;
  border-top: 1px solid rgba(22, 63, 143, 0.14);
  border-right: 1px solid rgba(22, 63, 143, 0.14);
  background: rgba(255, 255, 255, 0.94);
  transform: rotate(45deg);
}

.study-pet--left .study-pet__notice {
  right: auto;
  left: calc(100% - 22px);
  border-radius: 18px 18px 18px 6px;
}

.study-pet--left .study-pet__notice::after {
  right: auto;
  left: -8px;
  border: 0;
  border-bottom: 1px solid rgba(22, 63, 143, 0.14);
  border-left: 1px solid rgba(22, 63, 143, 0.14);
}

.pet-notice-enter-active,
.pet-notice-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.pet-notice-enter-from,
.pet-notice-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.96);
}

.study-pet:focus-visible {
  outline: 3px solid rgba(95, 143, 195, 0.32);
  outline-offset: 6px;
  border-radius: 28px;
}

@media (prefers-reduced-motion: reduce) {
  .study-pet,
  .study-pet * {
    animation: none;
  }
}
</style>
