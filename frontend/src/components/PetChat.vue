<script setup lang="ts">
import { ref } from "vue";
import { resolveApiUrl, streamChatMessage } from "../api/apis";
import { useRouter } from "vue-router";
import { detectGenerationIntent, executeGeneration } from "../composables/useResourceGeneration";
import { upsertQuizSet } from "../utils/quizBank";

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  "update:expanded": [value: boolean];
  "update:loading": [value: boolean];
}>();

const SAVED_GENERATED_RESOURCES_KEY = "zhiban_saved_generated_resources";
const router = useRouter();

// ─── Types ───
type PetChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  resourceId?: number | string;
  resourceKind?: "resource" | "image";
  resourceType?: string;
  resourceFilename?: string;
  resourceContent?: string;
  resourcePreviewUrl?: string;
  resourceDownloadUrl?: string;
  quizId?: string;
  questionCount?: number;
  centerSaveStatus?: "saving" | "saved" | "error" | "";
};

type StreamChatHandlers = {
  onChunk?: (chunk: string) => void | Promise<void>;
  onDone?: (data?: { chat_group_id?: number | string }) => void;
  onError?: (error: string) => void;
  onFile?: (fileData: unknown) => void;
};

type StreamChatMessageFn = (
  data: { user_req: string; chat_group_id?: number | string | null },
  handlers?: StreamChatHandlers,
) => Promise<void>;

// ─── State ───
const chatExpanded = ref(false);
const chatInput = ref("");
const chatLoading = ref(false);
const chatError = ref("");
const petChatGroupId = ref<number | string | null>(null);
const chatFormRef = ref<HTMLFormElement | null>(null);

const petMessages = ref<PetChatMessage[]>([
  {
    id: "pet-welcome",
    role: "assistant",
    content: "嗨，我是小知。点我就能聊天，也可以问我学习资源怎么生成。",
  },
]);

// ─── Helpers ───
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

const createWelcomeMessage = (): PetChatMessage => ({
  id: `pet-welcome-${Date.now()}`,
  role: "assistant",
  content: "嗨，我是小知。点我就能聊天，也可以问我学习资源怎么生成。",
});

const getPetGeneratedFileMessage = (fileData: any) => {
  const fileId = fileData?.file_id || fileData?.fileId || fileData?.resource_id || fileData?.resourceId || "";
  const filename = fileData?.filename || fileData?.file_name || fileData?.name || "生成文件";
  const previewUrl = resolveApiUrl(fileData?.preview_url || fileData?.previewUrl || fileData?.preview || "");
  const downloadUrl = resolveApiUrl(
    fileData?.download_url || fileData?.downloadUrl || fileData?.url || (fileId ? `/resource/${fileId}/download` : ""),
  );
  const links = [previewUrl ? `[预览](${previewUrl})` : "", downloadUrl ? `[下载](${downloadUrl})` : ""].filter(Boolean);
  return links.length ? `已生成：${filename}\n${links.join("  ")}` : `已生成：${filename}`;
};

const getPetGeneratedResourceId = (fileData: any) =>
  fileData?.file_id || fileData?.fileId || fileData?.resource_id || fileData?.resourceId || "";

const isPetExerciseFile = (fileData: any) => {
  const type = String(
    fileData?.file_type || fileData?.fileType || fileData?.resource_type || fileData?.resourceType || "",
  ).toLowerCase();
  return type.includes("exercise") || type.includes("quiz") || type.includes("question");
};

const applyPetQuizFile = async (message: PetChatMessage, fileData: any) => {
  const sourceId = getPetGeneratedResourceId(fileData);
  const filename = fileData?.filename || fileData?.file_name || fileData?.name || "AI 生成题目";
  const quiz = await upsertQuizSet({
    id: message.quizId,
    sourceId,
    title: String(filename).replace(/\.[^.\\/]+$/, ""),
    filename,
    fileType: fileData?.file_type || fileData?.fileType || fileData?.resource_type || fileData?.resourceType || "exercise",
    content: fileData?.content || fileData?.text || fileData?.preview_content || fileData?.previewContent || message.resourceContent || "",
  });
  if (!quiz) return;
  message.quizId = quiz.id;
  message.questionCount = quiz.questionCount;
  message.content = `题目已生成，已放入题库。共 ${quiz.questionCount} 道题。`;
};

