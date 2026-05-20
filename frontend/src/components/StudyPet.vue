<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { resolveApiUrl, streamChatMessage, streamResourceGeneration } from "../api/apis";
import petImage from "../assets/pic/zhiban-pet-base.png";

const PET_ASPECT_RATIO = 1;
type PetState =
  | "idle"
  | "waiting"
  | "thinking"
  | "greeting"
  | "loading"
  | "studying"
  | "failed"
  | "success";

const demoStates: PetState[] = [
  "idle",
  "waiting",
  "thinking",
  "greeting",
  "loading",
  "studying",
  "failed",
  "success",
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
const chatInput = ref("");
const chatLoading = ref(false);
const chatError = ref("");
const petChatGroupId = ref<number | string | null>(null);
const chatFormRef = ref<HTMLFormElement | null>(null);
let demoTimer: ReturnType<typeof window.setInterval> | undefined;

type PetChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type StreamChatHandlers = {
  onChunk?: (chunk: string) => void | Promise<void>;
  onDone?: (data?: { chat_group_id?: number | string }) => void;
  onError?: (error: string) => void;
  onFile?: (fileData: unknown) => void;
};

type StreamChatMessageFn = (
  data: {
    user_req: string;
    chat_group_id?: number | string | null;
  },
  handlers?: StreamChatHandlers,
) => Promise<void>;

const sendStreamChatMessage = streamChatMessage as unknown as StreamChatMessageFn;

type ResourceStreamHandlers = {
  onProgress?: (eventData: { resources?: string[]; review_passed?: boolean }) => void | Promise<void>;
  onDone?: (eventData?: { resources?: unknown[] }) => void | Promise<void>;
  onError?: (error: string) => void;
  onFile?: (fileData: unknown) => void | Promise<void>;
};

type StreamResourceGenerationFn = (
  data: {
    topic: string;
    resource_types: string[];
    chat_group_id?: number | string | null;
  },
  handlers?: ResourceStreamHandlers,
) => Promise<void>;

const sendStreamResourceGeneration = streamResourceGeneration as unknown as StreamResourceGenerationFn;

const escapeHtml = (value: string) =>
  String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const isImageUrl = (url: string) =>
  /\.(png|jpe?g|webp|gif|bmp|svg)(?:[?#].*)?$/i.test(String(url || ""));

const renderPetMarkdown = (value: string) => {
  let text = escapeHtml(value);

  text = text.replace(/!\[([^\]]*)\]\(((?:https?:\/\/|\/)[^\s)]+)\)/g, (_, label, url) => {
    const href = escapeHtml(resolveApiUrl(url));
    return `<a class="pet-chat__image-link" href="${href}" target="_blank" rel="noopener noreferrer"><img class="pet-chat__generated-image" src="${href}" alt="${label}" loading="lazy" /></a>`;
  });

  text = text.replace(/\[([^\]]+)\]\(((?:https?:\/\/|mailto:|\/)[^\s)]+)\)/g, (_, label, url) => {
    const href = escapeHtml(resolveApiUrl(url));

    if (!/^mailto:/i.test(url) && isImageUrl(url)) {
      return `<a class="pet-chat__image-link" href="${href}" target="_blank" rel="noopener noreferrer"><img class="pet-chat__generated-image" src="${href}" alt="${label}" loading="lazy" /></a>`;
    }

    return `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`;
  });

  return text.replace(/\n/g, "<br>");
};

const shouldGeneratePpt = (text: string) =>
  /(ppt|PPT|幻灯片|演示文稿)/.test(text) && /(生成|制作|做|创建|来一份|出一份)/.test(text);

