<template>
  <header class="topnav">
    <div class="topnav-inner">
      <!-- Logo -->
      <router-link to="/" class="logo-area" aria-label="知伴首页">
        <div class="logo-icon"></div>
        <span class="brand">知伴</span>
      </router-link>

      <!-- 主导航 -->
      <nav class="nav-links">
        <router-link to="/" class="nav-pill" exact>首页</router-link>
        <router-link to="/chat" class="nav-pill">AI 对话</router-link>
        <router-link to="/resources" class="nav-pill" :class="{ active: isResourceSection }">资源中心</router-link>
        <router-link to="/learning-path" class="nav-pill">学习路径</router-link>
        <router-link to="/learning-situation" class="nav-pill">学习情况</router-link>
        <router-link v-if="isAdmin" to="/admin" class="nav-pill">管理后台</router-link>
      </nav>

      <section v-if="audioVisible" class="audio-control" aria-label="音频播放控制">
        <span class="audio-control__wave" :class="{ playing: narrationState.playing }"></span>
        <div class="audio-control__meta">
          <strong>{{ currentAudioTitle }}</strong>
          <span>{{ audioProgressText }}</span>
        </div>
        <button type="button" :aria-label="narrationState.playing ? '暂停音频' : '继续播放音频'" @click="toggleCurrentAudio">
          <Pause v-if="narrationState.playing" :size="15" />
          <Play v-else :size="15" />
        </button>
        <button class="audio-control__close" type="button" aria-label="关闭播放条" @click="stopCurrentAudio">
          <Square :size="13" />
        </button>
      </section>

      <!-- 右侧操作区 -->
      <div class="nav-actions">
        <button class="theme-toggle" type="button" :aria-label="themeLabel" :title="themeLabel" @click="toggleTheme">
          <Sun v-if="!isThemeDark" :size="18" />
          <Moon v-else :size="18" />
        </button>

        <router-link to="/notifications" class="bell-btn" aria-label="消息中心">
          <Bell :size="20" />
          <span v-if="unreadCount > 0" class="bell-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
        </router-link>

        <UserAccountButton
          logged-out-name="未登录"
          logged-out-meta="点击登录"
          @login="handleLogin"
        />
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Bell, Moon, Pause, Play, Square, Sun } from 'lucide-vue-next'
import UserAccountButton from './UserAccountButton.vue'
import { getUnreadNotificationCount, isBackendUnavailableError } from '../api/apis'
import { useResourceNarration } from '../composables/useResourceNarration'
import { useTheme } from '../composables/useTheme'
import { currentUserRole, isAdminRole } from '../utils/auth'

const unreadCount = ref(0)
const route = useRoute()
const userRole = ref(currentUserRole())
let pollTimer = null
let unreadRetryAt = 0
const { narrationState, toggleCurrentAudio, stopCurrentAudio } = useResourceNarration()
const { toggle: toggleTheme, isDark: isThemeDark } = useTheme()

const themeLabel = computed(() => isThemeDark.value ? '切换亮色模式' : '切换暗色模式')

const isResourceSection = computed(() => {
  return route.path === '/resources' || route.path === '/learning-resources'
})

const isAdmin = computed(() => isAdminRole(userRole.value))
const hasAuthToken = () => Boolean(localStorage.getItem('token'))

const audioVisible = computed(() => {
  return Boolean(narrationState.value.resourceId && (narrationState.value.sections.length || narrationState.value.loading))
})

const currentAudioTitle = computed(() => {
  const section = narrationState.value.sections[narrationState.value.sectionIndex]
  return section?.title || '资源讲解'
})

const formatAudioTime = seconds => {
  const total = Math.max(0, Math.floor(Number(seconds) || 0))
  const min = Math.floor(total / 60)
  const sec = String(total % 60).padStart(2, '0')
  return `${min}:${sec}`
}

const audioProgressText = computed(() => {
  if (narrationState.value.loading) return '生成中'
  const current = formatAudioTime(narrationState.value.currentTime)
  const duration = narrationState.value.duration ? formatAudioTime(narrationState.value.duration) : '--:--'
  return `${current} / ${duration}`
})

const fetchUnread = async () => {
  if (!hasAuthToken()) {
    unreadCount.value = 0
    return
  }

  if (Date.now() < unreadRetryAt) return

  try {
    const res = await getUnreadNotificationCount()
    const raw = res?.data || res || {}
    const data = raw?.data || raw
    if (typeof data.unread_count === 'number') {
      unreadCount.value = data.unread_count
    } else {
      console.warn('[TopNav] unread_count 不是数字:', typeof data.unread_count, data)
    }
  } catch (e) {
    if (isBackendUnavailableError(e)) {
      unreadRetryAt = Date.now() + 15_000
      return
    }
    console.error('[TopNav] fetchUnread 异常:', e)
  }
}

