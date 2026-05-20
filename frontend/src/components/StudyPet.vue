<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { getPortrait, getUserProfile, initPortrait, resolveApiUrl, streamChatMessage } from "../api/apis";
import { detectGenerationIntent, executeGeneration } from "../composables/useResourceGeneration";
import petImage from "../assets/pic/zhiban-pet-base.png";
import { FileText, Image, Plus } from "lucide-vue-next";

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
const attachmentMenuOpen = ref(false);
const petChatGroupId = ref<number | string | null>(null);
const chatFormRef = ref<HTMLFormElement | null>(null);
let demoTimer: ReturnType<typeof window.setInterval> | undefined;

type PetChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type PortraitDimension = {
  key: string;
  title: string;
  description: string;
  tags: string[];
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

const petMessages = ref<PetChatMessage[]>([
  {
    id: "pet-welcome",
    role: "assistant",
    content: "嗨，我是小知。点我就能聊天，也可以问我学习资源怎么生成。",
  },
]);

const portraitDimensions: PortraitDimension[] = [
  {
    key: "interests",
    title: "兴趣爱好",
    description: "我会用它来推荐更贴近你的学习素材。",
    tags: ["编程", "科学探索", "绘画", "音乐", "体育", "阅读", "社会实践", "手工", "游戏策略", "摄影"],
  },
  {
    key: "learningStyle",
    title: "学习方式",
    description: "我会据此调整讲解、练习和总结方式。",
    tags: ["独立学习", "小组讨论", "动手操作", "多媒体学习", "喜欢记笔记", "喜欢问问题", "快速学习", "深度思考", "喜欢做练习"],
  },
  {
    key: "personality",
    title: "性格特征",
    description: "让我知道怎样的节奏和语气更适合你。",
    tags: ["外向", "内向", "乐观", "谨慎", "喜欢挑战", "稳妥", "主动", "需要鼓励", "细心", "容易分心"],
  },
  {
    key: "subjects",
    title: "学科偏好",
    description: "我会优先理解你关注的学科方向。",
    tags: ["数学", "物理", "化学", "生物", "语文", "英语", "历史", "地理", "艺术", "体育"],
  },
  {
    key: "skills",
    title: "能力特点",
    description: "这些会帮助我判断适合你的任务难度。",
    tags: ["逻辑思维", "语言表达", "动手能力", "团队协作", "创意设计", "分析判断", "编程技能", "领导力", "时间管理"],
  },
  {
    key: "values",
    title: "习惯与态度",
    description: "我会用它来安排更自然的学习提醒。",
    tags: ["守时", "勤奋", "好奇", "探索", "责任感", "独立", "合作", "自律", "适应力", "主动性"],
  },
];

const createPortraitSelection = () =>
  portraitDimensions.reduce<Record<string, string[]>>((result, dimension) => {
    result[dimension.key] = [];
    return result;
  }, {});

const portraitPromptVisible = ref(false);
const portraitWizardVisible = ref(false);
const portraitCompleteVisible = ref(false);
const portraitChecking = ref(false);
const portraitSaving = ref(false);
const portraitError = ref("");
const portraitStep = ref(0);
const portraitTags = ref<Record<string, string[]>>(createPortraitSelection());
const portraitUsername = ref("");

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

const currentPortraitDimension = computed(() => portraitDimensions[portraitStep.value]);

const currentPortraitTags = computed(() => {
  const dimension = currentPortraitDimension.value;
  return dimension ? portraitTags.value[dimension.key] || [] : [];
});

const canGoNextPortraitStep = computed(() => currentPortraitTags.value.length > 0 && !portraitSaving.value);

const portraitProgressText = computed(() => `${portraitStep.value + 1}/${portraitDimensions.length}`);

const portraitSkipKey = () => {
  const userId = localStorage.getItem("user_id") || localStorage.getItem("token") || "anonymous";
  return `zhiban_portrait_setup_skipped_${userId}`;
};

const handleLoginSuccess = () => {
  window.setTimeout(checkPortraitOnboarding, 150);
};

const getResponseData = (res: any) => res?.data ?? res ?? {};

const hasSavedPortraitTags = (portrait: any) => {
  const tags = portrait?.personality_tags;
  if (!tags) return false;

  try {
    const parsed = typeof tags === "string" ? JSON.parse(tags) : tags;
    if (Array.isArray(parsed)) return parsed.length > 0;
    if (parsed && typeof parsed === "object") {
      return portraitDimensions.some((dimension) => Array.isArray(parsed[dimension.key]) && parsed[dimension.key].length > 0);
    }
  } catch {
    return String(tags).trim().length > 0;
  }

  return false;
};

const loadPortraitUsername = async () => {
  portraitUsername.value =
    localStorage.getItem("username") ||
    localStorage.getItem("account") ||
    localStorage.getItem("user_id") ||
    "同学";

  try {
    const profile = getResponseData(await getUserProfile());
    if (profile?.username) {
      portraitUsername.value = profile.username;
      localStorage.setItem("username", profile.username);
    }
  } catch {
    // Keep the local fallback.
  }
};

const checkPortraitOnboarding = async () => {
  if (portraitChecking.value || !localStorage.getItem("token")) return;
  if (localStorage.getItem(portraitSkipKey()) === "1") return;

  portraitChecking.value = true;
  try {
    await loadPortraitUsername();
    const portrait = getResponseData(await getPortrait());
    if (!hasSavedPortraitTags(portrait)) {
      portraitPromptVisible.value = true;
      portraitWizardVisible.value = false;
      portraitCompleteVisible.value = false;
    }
  } catch {
    await loadPortraitUsername();
    portraitPromptVisible.value = true;
  } finally {
    portraitChecking.value = false;
  }
};

const openPortraitWizard = () => {
  portraitPromptVisible.value = false;
  portraitWizardVisible.value = true;
  portraitCompleteVisible.value = false;
  portraitStep.value = 0;
  portraitError.value = "";
  portraitTags.value = createPortraitSelection();
};

const closePortraitOnboarding = () => {
  portraitPromptVisible.value = false;
  portraitWizardVisible.value = false;
  portraitCompleteVisible.value = false;
  portraitError.value = "";
};

const skipPortraitOnboarding = () => {
  localStorage.setItem(portraitSkipKey(), "1");
  closePortraitOnboarding();
};

const togglePortraitTag = (tag: string) => {
  const dimension = currentPortraitDimension.value;
  if (!dimension) return;

  portraitError.value = "";
  const tags = portraitTags.value[dimension.key];
  const index = tags.indexOf(tag);

  if (index >= 0) {
    tags.splice(index, 1);
    return;
  }

  if (tags.length >= 3) {
    portraitError.value = "每个维度最多选择 3 个标签";
    return;
  }

  tags.push(tag);
};

const finishPortraitSetup = async () => {
  portraitSaving.value = true;
  portraitError.value = "";

  try {
    const tagsPayload = portraitDimensions.flatMap((dimension) => portraitTags.value[dimension.key]);
    await initPortrait({
      cognition: null,
      learning_goal: null,
      personality_tags: JSON.stringify(tagsPayload),
    });

    portraitWizardVisible.value = false;
    portraitCompleteVisible.value = true;
    window.setTimeout(() => {
      portraitCompleteVisible.value = false;
    }, 7600);
  } catch (error: any) {
    portraitError.value =
      error?.response?.data?.detail ||
      error?.response?.data?.msg ||
      error?.message ||
      "保存失败，请稍后再试";
  } finally {
    portraitSaving.value = false;
  }
};

const goNextPortraitStep = async () => {
  if (!canGoNextPortraitStep.value) {
    portraitError.value = "请至少选择 1 个标签";
    return;
  }

  if (portraitStep.value < portraitDimensions.length - 1) {
    portraitStep.value += 1;
    portraitError.value = "";
    return;
  }

  await finishPortraitSetup();
};

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
  attachmentMenuOpen.value = false;
  petChatGroupId.value = null;
  petMessages.value = [createWelcomeMessage()];
};