const openPetQuiz = (quizId?: string) => {
  if (!quizId) return;
  emit("update:modelValue", false);
  router.push(`/question-bank/${quizId}`);
};

const getPetCenterSaveLabel = (message: PetChatMessage) => {
  if (message.centerSaveStatus === "saving") return "保存中...";
  if (message.centerSaveStatus === "saved") return "已存入资源中心";
  if (message.centerSaveStatus === "error") return "重新存入资源中心";
  return "存入资源中心";
};

const getPetResourceTitle = (message: PetChatMessage) =>
  String(message.resourceFilename || "生成资源").replace(/\.[^.\\/]+$/, "");

const savePetResourceToCenter = async (message: PetChatMessage) => {
  if (!message.resourceId || message.centerSaveStatus === "saving" || message.centerSaveStatus === "saved") return;
  message.centerSaveStatus = "saving";
  try {
    const title = getPetResourceTitle(message);
    const saved = JSON.parse(localStorage.getItem(SAVED_GENERATED_RESOURCES_KEY) || "[]");
    const kind = message.resourceKind || "resource";
    const id = `${kind}-${message.resourceId}`;
    const record = {
      id,
      sourceId: message.resourceId,
      kind,
      fileType: message.resourceType || "file",
      title,
      filename: message.resourceFilename || title,
      previewUrl: message.resourcePreviewUrl || "",
      downloadUrl:
        message.resourceDownloadUrl ||
        (kind === "image"
          ? `/image/${message.resourceId}/download`
          : `/resource/${message.resourceId}/download`),
      content: message.resourceContent || "",
      createdAt: new Date().toISOString(),
    };
    const next = [record, ...saved.filter((item: any) => item.id !== id)];
    localStorage.setItem(SAVED_GENERATED_RESOURCES_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent("zhiban-generated-resource-saved", { detail: record }));
    message.centerSaveStatus = "saved";
  } catch (error: any) {
    console.error("小知资源存入资源中心失败：", error);
    message.centerSaveStatus = "error";
    window.alert(error?.message || "存入资源中心失败，请稍后再试。");
  }
};

