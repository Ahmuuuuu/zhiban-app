<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getPortrait } from "../api/apis";

const router = useRouter();

const portraitPromptVisible = ref(false);
const portraitChecking = ref(false);

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
      return Object.values(parsed).some(
        (v: any) => Array.isArray(v) && v.length > 0,
      );
    }
  } catch {
    return String(tags).trim().length > 0;
  }
  return false;
};

const checkPortraitOnboarding = async () => {
  if (portraitChecking.value || !localStorage.getItem("token")) return;
  if (localStorage.getItem(portraitSkipKey()) === "1") return;

  portraitChecking.value = true;
  try {
    const portrait = getResponseData(await getPortrait());
    if (!hasSavedPortraitTags(portrait)) {
      portraitPromptVisible.value = true;
    }
  } catch {
    portraitPromptVisible.value = true;
  } finally {
    portraitChecking.value = false;
  }
};

const goToChat = () => {
  portraitPromptVisible.value = false;
  router.push("/chat");
};

const skipPortraitOnboarding = () => {
  localStorage.setItem(portraitSkipKey(), "1");
  portraitPromptVisible.value = false;
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
  <Teleport to="body">
    <Transition name="pet-onboarding-pop">
      <section
        v-if="portraitPromptVisible"
        class="pet-onboarding pet-onboarding--chat"
        @click.stop
        @pointerdown.stop
        @keydown.stop
      >
        <div class="pet-onboarding__avatar">
          <span class="pet-onboarding__pet-icon">✦</span>
        </div>
        <p>来和我对话让我认识一下你，开启更加个性化的学习之旅</p>
        <div class="pet-onboarding__actions">
          <button type="button" class="pet-onboarding__primary" @click="goToChat">
            去对话
          </button>
          <button type="button" class="pet-onboarding__ghost" @click="skipPortraitOnboarding">
            以后再说
          </button>
        </div>
      </section>
    </Transition>
  </Teleport>
</template>

<style scoped>
.pet-onboarding {
  position: fixed;
  right: 142px;
  bottom: 176px;
  z-index: 1245;
  width: min(290px, calc(100vw - 32px));
  max-width: calc(100vw - 32px);
  padding: 18px 16px 14px;
  border: 1px solid rgba(22, 63, 143, 0.12);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 22px 58px rgba(22, 63, 143, 0.18);
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
  cursor: default;
  pointer-events: auto;
  box-sizing: border-box;
}

.pet-onboarding::after {
  content: "";
  position: absolute;
  right: 28px;
  bottom: -9px;
  width: 18px;
  height: 18px;
  border-right: 1px solid rgba(22, 63, 143, 0.12);
  border-bottom: 1px solid rgba(22, 63, 143, 0.12);
  background: rgba(255, 255, 255, 0.96);
  transform: rotate(45deg);
}

.pet-onboarding__avatar {
  display: flex;
  margin-bottom: 8px;
}

.pet-onboarding__pet-icon {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #163f8f, #5f8fc3);
  color: #fff;
  display: inline-grid;
  place-items: center;
  font-size: 16px;
}

.pet-onboarding p {
  margin: 0 0 12px;
  color: #163f8f;
  font-size: 14px;
  line-height: 1.65;
  font-weight: 700;
}

.pet-onboarding__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pet-onboarding__actions button {
  font: inherit;
}

.pet-onboarding__primary,
.pet-onboarding__ghost {
  min-height: 32px;
  padding: 0 16px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.pet-onboarding__primary:hover,
.pet-onboarding__ghost:hover {
  transform: translateY(-1px);
}

.pet-onboarding__primary {
  border: 1px solid #163f8f;
  background: #163f8f;
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(22, 63, 143, 0.2);
}

.pet-onboarding__ghost {
  border: 1px solid rgba(201, 220, 233, 0.82);
  background: #ffffff;
  color: #163f8f;
}

/* dark mode */
html[data-theme="dark"] .pet-onboarding {
  background: #1a2535 !important;
  border-color: #2a3546 !important;
}

html[data-theme="dark"] .pet-onboarding::after {
  border-right-color: #2a3546 !important;
  border-bottom-color: #2a3546 !important;
  background: #1a2535 !important;
}

html[data-theme="dark"] .pet-onboarding p {
  color: #c8d6e5 !important;
}

html[data-theme="dark"] .pet-onboarding__primary {
  background: #2f6b2f !important;
  border-color: #3d8f56 !important;
}

html[data-theme="dark"] .pet-onboarding__ghost {
  background: #1a2535 !important;
  border-color: #2a3546 !important;
  color: #c8d6e5 !important;
}

/* animations */
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

@media (max-width: 720px) {
  .pet-onboarding {
    position: fixed;
    left: 16px;
    right: 16px;
    bottom: 212px;
    width: auto;
  }

  .pet-onboarding::after {
    right: 54px;
  }
}
</style>