const toggleAttachmentMenu = () => {
  attachmentMenuOpen.value = !attachmentMenuOpen.value;
};

const handlePetAddFile = () => {
  attachmentMenuOpen.value = false;
};

const handlePetAddImage = () => {
  attachmentMenuOpen.value = false;
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
  attachmentMenuOpen.value = false;
  chatLoading.value = true;

  try {
    // 关键词检测 — 自动路由到资源/图片生成
    const detectedTool = detectGenerationIntent(text)
    if (detectedTool?.generateMode) {
      await executeGeneration(text, detectedTool, petChatGroupId.value, {
        onProgress: (msg) => { assistantMessage.content = msg },
        onFile: (fileData: any) => {
          assistantMessage.content = `✅ 已生成：${fileData.filename || fileData.file_name || '文件'}`
        },
        onError: (err) => { assistantMessage.content = err },
      })
      chatLoading.value = false
      return
    }

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
  window.addEventListener("zhiban-login-success", handleLoginSuccess);
  startActionDemo();

  nextTick(() => {
    if (!props.floating || !petRef.value) return;

    const rect = petRef.value.getBoundingClientRect();
    dragPosition.value = clampPosition(rect.left, rect.top);
  });

  window.setTimeout(checkPortraitOnboarding, 450);
});

watch(() => props.autoPlayActions, startActionDemo);

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  window.removeEventListener("zhiban-login-success", handleLoginSuccess);
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

    <Transition name="pet-onboarding-pop">
      <section
        v-if="portraitPromptVisible"
        class="pet-onboarding pet-onboarding--prompt"
        @click.stop
        @pointerdown.stop
        @keydown.stop
      >
        <p>hi {{ portraitUsername }}，帮助我认识一下你吧！</p>
        <div class="pet-onboarding__actions">
          <button type="button" class="pet-onboarding__primary" @click="openPortraitWizard">开始</button>
          <button type="button" class="pet-onboarding__ghost" @click="skipPortraitOnboarding">跳过</button>
        </div>
      </section>
    </Transition>

    <Transition name="pet-onboarding-pop">
      <section
        v-if="portraitCompleteVisible"
        class="pet-onboarding pet-onboarding--complete"
        @click.stop
        @pointerdown.stop
        @keydown.stop
      >
        <p>我现在认识你了！以后请多和我对话吧，让我更了解你，帮助你更好的学习吧！</p>
      </section>
    </Transition>

    <Transition name="portrait-wizard-fade">
      <section
        v-if="portraitWizardVisible && currentPortraitDimension"
        class="portrait-wizard"
        role="dialog"
        aria-label="小知画像构建"
        @click.stop
        @pointerdown.stop
        @keydown.stop
      >
        <header class="portrait-wizard__header">
          <div>
            <span>{{ portraitProgressText }}</span>
            <h3>{{ currentPortraitDimension.title }}</h3>
            <p>{{ currentPortraitDimension.description }}</p>
          </div>
          <button type="button" @click="skipPortraitOnboarding">跳过</button>
        </header>

        <Transition name="portrait-card-slide" mode="out-in">
          <article :key="currentPortraitDimension.key" class="portrait-wizard__card">
            <div class="portrait-wizard__tags">
              <button
                v-for="tag in currentPortraitDimension.tags"
                :key="tag"
                type="button"
                :class="{ selected: currentPortraitTags.includes(tag) }"
                @click="togglePortraitTag(tag)"
              >
                {{ tag }}
              </button>
            </div>
          </article>
        </Transition>

        <p v-if="portraitError" class="portrait-wizard__error">{{ portraitError }}</p>

        <footer class="portrait-wizard__footer">
          <button
            type="button"
            class="portrait-wizard__back"
            :disabled="portraitStep === 0 || portraitSaving"
            @click="portraitStep -= 1"
          >
            上一步
          </button>
          <button
            type="button"
            class="portrait-wizard__next"
            :disabled="!canGoNextPortraitStep"
            @click="goNextPortraitStep"
          >
            {{ portraitSaving ? "保存中..." : portraitStep === portraitDimensions.length - 1 ? "完成" : "下一步" }}
          </button>
        </footer>
      </section>
    </Transition>

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
        <div class="pet-chat__attach">
          <button
            type="button"
            class="pet-chat__attach-btn"
            aria-label="添加附件"
            @click="toggleAttachmentMenu"
          >
            <Plus :size="18" stroke-width="2" />
          </button>

          <div v-if="attachmentMenuOpen" class="pet-chat__attach-menu">
            <button type="button" @click="handlePetAddFile">
              <FileText :size="16" stroke-width="1.8" />
              添加文件
            </button>
            <button type="button" @click="handlePetAddImage">
              <Image :size="16" stroke-width="1.8" />
              添加图片
            </button>
          </div>
        </div>

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