const extractPptTopic = (text: string) => {
  return text
    .replace(/(帮我|请|小知|可以|能不能|能否)/g, "")
    .replace(/(生成|制作|做|创建|来一份|出一份)/g, "")
    .replace(/(一个|一份|的)?(ppt|PPT|幻灯片|演示文稿)/g, "")
    .replace(/[：:，,。！？!?]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
};

const fileTypeLabel = (type: unknown) => {
  const normalizedType = String(type || "").toLowerCase();

  if (normalizedType.includes("ppt")) return "PPT";
  if (normalizedType.includes("mindmap")) return "思维导图";
  if (normalizedType.includes("document")) return "学习文档";
  return "学习资源";
};

const renderResourceLinks = (resources: unknown[]) => {
  const links = resources
    .map((item, index) => {
      const resource = item as Record<string, unknown>;
      const label = `${fileTypeLabel(resource.file_type || resource.resource_type)} ${index + 1}`;
      const url = String(resource.download_url || "");

      return url ? `- [${label}](${url})` : `- ${label}`;
    })
    .join("\n");

  return links || "PPT 已生成，但后端没有返回下载链接。";
};

const petMessages = ref<PetChatMessage[]>([
  {
    id: "pet-welcome",
    role: "assistant",
    content: "嗨，我是小知。点我就能聊天，也可以问我学习资源怎么生成。",
  },
]);

const createWelcomeMessage = (): PetChatMessage => ({
  id: `pet-welcome-${Date.now()}`,
  role: "assistant",
  content: "嗨，我是小知。点我就能聊天，也可以问我学习资源怎么生成。",
});

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
  dragOffset.value = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
  dragPosition.value = { x: rect.left, y: rect.top };
  petRef.value.setPointerCapture(event.pointerId);
};

const moveDrag = (event: PointerEvent) => {
  if (!isDragging.value) return;
  const movedDistance = Math.hypot(
    event.clientX - pointerStart.value.x,
    event.clientY - pointerStart.value.y,
  );

  if (movedDistance > 6) {
    hasDragged.value = true;
  }

  dragPosition.value = clampPosition(
    event.clientX - dragOffset.value.x,
    event.clientY - dragOffset.value.y,
  );
};

const stopDrag = (event: PointerEvent) => {
  if (!isDragging.value) return;

  isDragging.value = false;
  suppressNextClick.value = true;

  if (!hasDragged.value) {
    toggleChat();
  }

  if (petRef.value?.hasPointerCapture(event.pointerId)) {
    petRef.value.releasePointerCapture(event.pointerId);
  }
};

const handleResize = () => {
  if (!dragPosition.value) return;
  dragPosition.value = clampPosition(dragPosition.value.x, dragPosition.value.y);
};

const activeState = computed(() => {
  if (chatLoading.value) return "thinking";
  if (chatOpen.value) return "greeting";
  return props.autoPlayActions ? demoStates[demoIndex.value] : props.state;
});

const petStyle = computed(() => ({
  "--pet-size": `${props.size}px`,
  "--pet-bottom": `${props.bottom}px`,
  ...(dragPosition.value
    ? {
        left: `${dragPosition.value.x}px`,
        top: `${dragPosition.value.y}px`,
        right: "auto",
        bottom: "auto",
      }
    : {}),
}));

const startActionDemo = () => {
  if (demoTimer) window.clearInterval(demoTimer);
  if (!props.autoPlayActions) return;

  demoTimer = window.setInterval(() => {
    demoIndex.value = (demoIndex.value + 1) % demoStates.length;
  }, 2600);
};

const toggleChat = () => {
  const nextOpen = !chatOpen.value;
  chatOpen.value = nextOpen;
  if (nextOpen && petMessages.value.length > 1) {
    chatExpanded.value = true;
  }
  chatError.value = "";
};

const handlePetClick = () => {
  if (suppressNextClick.value) {
    suppressNextClick.value = false;
    return;
  }

  toggleChat();
};

const handlePetKeydown = (event: KeyboardEvent) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  toggleChat();
};

const closeChat = () => {
  chatOpen.value = false;
  chatExpanded.value = false;
  chatInput.value = "";
  chatError.value = "";
  petChatGroupId.value = null;
  petMessages.value = [createWelcomeMessage()];
};

const sendPetMessage = async () => {
  const text = chatInput.value.trim();

  if (!text || chatLoading.value) return;

  const assistantMessage: PetChatMessage = {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: "",
  };

  petMessages.value.push({
    id: `user-${Date.now()}`,
    role: "user",
    content: text,
  });
  petMessages.value.push(assistantMessage);
  chatExpanded.value = true;
  chatInput.value = "";
  chatError.value = "";
  chatLoading.value = true;

  try {
    let receivedChunk = false;

    await sendStreamChatMessage(
      {
        user_req: text,
        chat_group_id: petChatGroupId.value,
      },
      {
        onChunk: (chunk: string) => {
          if (!receivedChunk) {
            assistantMessage.content = "";
            receivedChunk = true;
          }

          assistantMessage.content += chunk;
        },
        onDone: (data: { chat_group_id?: number | string } = {}) => {
          if (data?.chat_group_id) {
            petChatGroupId.value = data.chat_group_id;
          }
        },
      },
    );

    if (!assistantMessage.content) {
      assistantMessage.content = "我收到啦，不过这次没有返回具体内容。";
    }
  } catch (error) {
    console.error("小人聊天失败：", error);
    assistantMessage.content = "抱歉，我这会儿没有连上 AI，请稍后再试。";
    chatError.value = "AI 对话请求失败";
  } finally {
    chatLoading.value = false;
  }
};

