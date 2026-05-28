<template>
  <header class="floating-nav" :class="{ 'entering-chat': enteringChat }">
    <nav class="nav-links">
      <a href="#/chat" @click.prevent="goChat">ai对话</a>
      <router-link to="/resources">资源中心</router-link>
      <router-link to="/learning-resources">我的资源</router-link>
      <router-link to="/learning-path">学习路径</router-link>
      <router-link to="/learning-situation">学习情况</router-link>
    </nav>

  </header>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
const enteringChat = ref(false)

const goChat = () => {
  if (enteringChat.value) return

  enteringChat.value = true
  window.setTimeout(() => {
    router.push('/chat')
  }, 720)
}

watch(
  () => route.path,
  path => {
    if (path === '/') {
      enteringChat.value = false
    }
  }
)
</script>

<style scoped>
.floating-nav {
  position: fixed;
  top: 22px;
  left: 28px;
  z-index: 20;
  width: min(760px, calc(100% - 56px));
  max-width: calc(100% - 40px);
  min-height: 62px;
  padding: 10px 8px;
  transform: none;
  border: 1px solid rgba(255, 255, 255, 0.58);
  border-radius: 999px;
  background:
    radial-gradient(circle at 18% 0%, rgba(255, 255, 255, 0.82), transparent 42%),
    rgba(255, 255, 255, 0.36);
  backdrop-filter: blur(24px) saturate(155%);
  -webkit-backdrop-filter: blur(24px) saturate(155%);
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow:
    0 20px 46px rgba(22, 63, 143, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.74);
  transform-origin: left top;
  transition:
    transform 0.48s cubic-bezier(0.22, 1, 0.36, 1),
    width 0.96s cubic-bezier(0.22, 1, 0.36, 1),
    padding 0.96s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.48s ease;
}

.floating-nav.entering-chat {
  width: 108px;
  transform: none;
  padding: 10px 12px;
  box-shadow:
    0 18px 40px rgba(22, 63, 143, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.76);
}

.floating-nav.entering-chat .nav-links {
  display: grid;
  gap: 0;
}

.floating-nav.entering-chat .nav-links a {
  grid-area: 1 / 1;
  justify-self: start;
  min-width: 82px;
  justify-content: center;
}

.floating-nav.entering-chat .nav-links a:first-child {
  position: relative;
  z-index: 3;
  transform: none;
  background:
    radial-gradient(circle at 18% 10%, rgba(95, 143, 195, 0.34), transparent 45%),
    rgba(10, 38, 92, 0.9);
  box-shadow:
    0 12px 24px rgba(10, 38, 92, 0.24),
    inset 0 1px 0 rgba(250, 250, 250, 0.2);
}

.floating-nav.entering-chat .nav-links a:nth-child(2) {
  z-index: 2;
  opacity: 0.58;
  transform: translateY(9px) scale(0.94);
}

.floating-nav.entering-chat .nav-links a:nth-child(3) {
  z-index: 1;
  opacity: 0.36;
  transform: translateY(17px) scale(0.88);
}

.floating-nav.entering-chat .nav-links a:nth-child(n + 4) {
  opacity: 0;
  pointer-events: none;
}

.nav-links a {
  text-decoration: none;
}

.nav-links {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-evenly;
  gap: 0;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-links::-webkit-scrollbar {
  display: none;
}

.nav-links a {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(22, 63, 143, 0.92);
  background:
    radial-gradient(circle at 18% 10%, rgba(95, 143, 195, 0.32), transparent 45%),
    #163f8f;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  backdrop-filter: blur(12px) saturate(135%);
  -webkit-backdrop-filter: blur(12px) saturate(135%);
  transition:
    background 0.22s ease,
    border-color 0.22s ease,
    transform 0.96s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.22s ease,
    opacity 0.96s ease;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  background:
    radial-gradient(circle at 18% 10%, rgba(255, 255, 255, 0.2), transparent 45%),
    #1a4da8;
  border-color: rgba(22, 63, 143, 0.96);
  transform: translateY(-2px);
  box-shadow:
    0 8px 18px rgba(10, 38, 92, 0.24),
    inset 0 1px 0 rgba(250, 250, 250, 0.22);
}

.nav-links a:active {
  transform: translateY(0) scale(0.98);
  box-shadow: none;
}

@media (max-width: 980px) {
  .floating-nav {
    width: min-content;
    max-width: calc(100% - 40px);
  }

  .nav-links {
    grid-column: 1 / -1;
    justify-content: flex-start;
    overflow-x: auto;
  }
}

@media (max-width: 640px) {
  .floating-nav {
    top: 12px;
    left: 12px;
    width: calc(100% - 24px);
  }

}
</style>
