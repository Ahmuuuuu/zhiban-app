<template>
  <div class="app-shell">
    <Transition name="page-fade" mode="out-in">
      <div v-if="isHomeChatRoute" key="home-chat" class="home-chat-shell">
        <div
          class="route-slide-track"
          :class="{ 'show-chat': route.path === '/chat' }"
        >
          <section class="route-slide-pane">
            <HomeView />
          </section>
          <section class="route-slide-pane">
            <ChatView v-if="showChatPane" />
          </section>
        </div>
      </div>

      <RouterView v-else v-slot="{ Component }" :key="pageShellKey">
        <div class="page-transition-shell">
          <component :is="Component" />
        </div>
      </RouterView>
    </Transition>
  </div>

  <StudyPet floating auto-play-actions />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import HomeView from './pages/HomeView.vue'
import ChatView from './pages/ChatView.vue'
import StudyPet from './components/StudyPet.vue'

const route = useRoute()
const keepChatPane = ref(route.path === '/chat')
const isHomeChatRoute = computed(() => route.path === '/' || route.path === '/chat')
const showChatPane = computed(() => route.path === '/chat' || keepChatPane.value)
const pageShellKey = computed(() => route.matched[0]?.path || route.path)

watch(
  () => route.path,
  (to, from) => {
    if (to === '/chat') {
      keepChatPane.value = true
      return
    }

    if (from === '/chat' && to === '/') {
      window.setTimeout(() => {
        if (route.path === '/') keepChatPane.value = false
      }, 760)
      return
    }

    if (to !== '/chat') {
      keepChatPane.value = false
    }
  },
  { flush: 'sync' }
)
</script>

<style>
.app-shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(ellipse 72% 44% at 10% 0%, rgba(209, 244, 250, 0.46), transparent 70%),
    linear-gradient(135deg, #fafafa 0%, rgb(237, 249, 252) 52%, #fafafa 100%);
}

.app-shell::before {
  display: none;
}

.home-chat-shell,
.route-slide-pane,
.page-transition-shell,
.home-cover,
.chat-page,
.my-full-page,
.question-bank-page,
.quiz-runner-page,
.profile-page,
.resource-center-page,
.resource-page,
.import-page,
.study-panel {
  background:
    radial-gradient(ellipse 72% 44% at 10% 0%, rgba(209, 244, 250, 0.46), transparent 70%),
    linear-gradient(135deg, #fafafa 0%, rgb(237, 249, 252) 52%, #fafafa 100%) !important;
}

.app-shell > * {
  position: relative;
  z-index: 1;
}

.route-slide-track {
  position: relative;
  z-index: 1;
  width: 200vw;
  height: 100vh;
  display: flex;
  transform: translateX(0);
  transition: transform 1.08s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}

.route-slide-track.show-chat {
  transform: translateX(-100vw);
}

.route-slide-pane {
  width: 100vw;
  height: 100vh;
  flex: 0 0 100vw;
  overflow: hidden;
}

.home-chat-shell {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  transform-origin: 50% 46%;
  will-change: opacity, transform, filter;
}

.page-transition-shell {
  min-height: 100vh;
  transform-origin: 50% 46%;
  will-change: opacity, transform, filter;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition:
    opacity 0.42s ease,
    transform 0.52s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.42s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(28px) scale(0.975);
  filter: blur(8px);
}

.page-fade-enter-to,
.page-fade-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
  filter: blur(0);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-18px) scale(0.985);
  filter: blur(6px);
}

@media (prefers-reduced-motion: reduce) {
  .route-slide-track,
  .page-fade-enter-active,
  .page-fade-leave-active {
    transition: none;
  }

  .page-fade-enter-from,
  .page-fade-leave-to {
    opacity: 1;
    transform: none;
    filter: none;
  }
}

</style>