const handleChatEnter = (event: KeyboardEvent) => {
  if (event.shiftKey || event.isComposing) return;
  event.preventDefault();
  event.stopPropagation();
  chatFormRef.value?.requestSubmit();
};

onMounted(() => {
  window.addEventListener("resize", handleResize);
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
  if (demoTimer) window.clearInterval(demoTimer);
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
    <div class="study-pet__stage">
      <img class="study-pet__image" :src="petImage" alt="" draggable="false" />
      <span class="study-pet__loading-ring" />
      <span class="study-pet__thought">
        <i />
        <i />
        <i />
      </span>
      <span class="study-pet__wave" />
      <span class="study-pet__page-flip" />
      <span class="study-pet__tear" />
      <span class="study-pet__sparkles">
        <i />
        <i />
        <i />
      </span>
    </div>

    <section
      v-if="chatOpen"
      class="pet-chat"
      :class="{ 'pet-chat--expanded': chatExpanded }"
      role="dialog"
      aria-label="小知对话"
      @click.stop
      @pointerdown.stop
      @keydown.stop
    >
      <header class="pet-chat__header">
        <div>
          <strong>小知</strong>
        </div>
        <button type="button" aria-label="关闭小知对话" @click="closeChat">×</button>
      </header>

      <div class="pet-chat__messages">
        <div
          v-for="message in petMessages"
          :key="message.id"
          class="pet-chat__message"
          :class="`pet-chat__message--${message.role}`"
        >
          <span v-html="renderPetMarkdown(message.content || 'Thinking...')"></span>
        </div>
      </div>

      <p v-if="chatError" class="pet-chat__error">{{ chatError }}</p>

      <form ref="chatFormRef" class="pet-chat__form" @submit.prevent="sendPetMessage">
        <textarea
          v-model="chatInput"
          rows="1"
          placeholder="问我一个问题..."
          :disabled="chatLoading"
          @keydown.enter="handleChatEnter"
        />
        <button type="submit" :disabled="!chatInput.trim() || chatLoading">
          发送
        </button>
      </form>
    </section>
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

.study-pet:focus-visible {
  outline: 3px solid rgba(95, 143, 195, 0.32);
  outline-offset: 6px;
  border-radius: 28px;
}

.study-pet__stage {
  position: relative;
  width: 100%;
  height: 100%;
  animation: pet-idle 3.6s ease-in-out infinite;
  transform-origin: 50% 88%;
}

.study-pet--waiting .study-pet__stage {
  animation: pet-waiting 1.8s ease-in-out infinite;
}

.study-pet--thinking .study-pet__stage {
  animation: pet-thinking 2.2s ease-in-out infinite;
}

.study-pet--greeting .study-pet__stage {
  animation: pet-greeting 1.35s ease-in-out infinite;
}

.study-pet--loading .study-pet__stage {
  animation: pet-loading-pulse 1.6s ease-in-out infinite;
}

.study-pet--studying .study-pet__stage {
  animation: pet-studying 2.4s ease-in-out infinite;
}

.study-pet--failed .study-pet__stage {
  animation: pet-failed 1.8s ease-in-out infinite;
}

.study-pet--success .study-pet__stage {
  animation: pet-success 1.35s ease-in-out infinite;
}

.study-pet--dragging .study-pet__stage {
  animation-play-state: paused;
}

.study-pet__image {
  position: relative;
  z-index: 2;
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  pointer-events: none;
  -webkit-user-drag: none;
}

.study-pet__loading-ring,
.study-pet__thought,
.study-pet__wave,
.study-pet__page-flip,
.study-pet__tear,
.study-pet__sparkles {
  position: absolute;
  pointer-events: none;
  opacity: 0;
}

.study-pet__loading-ring {
  z-index: 1;
  inset: 8%;
  border-radius: 999px;
  background: conic-gradient(from 0deg, rgba(97, 225, 255, 0), rgba(97, 225, 255, 0.72), rgba(97, 225, 255, 0));
  mask: radial-gradient(circle, transparent 62%, #000 63%);
}

.study-pet--loading .study-pet__loading-ring {
  opacity: 1;
  animation: pet-ring 1s linear infinite;
}

.study-pet__thought {
  z-index: 3;
  left: 12%;
  top: 7%;
  width: 30%;
  height: 13%;
}

.study-pet__thought i {
  position: absolute;
  display: block;
  width: 22%;
  aspect-ratio: 1;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 4px 12px rgba(40, 136, 205, 0.2);
}

.study-pet__thought i:nth-child(1) {
  left: 0;
  bottom: 4%;
}

.study-pet__thought i:nth-child(2) {
  left: 30%;
  top: 24%;
}

.study-pet__thought i:nth-child(3) {
  right: 6%;
  top: 0;
}

.study-pet--thinking .study-pet__thought,
.study-pet--waiting .study-pet__thought {
  opacity: 1;
  animation: pet-pop 1.6s ease-in-out infinite;
}

.study-pet__wave {
  z-index: 3;
  right: 5%;
  top: 31%;
  width: 18%;
  height: 18%;
  border: 4px solid rgba(80, 211, 255, 0.8);
  border-left-color: transparent;
  border-bottom-color: transparent;
  border-radius: 50%;
  transform: rotate(-18deg);
}

.study-pet--greeting .study-pet__wave {
  opacity: 1;
  animation: pet-wave-mark 0.8s ease-in-out infinite;
}

.study-pet__page-flip {
  z-index: 4;
  left: 31%;
  top: 52%;
  width: 24%;
  height: 17%;
  border-radius: 58% 12% 22% 18%;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(210, 238, 255, 0.4));
  transform-origin: 92% 82%;
  transform: rotate(-10deg) scaleX(0);
}

.study-pet--studying .study-pet__page-flip {
  opacity: 1;
  animation: pet-page 1.3s ease-in-out infinite;
}

.study-pet__tear {
  z-index: 4;
  left: 33%;
  top: 43%;
  width: 5%;
  height: 8%;
  border-radius: 58% 58% 58% 12%;
  background: linear-gradient(180deg, #72eaff, #1593dd);
  transform: rotate(24deg);
}

.study-pet--failed .study-pet__tear {
  opacity: 1;
  animation: pet-tear 1.4s ease-in-out infinite;
}

.study-pet__sparkles {
  z-index: 4;
  inset: 3% 0 auto auto;
  width: 38%;
  height: 32%;
}

.study-pet__sparkles i {
  position: absolute;
  display: block;
  width: 14%;
  aspect-ratio: 1;
  background: #fff9a8;
  clip-path: polygon(50% 0, 62% 36%, 100% 50%, 62% 64%, 50% 100%, 38% 64%, 0 50%, 38% 36%);
  filter: drop-shadow(0 0 8px rgba(255, 241, 92, 0.72));
}

.study-pet__sparkles i:nth-child(1) {
  left: 10%;
  top: 35%;
}

.study-pet__sparkles i:nth-child(2) {
  right: 12%;
  top: 8%;
  width: 18%;
}

.study-pet__sparkles i:nth-child(3) {
  right: 24%;
  bottom: 12%;
  width: 11%;
}

.study-pet--success .study-pet__sparkles {
  opacity: 1;
  animation: pet-pop 1s ease-in-out infinite;
}

.pet-chat {
  position: absolute;
  right: calc(100% - 36px);
  bottom: calc(100% - 36px);
  z-index: 6;
  width: min(360px, calc(100vw - 32px));
  max-height: min(520px, calc(100vh - 72px));
  padding: 14px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow:
    0 22px 58px rgba(22, 63, 143, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
  cursor: default;
  pointer-events: auto;
  animation: pet-chat-pop 220ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  transition:
    border-radius 420ms cubic-bezier(0.22, 1, 0.36, 1),
    background 420ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.pet-chat::after {
  content: "";
  position: absolute;
  right: 28px;
  bottom: -10px;
  width: 20px;
  height: 20px;
  border-right: 1px solid rgba(22, 63, 143, 0.14);
  border-bottom: 1px solid rgba(22, 63, 143, 0.14);
  background: rgba(255, 255, 255, 0.94);
  transform: rotate(45deg);
}

.pet-chat--expanded {
  position: fixed;
  inset: clamp(18px, 3vw, 42px);
  z-index: 1300;
  width: auto;
  max-height: none;
  padding: clamp(18px, 2.4vw, 30px);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.24);
  box-shadow:
    0 30px 90px rgba(22, 63, 143, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.46);
  backdrop-filter: blur(24px) saturate(138%);
  -webkit-backdrop-filter: blur(24px) saturate(138%);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto auto;
  animation: pet-chat-expand 520ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.pet-chat--expanded::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(10px) saturate(118%);
  -webkit-backdrop-filter: blur(10px) saturate(118%);
  pointer-events: none;
}

.pet-chat--expanded::after {
  content: none;
}

.pet-chat__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 2px 2px 12px;
  border-bottom: 1px solid rgba(201, 220, 233, 0.58);
}

.pet-chat--expanded .pet-chat__header {
  max-width: 1080px;
  width: 100%;
  margin: 0 auto;
  padding: 0 0 18px;
}

.pet-chat__header div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.pet-chat__header strong {
  color: #163f8f;
  font-size: 15px;
  line-height: 1.25;
}

.pet-chat--expanded .pet-chat__header strong {
  font-size: 22px;
}

.pet-chat__header span {
  color: rgba(22, 63, 143, 0.58);
  font-size: 12px;
}

.pet-chat__header button {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 999px;
  background: rgba(201, 220, 233, 0.46);
  color: #163f8f;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.pet-chat--expanded .pet-chat__header button {
  width: 38px;
  height: 38px;
  font-size: 24px;
}

.pet-chat__messages {
  max-height: 300px;
  margin: 12px 0;
  padding-right: 4px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.pet-chat--expanded .pet-chat__messages {
  width: min(100%, 1080px);
  max-height: none;
  min-height: 0;
  margin: 20px auto;
  padding: 4px 8px 4px 0;
  gap: 14px;
}

.pet-chat__message {
  max-width: 86%;
  padding: 10px 12px;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 14px;
  color: #163f8f;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

:deep(.pet-chat__image-link) {
  display: block;
  margin-top: 8px;
  text-decoration: none;
}

:deep(.pet-chat__generated-image) {
  display: block;
  width: min(100%, 360px);
  max-height: 280px;
  object-fit: contain;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 12px 24px rgba(22, 63, 143, 0.1);
}

.pet-chat--expanded .pet-chat__message {
  max-width: min(760px, 78%);
  padding: 14px 16px;
  border-radius: 18px;
  font-size: 15px;
}

.pet-chat__message--assistant {
  align-self: flex-start;
  background: rgba(250, 250, 250, 0.96);
  border-top-left-radius: 6px;
}

.pet-chat__message--user {
  align-self: flex-end;
  background: #163f8f;
  color: #ffffff;
  border-color: #163f8f;
  border-top-right-radius: 6px;
}

.pet-chat__error {
  margin: -4px 0 10px;
  color: #c2410c;
  font-size: 12px;
}

.pet-chat--expanded .pet-chat__error {
  width: min(100%, 1080px);
  margin: 0 auto 10px;
}

.pet-chat__form {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid rgba(201, 220, 233, 0.58);
}

.pet-chat--expanded .pet-chat__form {
  width: min(100%, 1080px);
  margin: 0 auto;
  padding: 16px;
  border: 1px solid rgba(201, 220, 233, 0.68);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.42);
  box-shadow:
    0 16px 42px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.58);
  backdrop-filter: blur(14px) saturate(130%);
  -webkit-backdrop-filter: blur(14px) saturate(130%);
}

.pet-chat__form textarea {
  flex: 1;
  min-height: 42px;
  max-height: 92px;
  padding: 10px 12px;
  border: 1px solid rgba(201, 220, 233, 0.84);
  border-radius: 12px;
  outline: none;
  resize: none;
  background: #ffffff;
  color: #163f8f;
  font: inherit;
  font-size: 13px;
  line-height: 1.5;
}

.pet-chat--expanded .pet-chat__form textarea {
  min-height: 52px;
  max-height: 150px;
  font-size: 15px;
}

.pet-chat__form textarea:focus {
  border-color: #5f8fc3;
  box-shadow: 0 0 0 3px rgba(95, 143, 195, 0.16);
}

.pet-chat__form button {
  height: 42px;
  padding: 0 14px;
  border: none;
  border-radius: 12px;
  background: #163f8f;
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.pet-chat--expanded .pet-chat__form button {
  height: 52px;
  min-width: 76px;
  font-size: 14px;
}

.pet-chat__form button:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.pet-chat__messages::-webkit-scrollbar {
  width: 7px;
}

.pet-chat__messages::-webkit-scrollbar-track {
  background: transparent;
}

.pet-chat__messages::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(95, 143, 195, 0.36);
}

@keyframes pet-chat-pop {
  from {
    opacity: 0;
    transform: translate(10px, 10px) scale(0.94);
  }

  to {
    opacity: 1;
    transform: translate(0, 0) scale(1);
  }
}

@keyframes pet-chat-expand {
  from {
    opacity: 0.82;
    transform: translateY(18px) scale(0.96);
    filter: blur(2px);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
  }
}

@keyframes pet-idle {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }

  50% {
    transform: translateY(-6px) scale(1.01);
  }
}

@keyframes pet-waiting {
  0%,
  100% {
    transform: translateY(0) rotate(0);
  }

  32% {
    transform: translateY(-5px) rotate(-2.2deg);
  }

  66% {
    transform: translateY(-5px) rotate(2.2deg);
  }
}

@keyframes pet-thinking {
  0%,
  100% {
    transform: translateY(0) rotate(0);
  }

  50% {
    transform: translateY(-5px) rotate(-3deg);
  }
}

@keyframes pet-greeting {
  0%,
  100% {
    transform: translateY(0) rotate(-1deg);
  }

  35% {
    transform: translateY(-9px) rotate(4deg);
  }

  70% {
    transform: translateY(-4px) rotate(-3deg);
  }
}

@keyframes pet-loading-pulse {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }

  50% {
    transform: translateY(-4px) scale(0.985);
  }
}

@keyframes pet-studying {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-4px);
  }
}