.pet-onboarding {
  position: absolute;
  right: calc(100% - 34px);
  bottom: calc(100% - 28px);
  z-index: 8;
  width: min(270px, calc(100vw - 32px));
  padding: 14px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 22px 58px rgba(22, 63, 143, 0.18);
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
  cursor: default;
  pointer-events: auto;
}

.pet-onboarding::after {
  content: "";
  position: absolute;
  right: 28px;
  bottom: -9px;
  width: 18px;
  height: 18px;
  border-right: 1px solid rgba(22, 63, 143, 0.14);
  border-bottom: 1px solid rgba(22, 63, 143, 0.14);
  background: rgba(255, 255, 255, 0.96);
  transform: rotate(45deg);
}

.pet-onboarding p {
  margin: 0;
  color: #163f8f;
  font-size: 14px;
  line-height: 1.65;
  font-weight: 800;
}

.pet-onboarding--complete {
  width: min(360px, calc(100vw - 32px));
}

.pet-onboarding__actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.pet-onboarding__actions button,
.portrait-wizard button {
  font: inherit;
}

.pet-onboarding__primary,
.pet-onboarding__ghost {
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
}

.pet-onboarding__primary {
  border: 1px solid #163f8f;
  background: #163f8f;
  color: #ffffff;
}

.pet-onboarding__ghost {
  border: 1px solid rgba(201, 220, 233, 0.82);
  background: #ffffff;
  color: #163f8f;
}