// ─── Send ───
const sendPetMessage = async () => {
  const text = chatInput.value.trim();
  if (!text || chatLoading.value) return;

  const assistantMessage: PetChatMessage = {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: "",
  };

  petMessages.value.push({ id: `user-${Date.now()}`, role: "user", content: text });
  petMessages.value.push(assistantMessage);
  chatExpanded.value = true;
  emit("update:expanded", true);
  chatInput.value = "";
  chatError.value = "";
  chatLoading.value = true;
  emit("update:loading", true);

  try {
    const detectedTool = detectGenerationIntent(text);
    if (detectedTool?.generateMode) {
      await executeGeneration(text, detectedTool, petChatGroupId.value, {
        onProgress: (msg) => {
          assistantMessage.content = msg;
        },
        onFile: async (fileData: any) => {
          if (isPetExerciseFile(fileData)) {
            await applyPetQuizFile(assistantMessage, fileData);
            return;
          }
          assistantMessage.content = getPetGeneratedFileMessage(fileData);
          assistantMessage.resourceId = getPetGeneratedResourceId(fileData) || assistantMessage.resourceId;
          assistantMessage.resourceKind = "resource";
          assistantMessage.resourceType =
            fileData?.file_type ||
            fileData?.fileType ||
            fileData?.resource_type ||
            fileData?.resourceType ||
            assistantMessage.resourceType;
          assistantMessage.resourceFilename =
            fileData?.filename || fileData?.file_name || fileData?.name || assistantMessage.resourceFilename;
          assistantMessage.resourceContent =
            fileData?.content ||
            fileData?.text ||
            fileData?.preview_content ||
            fileData?.previewContent ||
            assistantMessage.resourceContent;
          assistantMessage.centerSaveStatus = assistantMessage.resourceId
            ? assistantMessage.centerSaveStatus || ""
            : assistantMessage.centerSaveStatus;
        },
        onDone: async (eventData: any) => {
          const savedResource = Array.isArray(eventData?.resources) ? eventData.resources[0] : null;
          if (!savedResource) return;
          if (isPetExerciseFile(savedResource)) {
            await applyPetQuizFile(assistantMessage, savedResource);
            return;
          }
          assistantMessage.resourceId = getPetGeneratedResourceId(savedResource) || assistantMessage.resourceId;
          assistantMessage.resourceKind = "resource";
          assistantMessage.resourceType =
            savedResource.file_type ||
            savedResource.fileType ||
            savedResource.resource_type ||
            savedResource.resourceType ||
            assistantMessage.resourceType;
          assistantMessage.resourceFilename =
            savedResource.filename || savedResource.file_name || savedResource.name || assistantMessage.resourceFilename;
          assistantMessage.centerSaveStatus = assistantMessage.resourceId
            ? assistantMessage.centerSaveStatus || ""
            : assistantMessage.centerSaveStatus;
        },
        onError: (err) => {
          assistantMessage.content = err;
        },
      });
      chatLoading.value = false;
      emit("update:loading", false);
      return;
    }

    let receivedChunk = false;
    await sendStreamChatMessage(
      { user_req: text, chat_group_id: petChatGroupId.value },
      {
        onChunk: (chunk: string) => {
          if (!receivedChunk) {
            assistantMessage.content = "";
            receivedChunk = true;
          }
          assistantMessage.content += chunk;
        },
        onFile: async (fileData: any) => {
          if (isPetExerciseFile(fileData)) {
            await applyPetQuizFile(assistantMessage, fileData);
            receivedChunk = true;
            return;
          }
          assistantMessage.content = getPetGeneratedFileMessage(fileData);
          assistantMessage.resourceId = getPetGeneratedResourceId(fileData) || assistantMessage.resourceId;
          assistantMessage.resourceType =
            fileData?.file_type ||
            fileData?.fileType ||
            fileData?.resource_type ||
            fileData?.resourceType ||
            assistantMessage.resourceType;
          assistantMessage.resourceFilename =
            fileData?.filename || fileData?.file_name || fileData?.name || assistantMessage.resourceFilename;
          assistantMessage.resourceContent =
            fileData?.content ||
            fileData?.text ||
            fileData?.preview_content ||
            fileData?.previewContent ||
            assistantMessage.resourceContent;
          assistantMessage.centerSaveStatus = assistantMessage.resourceId
            ? assistantMessage.centerSaveStatus || ""
            : assistantMessage.centerSaveStatus;
          receivedChunk = true;
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
    emit("update:loading", false);
  }
};

const closeChat = () => {
  emit("update:modelValue", false);
  emit("update:expanded", false);
  chatExpanded.value = false;
  chatInput.value = "";
  chatError.value = "";
  petChatGroupId.value = null;
  petMessages.value = [createWelcomeMessage()];
};

const handleChatEnter = (event: KeyboardEvent) => {
  if (event.shiftKey || event.isComposing) return;
  event.preventDefault();
  event.stopPropagation();
  chatFormRef.value?.requestSubmit();
};
</script>

<template>
  <section
    v-if="modelValue"
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
        <button
          v-if="message.role === 'assistant' && message.resourceId"
          type="button"
          class="pet-chat__save-resource"
          :disabled="message.centerSaveStatus === 'saving' || message.centerSaveStatus === 'saved'"
          @click="savePetResourceToCenter(message)"
        >
          {{ getPetCenterSaveLabel(message) }}
        </button>
        <button
          v-if="message.role === 'assistant' && message.quizId"
          type="button"
          class="pet-chat__save-resource"
          @click="openPetQuiz(message.quizId)"
        >
          去题库做题
        </button>
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
      <button type="submit" :disabled="!chatInput.trim() || chatLoading">发送</button>
    </form>
  </section>
</template>

<style scoped>
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

.pet-chat__save-resource {
  margin-top: 10px;
  min-height: 28px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: #163f8f;
  color: #ffffff;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.pet-chat__save-resource:disabled {
  opacity: 0.62;
  cursor: not-allowed;
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