@keyframes pet-failed {
  0%,
  100% {
    transform: translateY(7px) rotate(0) scale(0.985);
  }

  26% {
    transform: translateY(7px) rotate(-1.8deg) scale(0.985);
  }

  52% {
    transform: translateY(7px) rotate(1.8deg) scale(0.985);
  }
}

@keyframes pet-success {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }

  40% {
    transform: translateY(-18px) scale(1.04);
  }

  72% {
    transform: translateY(2px) scale(0.99);
  }
}

@keyframes pet-ring {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pet-pop {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }

  50% {
    transform: translateY(-5px) scale(1.08);
  }
}

@keyframes pet-wave-mark {
  0%,
  100% {
    transform: rotate(-18deg) scale(0.82);
  }

  50% {
    transform: rotate(-18deg) scale(1.1);
  }
}

@keyframes pet-page {
  0% {
    transform: rotate(-12deg) scaleX(0);
    opacity: 0;
  }

  25% {
    opacity: 0.95;
  }

  60% {
    transform: rotate(12deg) scaleX(1);
    opacity: 0.75;
  }

  100% {
    transform: rotate(18deg) scaleX(0);
    opacity: 0;
  }
}

@keyframes pet-tear {
  0%,
  100% {
    transform: translateY(0) rotate(24deg) scale(0.8);
  }

  50% {
    transform: translateY(10px) rotate(24deg) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .study-pet,
  .study-pet * {
    animation: none;
  }
}

@media (max-width: 720px) {
  .pet-chat {
    position: fixed;
    left: 16px;
    right: 16px;
    bottom: calc(var(--pet-size) + var(--pet-bottom) + 10px);
    width: auto;
    max-height: min(480px, calc(100vh - 120px));
  }

  .pet-chat::after {
    right: 54px;
  }

  .pet-chat--expanded {
    inset: 12px;
    width: auto;
    max-height: none;
    padding: 16px;
    border-radius: 22px;
  }

  .pet-chat--expanded .pet-chat__messages {
    margin: 14px auto;
  }

  .pet-chat--expanded .pet-chat__message {
    max-width: 88%;
    font-size: 14px;
  }

  .pet-chat--expanded .pet-chat__form {
    padding: 12px;
    border-radius: 18px;
  }
}
</style>
