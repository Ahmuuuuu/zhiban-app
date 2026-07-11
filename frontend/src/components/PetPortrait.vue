<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { getPortrait, getUserProfile } from "../api/apis";

const portraitPromptVisible = ref(false);
const portraitChecking = ref(false);
const portraitUsername = ref("");

const getResponseData = (res: any) => res?.data ?? res ?? {};

const hasSavedPortraitTags = (portrait: any) => {
  const tags = portrait?.personality_tags;
  if (!tags) return false;
  try {
    const parsed = typeof tags === "string" ? JSON.parse(tags) : tags;
    if (Array.isArray(parsed)) return parsed.length > 0;
    if (parsed && typeof parsed === "object") {
      return Object.values(parsed).some((v) => Array.isArray(v) && v.length > 0);
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

const portraitSkipKey = () => {
  const userId = localStorage.getItem("user_id") || localStorage.getItem("token") || "anonymous";
  return `zhiban_portrait_setup_skipped_${userId}`;
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
    }
  } catch {
    await loadPortraitUsername();
    portraitPromptVisible.value = true;
  } finally {
    portraitChecking.value = false;
  }
};

const startPortraitQA = () => {
  portraitPromptVisible.value = false;
  // 通知 PetChat 进入画像问答模式
  window.dispatchEvent(new CustomEvent("zhiban-start-portrait-qa"));
};

const skipPortraitOnboarding = () => {
  localStorage.setItem(portraitSkipKey(), "1");
  portraitPromptVisible.value = false;
};

const handleLoginSuccess = () => {
  window.setTimeout(checkPortraitOnboarding, 150);
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
        class="pet-onboarding"
        @click.stop
        @pointerdown.stop
        @keydown.stop
      >
        <p>hi {{ portraitUsername }}，初次见面，我们聊一聊吧！我想更好地了解你~</p>
        <div class="pet-onboarding__actions">
          <button type="button" class="pet-onboarding__primary" @click="startPortraitQA">开始</button>
          <button type="button" class="pet-onboarding__ghost" @click="skipPortraitOnboarding">跳过</button>
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
  width: min(270px, calc(100vw - 32px));
  max-width: calc(100vw - 32px);
  padding: 14px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 18px;
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

.pet-onboarding__actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pet-onboarding__actions button {
  font: inherit;
}

.pet-onboarding__primary,
.pet-onboarding__ghost {
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
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
