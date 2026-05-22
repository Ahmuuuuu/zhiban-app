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
    radial-gradient(ellipse 118% 82% at -24% 58%, rgba(255, 255, 255, 0.42) 0 34%, rgba(255, 255, 255, 0.2) 58%, transparent 86%),
    radial-gradient(ellipse 88% 62% at 14% 18%, rgba(185, 222, 249, 0.36) 0 30%, rgba(185, 222, 249, 0.14) 56%, transparent 84%),
    radial-gradient(ellipse 72% 44% at 84% 18%, rgba(255, 255, 255, 0.26) 0 28%, rgba(255, 255, 255, 0.1) 52%, transparent 78%),
    radial-gradient(ellipse 86% 38% at 48% 88%, rgba(255, 255, 255, 0.28) 0 28%, rgba(255, 255, 255, 0.12) 52%, transparent 82%),
    linear-gradient(155deg, #174d9b 0%, #438bd2 26%, #a8d7f6 62%, #f2fbff 100%);
}

.app-shell::before {
  content: "";
  position: fixed;
  left: -32vw;
  right: -20vw;
  bottom: -28vh;
  height: 68vh;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(ellipse 42% 66% at 4% 48%, rgba(255, 255, 255, 0.8) 0 34%, rgba(255, 255, 255, 0.28) 62%, transparent 88%),
    radial-gradient(ellipse 40% 70% at 24% 32%, rgba(255, 255, 255, 0.74) 0 34%, rgba(255, 255, 255, 0.24) 62%, transparent 88%),
    radial-gradient(ellipse 40% 58% at 52% 44%, rgba(255, 255, 255, 0.62) 0 32%, rgba(255, 255, 255, 0.18) 58%, transparent 86%),
    radial-gradient(ellipse 36% 62% at 76% 34%, rgba(255, 255, 255, 0.68) 0 30%, rgba(255, 255, 255, 0.2) 56%, transparent 84%),
    radial-gradient(ellipse 32% 52% at 94% 52%, rgba(255, 255, 255, 0.62) 0 28%, rgba(255, 255, 255, 0.18) 54%, transparent 82%);
  filter: blur(30px);
  opacity: 0.66;
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
