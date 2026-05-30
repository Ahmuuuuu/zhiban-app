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
        <router-link to="/resources" class="nav-pill">资源中心</router-link>
        <router-link to="/learning-path" class="nav-pill">学习路径</router-link>
        <router-link to="/learning-situation" class="nav-pill">学习情况</router-link>
      </nav>

      <!-- 右侧操作区 -->
      <div class="nav-actions">
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
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { Bell } from 'lucide-vue-next'
import UserAccountButton from './UserAccountButton.vue'
import { getUnreadNotificationCount } from '../api/apis'

const unreadCount = ref(0)
let pollTimer = null

const fetchUnread = async () => {
  try {
    const res = await getUnreadNotificationCount()
    const data = res?.data || res || {}
    if (typeof data.unread_count === 'number') {
      unreadCount.value = data.unread_count
    }
  } catch { /* backend may not be ready yet */ }
}

const handleLogin = () => {
  window.dispatchEvent(new CustomEvent('zhiban:user-logged-in'))
}

const handleNotifRead = () => {
  fetchUnread()
}

onMounted(() => {
  fetchUnread()
  pollTimer = setInterval(fetchUnread, 30_000)
  window.addEventListener('zhiban:notification-read', handleNotifRead)
  window.addEventListener('zhiban:notification-update', () => {
    fetchUnread()
  })
  window.addEventListener('zhiban:user-logged-in', () => {
    // Refresh unread count shortly after login
    setTimeout(fetchUnread, 1000)
  })
})

onBeforeUnmount(() => {
  clearInterval(pollTimer)
  window.removeEventListener('zhiban:notification-read', handleNotifRead)
  window.removeEventListener('zhiban:notification-update', fetchUnread)
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
  background: #f1f7fb;
  backdrop-filter: blur(24px) saturate(155%);
  -webkit-backdrop-filter: blur(24px) saturate(155%);
  border-bottom: 1px solid rgba(201, 220, 233, 0.7);
  box-shadow: 0 4px 24px rgba(20, 55, 97, 0.08);
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
.nav-pill.router-link-exact-active {
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
.nav-pill.router-link-exact-active:hover {
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
