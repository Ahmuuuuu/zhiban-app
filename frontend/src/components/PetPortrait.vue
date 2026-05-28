<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { getPortrait, getUserProfile, initPortrait } from "../api/apis";

type PortraitDimension = {
  key: string;
  title: string;
  description: string;
  tags: string[];
};

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
      return portraitDimensions.some(
        (dimension) => Array.isArray(parsed[dimension.key]) && parsed[dimension.key].length > 0,
      );
    }
  } catch {
    return String(tags).trim().length > 0;
  }
  return false;
};

const loadPortraitUsername = async () => {
  portraitUsername.value =
    localStorage.getItem("username") || localStorage.getItem("account") || localStorage.getItem("user_id") || "同学";
  try {
    const profile = getResponseData(await getUserProfile());
    if (profile?.username) {
      portraitUsername.value = profile.username;
      localStorage.setItem("username", profile.username);
    }
  } catch {
    // Keep local fallback.
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
  if (index >= 0) { tags.splice(index, 1); return; }
  if (tags.length >= 3) { portraitError.value = "每个维度最多选择 3 个标签"; return; }
  tags.push(tag);
};

const finishPortraitSetup = async () => {
  portraitSaving.value = true;
  portraitError.value = "";
  try {
    const tagsPayload = portraitDimensions.flatMap((dimension) => portraitTags.value[dimension.key]);
    await initPortrait({ cognition: null, learning_goal: null, personality_tags: JSON.stringify(tagsPayload) });
    portraitWizardVisible.value = false;
    portraitCompleteVisible.value = true;
    window.setTimeout(() => { portraitCompleteVisible.value = false; }, 7600);
  } catch (error: any) {
    portraitError.value = error?.response?.data?.detail || error?.response?.data?.msg || error?.message || "保存失败，请稍后再试";
  } finally {
    portraitSaving.value = false;
  }
};

const goNextPortraitStep = async () => {
  if (!canGoNextPortraitStep.value) { portraitError.value = "请至少选择 1 个标签"; return; }
  if (portraitStep.value < portraitDimensions.length - 1) { portraitStep.value += 1; portraitError.value = ""; return; }
  await finishPortraitSetup();
};

onMounted(() => {
  window.addEventListener("zhiban-login-success", handleLoginSuccess);
  window.setTimeout(checkPortraitOnboarding, 450);
});

onUnmounted(() => {
  window.removeEventListener("zhiban-login-success", handleLoginSuccess);
});
</script>

<template>
  <Transition name="portrait-backdrop-fade">
    <div v-if="portraitPromptVisible || portraitWizardVisible || portraitCompleteVisible" class="portrait-backdrop" @click="closePortraitOnboarding" />
  </Transition>

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
</template>

<style scoped>
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
  background: radial-gradient(circle at 18% 0%, rgba(209, 244, 250, 0.54), transparent 40%), rgba(250, 250, 250, 0.88);
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

.portrait-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1240;
  background: rgba(8, 23, 51, 0.35);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.portrait-backdrop-fade-enter-active,
.portrait-backdrop-fade-leave-active {
  transition: opacity 320ms ease;
}

.portrait-backdrop-fade-enter-from,
.portrait-backdrop-fade-leave-to {
  opacity: 0;
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
}
</style>