.portrait-wizard {
  position: fixed;
  right: clamp(22px, 4vw, 72px);
  bottom: clamp(170px, 22vh, 230px);
  z-index: 1250;
  width: min(480px, calc(100vw - 32px));
  padding: 18px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 28px 72px rgba(22, 63, 143, 0.2);
  backdrop-filter: blur(22px) saturate(145%);
  -webkit-backdrop-filter: blur(22px) saturate(145%);
  cursor: default;
  pointer-events: auto;
}

.portrait-wizard__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.portrait-wizard__header span {
  display: inline-flex;
  height: 24px;
  padding: 0 9px;
  align-items: center;
  border-radius: 999px;
  background: rgba(201, 220, 233, 0.64);
  color: #163f8f;
  font-size: 12px;
  font-weight: 900;
}

.portrait-wizard__header h3 {
  margin: 10px 0 5px;
  color: #163f8f;
  font-size: 21px;
  line-height: 1.25;
}

.portrait-wizard__header p {
  margin: 0;
  color: rgba(22, 63, 143, 0.62);
  font-size: 13px;
  line-height: 1.5;
}

.portrait-wizard__header > button {
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 999px;
  background: #ffffff;
  color: #163f8f;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.portrait-wizard__card {
  margin-top: 16px;
  min-height: 174px;
  padding: 16px;
  border-radius: 20px;
  background:
    radial-gradient(circle at 18% 0%, rgba(209, 244, 250, 0.54), transparent 40%),
    rgba(250, 250, 250, 0.88);
  border: 1px solid rgba(201, 220, 233, 0.72);
}