const handleLogin = () => {
  userRole.value = currentUserRole()
  window.dispatchEvent(new CustomEvent('zhiban:user-logged-in'))
}

const handleNotifRead = () => {
  fetchUnread()
}

const handleNotifUpdate = () => {
  fetchUnread()
  // 二次确认：后端 Notification.create 可能晚于 task.status 更新
  setTimeout(fetchUnread, 2000)
}

const handleUserLoggedIn = () => {
  userRole.value = currentUserRole()
  // Refresh unread count shortly after login
  setTimeout(fetchUnread, 1000)
}

const handleUserLoggedOut = () => {
  userRole.value = ''
  unreadCount.value = 0
}

onMounted(() => {
  userRole.value = currentUserRole()
  fetchUnread()
  pollTimer = setInterval(fetchUnread, 30_000)
  window.addEventListener('zhiban:notification-read', handleNotifRead)
  window.addEventListener('zhiban:notification-update', handleNotifUpdate)
  window.addEventListener('zhiban:user-logged-in', handleUserLoggedIn)
  window.addEventListener('zhiban:user-logged-out', handleUserLoggedOut)
})

onBeforeUnmount(() => {
  clearInterval(pollTimer)
  window.removeEventListener('zhiban:notification-read', handleNotifRead)
  window.removeEventListener('zhiban:notification-update', handleNotifUpdate)
  window.removeEventListener('zhiban:user-logged-in', handleUserLoggedIn)
  window.removeEventListener('zhiban:user-logged-out', handleUserLoggedOut)
})
</script>

<style scoped>
.topnav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  height: 64px;
  background: var(--color-nav-bg, #f1f7fb);
  backdrop-filter: blur(24px) saturate(155%);
  -webkit-backdrop-filter: blur(24px) saturate(155%);
  border-bottom: 1px solid var(--color-nav-border, rgba(201, 220, 233, 0.7));
  box-shadow: 0 4px 24px var(--color-shadow, rgba(20, 55, 97, 0.08));
}

.topnav-inner {
  max-width: 1400px;
  height: 100%;
  margin: 0 auto;
  padding: 0 28px;
  display: flex;
  align-items: center;
  gap: 32px;
}

/* Logo */
.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  flex-shrink: 0;
}

.logo-icon {
  width: 26px;
  height: 26px;
  border: 3px solid #143761;
  border-radius: 7px;
  transform: rotate(45deg);
  transition: transform 0.3s ease;
}

.logo-area:hover .logo-icon {
  transform: rotate(135deg);
}

.brand {
  font-size: 22px;
  font-weight: 800;
  color: #143761;
  letter-spacing: 0;
}

/* 导航链接 */
.nav-links {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  justify-content: center;
}

.nav-pill {
  min-height: 36px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  color: #5f8fc3;
  font-size: 14px;
  font-weight: 700;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  transition:
    background 0.22s ease,
    border-color 0.22s ease,
    color 0.22s ease,
    transform 0.22s ease,
    box-shadow 0.22s ease;
}

.nav-pill:hover {
  background: rgba(201, 220, 233, 0.5);
  color: #143761;
  transform: translateY(-1px);
}

.nav-pill.router-link-active,
.nav-pill.router-link-exact-active,
.nav-pill.active {
  background:
    radial-gradient(circle at 18% 10%, rgba(95, 143, 195, 0.32), transparent 45%),
    #143761;
  border-color: rgba(20, 55, 97, 0.92);
  color: #ffffff;
  box-shadow:
    0 6px 16px rgba(20, 55, 97, 0.18),
    inset 0 1px 0 rgba(250, 250, 250, 0.22);
}

.nav-pill.router-link-active:hover,
.nav-pill.router-link-exact-active:hover,
.nav-pill.active:hover {
  background:
    radial-gradient(circle at 18% 10%, rgba(255, 255, 255, 0.2), transparent 45%),
    #143761;
  border-color: rgba(20, 55, 97, 0.96);
  transform: translateY(-2px);
  box-shadow:
    0 8px 20px rgba(20, 55, 97, 0.24),
    inset 0 1px 0 rgba(250, 250, 250, 0.22);
}

.nav-pill:active {
  transform: translateY(0) scale(0.98);
  box-shadow: none;
}

/* 右侧操作区 */
.theme-toggle {
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid rgba(20, 55, 97, 0.12);
  background: rgba(255, 255, 255, 0.58);
  color: #e8a400;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease, color 0.2s ease;
  flex-shrink: 0;
}

