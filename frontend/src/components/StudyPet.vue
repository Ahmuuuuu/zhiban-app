<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
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

const router = useRouter();
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
const petModalVisible = ref(false);
const petModal = reactive({
  title: "",
  message: "",
  primaryText: "我知道了",
  secondaryText: "",
  primaryAction: "",
});
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

const showPetModal = (detail: {
  title?: string;
  message?: string;
  primaryText?: string;
  secondaryText?: string;
  primaryAction?: string;
}) => {
  const message = String(detail.message || "").trim();
  if (!message) return;
  petModal.title = detail.title || "小知提醒";
  petModal.message = message;
  petModal.primaryText = detail.primaryText || "我知道了";
  petModal.secondaryText = detail.secondaryText || "";
  petModal.primaryAction = detail.primaryAction || "";
  petModalVisible.value = true;
};

const handlePetModal = (event: Event) => {
  const detail = (event as CustomEvent<{
    title?: string;
    message?: string;
    primaryText?: string;
    secondaryText?: string;
    primaryAction?: string;
  }>).detail || {};
  showPetModal(detail);
};

const closePetModal = () => {
  petModalVisible.value = false;
};

const runPetModalAction = async () => {
  const action = petModal.primaryAction;
  closePetModal();
  if (action === "profile") {
    await router.push("/profile");
  } else if (action === "learning-path") {
    await router.push("/learning-path");
  }
};

const handleOpenPetChat = (event: Event) => {
  const detail = (event as CustomEvent<{ expanded?: boolean }>).detail || {};
  chatOpen.value = true;
  chatExpanded.value = Boolean(detail.expanded);
  chatLoading.value = false;
};

onMounted(() => {
  window.addEventListener("resize", handleResize);
  window.addEventListener("zhiban-pet-notice", handlePetNotice as EventListener);
  window.addEventListener("zhiban-pet-modal", handlePetModal as EventListener);
  window.addEventListener("zhiban-pet-open-chat", handleOpenPetChat as EventListener);
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
  window.removeEventListener("zhiban-pet-modal", handlePetModal as EventListener);
  window.removeEventListener("zhiban-pet-open-chat", handleOpenPetChat as EventListener);
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

  <Teleport to="body">
    <Transition name="pet-modal">
      <div v-if="petModalVisible" class="study-pet-modal" @click.self="closePetModal">
        <section class="study-pet-modal__panel" role="dialog" aria-modal="true" :aria-label="petModal.title">
          <div class="study-pet-modal__avatar">
            <PetCharacter state="greeting" />
          </div>
          <div class="study-pet-modal__content">
            <p class="study-pet-modal__eyebrow">XIAOZHI NOTICE</p>
            <h3>{{ petModal.title }}</h3>
            <p>{{ petModal.message }}</p>
          </div>
          <div class="study-pet-modal__actions">
            <button
              v-if="petModal.secondaryText"
              class="study-pet-modal__button secondary"
              type="button"
              @click="closePetModal"
            >
              {{ petModal.secondaryText }}
            </button>
            <button class="study-pet-modal__button primary" type="button" @click="runPetModalAction">
              {{ petModal.primaryText }}
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
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

.study-pet-modal {
  position: fixed;
  inset: 0;
  z-index: 6200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(8, 18, 32, 0.38);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.study-pet-modal__panel {
  width: min(92vw, 460px);
  padding: 24px;
  border: 1px solid rgba(96, 145, 196, 0.26);
  border-radius: 8px;
  background: rgba(248, 252, 255, 0.96);
  color: #143761;
  box-shadow: 0 28px 80px rgba(12, 34, 62, 0.28);
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 18px;
}

.study-pet-modal__avatar {
  width: 96px;
  aspect-ratio: 1;
  align-self: start;
}

.study-pet-modal__content {
  min-width: 0;
}

.study-pet-modal__eyebrow,
.study-pet-modal__content h3,
.study-pet-modal__content p {
  margin: 0;
}

.study-pet-modal__eyebrow {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.study-pet-modal__content h3 {
  margin-top: 6px;
  color: #143761;
  font-size: 22px;
  font-weight: 900;
}

.study-pet-modal__content p:not(.study-pet-modal__eyebrow) {
  margin-top: 10px;
  color: #486783;
  font-size: 15px;
  font-weight: 750;
  line-height: 1.65;
}

.study-pet-modal__actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.study-pet-modal__button {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(96, 145, 196, 0.28);
  border-radius: 8px;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.study-pet-modal__button.primary {
  background: #163f8f;
  color: #fff;
}

.study-pet-modal__button.secondary {
  background: rgba(238, 247, 252, 0.92);
  color: #143761;
}

.pet-modal-enter-active,
.pet-modal-leave-active {
  transition: opacity 0.2s ease;
}

.pet-modal-enter-active .study-pet-modal__panel,
.pet-modal-leave-active .study-pet-modal__panel {
  transition: transform 0.2s ease;
}

.pet-modal-enter-from,
.pet-modal-leave-to {
  opacity: 0;
}

.pet-modal-enter-from .study-pet-modal__panel,
.pet-modal-leave-to .study-pet-modal__panel {
  transform: translateY(10px) scale(0.98);
}

:global(html[data-theme='dark']) .study-pet-modal {
  background: rgba(5, 12, 23, 0.56);
}

:global(html[data-theme='dark']) .study-pet-modal__panel {
  border-color: rgba(114, 167, 220, 0.22);
  background: rgba(22, 34, 50, 0.97);
  color: #d7e6f5;
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.46);
}

:global(html[data-theme='dark']) .study-pet-modal__content h3 {
  color: #e7f1fb;
}

:global(html[data-theme='dark']) .study-pet-modal__content p:not(.study-pet-modal__eyebrow) {
  color: #b6c9dc;
}

:global(html[data-theme='dark']) .study-pet-modal__button.secondary {
  border-color: rgba(114, 167, 220, 0.24);
  background: rgba(28, 45, 64, 0.96);
  color: #d7e6f5;
}

@media (prefers-reduced-motion: reduce) {
  .study-pet,
  .study-pet * {
    animation: none;
  }
}

@media (max-width: 560px) {
  .study-pet-modal__panel {
    grid-template-columns: 72px minmax(0, 1fr);
    padding: 18px;
  }

  .study-pet-modal__avatar {
    width: 72px;
  }

  .study-pet-modal__actions {
    justify-content: stretch;
  }

  .study-pet-modal__button {
    flex: 1;
  }
}
</style>