.portrait-wizard__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.portrait-wizard__tags button {
  min-height: 36px;
  padding: 0 13px;
  border: 1px solid rgba(201, 220, 233, 0.92);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.84);
  color: #163f8f;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.portrait-wizard__tags button:hover {
  transform: translateY(-1px);
  border-color: #5f8fc3;
}

.portrait-wizard__tags button.selected {
  background: #163f8f;
  border-color: #163f8f;
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(22, 63, 143, 0.16);
}

.portrait-wizard__error {
  margin: 10px 4px 0;
  color: #c2410c;
  font-size: 12px;
}

.portrait-wizard__footer {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.portrait-wizard__back,
.portrait-wizard__next {
  height: 40px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}

.portrait-wizard__back {
  border: 1px solid rgba(201, 220, 233, 0.82);
  background: #ffffff;
  color: #163f8f;
}

.portrait-wizard__next {
  border: 1px solid #163f8f;
  background: #163f8f;
  color: #ffffff;
}

.portrait-wizard__back:disabled,
.portrait-wizard__next:disabled {
  opacity: 0.45;
  cursor: not-allowed;
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
  position: relative;
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

.pet-chat__attach {
  position: relative;
  flex-shrink: 0;
}

.pet-chat__attach-btn {
  width: 42px;
  min-width: 42px;
  padding: 0;
  border: 1px solid rgba(201, 220, 233, 0.84);
  background: #ffffff;
  color: #163f8f;
}

.pet-chat__attach-menu {
  position: absolute;
  left: 0;
  bottom: calc(100% + 8px);
  z-index: 4;
  width: 150px;
  padding: 8px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 16px 32px rgba(22, 63, 143, 0.12);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pet-chat__attach-menu button {
  width: 100%;
  min-height: 36px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #163f8f;
  display: flex;
  align-items: center;
  gap: 8px;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  text-align: left;
}

.pet-chat__attach-menu button:hover {
  background: rgba(201, 220, 233, 0.5);
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

.pet-onboarding-pop-enter-active,
.pet-onboarding-pop-leave-active {
  transition: opacity 220ms ease, transform 220ms cubic-bezier(0.22, 1, 0.36, 1), filter 220ms ease;
}

.pet-onboarding-pop-enter-from,
.pet-onboarding-pop-leave-to {
  opacity: 0;
  transform: translate(12px, 12px) scale(0.94);
  filter: blur(2px);
}

.portrait-wizard-fade-enter-active,
.portrait-wizard-fade-leave-active {
  transition: opacity 260ms ease, transform 320ms cubic-bezier(0.22, 1, 0.36, 1), filter 260ms ease;
}

.portrait-wizard-fade-enter-from,
.portrait-wizard-fade-leave-to {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
  filter: blur(2px);
}

.portrait-card-slide-enter-active,
.portrait-card-slide-leave-active {
  transition: opacity 220ms ease, transform 260ms cubic-bezier(0.22, 1, 0.36, 1), filter 220ms ease;
}

.portrait-card-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
  filter: blur(2px);
}

.portrait-card-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
  filter: blur(2px);
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
  .pet-onboarding {
    position: fixed;
    left: 16px;
    right: 16px;
    bottom: calc(var(--pet-size) + var(--pet-bottom) + 10px);
    width: auto;
  }

  .pet-onboarding::after {
    right: 54px;
  }

  .portrait-wizard {
    left: 14px;
    right: 14px;
    bottom: calc(var(--pet-size) + var(--pet-bottom) + 8px);
    width: auto;
    padding: 14px;
    border-radius: 22px;
  }

  .portrait-wizard__card {
    min-height: 150px;
    padding: 14px;
  }

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