html[data-theme="dark"] .theme-toggle {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  color: #fbbf24;
}

.theme-toggle:hover {
  background: rgba(255, 255, 255, 0.86);
  transform: translateY(-1px);
}

html[data-theme="dark"] .theme-toggle:hover {
  background: rgba(255, 255, 255, 0.14);
}

.audio-control {
  min-width: 300px;
  max-width: 430px;
  height: 42px;
  padding: 5px 7px 5px 12px;
  border: 1px solid rgba(20, 55, 97, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: #143761;
  display: flex;
  align-items: center;
  gap: 9px;
  box-shadow: 0 6px 18px rgba(20, 55, 97, 0.08);
}

.audio-control__wave {
  width: 10px;
  height: 18px;
  border-radius: 999px;
  background: #638fc2;
  box-shadow:
    6px 0 0 rgba(99, 143, 194, 0.65),
    12px 0 0 rgba(99, 143, 194, 0.35);
  transform-origin: bottom;
}

.audio-control__wave.playing {
  animation: audio-wave 0.9s ease-in-out infinite;
}

.audio-control__meta {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 1px;
}

.audio-control__meta strong,
.audio-control__meta span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audio-control__meta strong {
  font-size: 12px;
  font-weight: 850;
}

.audio-control__meta span {
  color: #638fc2;
  font-size: 11px;
  font-weight: 700;
}

.audio-control button {
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: #143761;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.audio-control button + button {
  background: rgba(20, 55, 97, 0.12);
  color: #143761;
}

.audio-control__close {
  background: rgba(20, 55, 97, 0.1) !important;
  color: #143761 !important;
}

@keyframes audio-wave {
  0%, 100% {
    transform: scaleY(0.72);
  }

  45% {
    transform: scaleY(1);
  }
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

/* 消息铃铛 */
.bell-btn {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(20, 55, 97, 0.12);
  background: rgba(255, 255, 255, 0.58);
  color: #143761;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  transition: background 0.2s ease, transform 0.2s ease;
}

.bell-btn:hover {
  background: rgba(255, 255, 255, 0.86);
  transform: translateY(-1px);
}

.bell-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #e8453c;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  line-height: 18px;
  text-align: center;
  box-shadow: 0 2px 6px rgba(232, 69, 60, 0.35);
}

/* 导航栏中的用户按钮 — 紧凑版 */
.nav-actions :deep(.account-entry) {
  min-height: 44px;
  padding: 4px 14px 4px 5px;
  gap: 8px;
  border-radius: 999px;
  box-shadow: 0 6px 18px rgba(20, 55, 97, 0.1), inset 0 1px 0 rgba(250, 250, 250, 0.7);
}

.nav-actions :deep(.account-avatar) {
  width: 34px;
  height: 34px;
}

.nav-actions :deep(.account-text strong) {
  font-size: 13px;
}

.nav-actions :deep(.account-text small) {
  font-size: 11px;
}

@media (max-width: 640px) {
  .nav-actions :deep(.account-entry) {
    min-height: 38px;
    padding: 3px 10px 3px 3px;
  }

  .nav-actions :deep(.account-avatar) {
    width: 30px;
    height: 30px;
  }

  .nav-actions :deep(.account-text) {
    display: none;
  }
}

@media (max-width: 900px) {
  .topnav-inner {
    padding: 0 16px;
    gap: 16px;
  }

  .audio-control {
    min-width: 220px;
    max-width: 300px;
  }

  .audio-control__meta strong {
    display: none;
  }

  .nav-links {
    gap: 2px;
  }

  .nav-pill {
    padding: 0 10px;
    font-size: 12px;
    min-height: 32px;
  }

  .brand {
    font-size: 18px;
  }
}

@media (max-width: 640px) {
  .topnav {
    height: 56px;
  }

  .audio-control {
    position: fixed;
    left: 12px;
    right: 12px;
    top: 56px;
    width: auto;
    min-width: 0;
    max-width: none;
    z-index: 101;
  }

  .topnav-inner {
    padding: 0 12px;
    gap: 8px;
  }

  .nav-links {
    gap: 0;
    overflow-x: auto;
    scrollbar-width: none;
    mask-image: linear-gradient(to right, transparent 0%, black 4%, black 96%, transparent 100%);
    -webkit-mask-image: linear-gradient(to right, transparent 0%, black 4%, black 96%, transparent 100%);
  }

  .nav-links::-webkit-scrollbar {
    display: none;
  }

  .nav-pill {
    padding: 0 8px;
    font-size: 11px;
    min-height: 30px;
    white-space: nowrap;
  }

  .brand {
    display: none;
  }

  .logo-icon {
    width: 22px;
    height: 22px;
  }
}
</style>
