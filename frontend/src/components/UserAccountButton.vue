<template>
  <div :class="['account-entry-wrap', { corner }]">
    <button
      type="button"
      :class="['account-entry', variant]"
      :aria-label="isLoggedIn ? '个人信息' : '登录'"
      @click="handleClick"
    >
      <span class="account-avatar">
        <img v-if="avatarUrl" :src="avatarUrl" alt="" />
        <span v-else>{{ avatarText }}</span>
      </span>
      <span class="account-text">
        <strong>{{ accountName }}</strong>
        <small>{{ accountMeta }}</small>
      </span>
    </button>

    <LoginView
      :visible="showLogin"
      @close="showLogin = false"
      @login="handleLoginSuccess"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getUserProfile, normalizeAvatarUrl } from '../api/apis'
import { isAdminRole } from '../utils/auth'
import LoginView from './LoginView.vue'

const props = defineProps({
  variant: { type: String, default: 'glass' },
  corner: { type: Boolean, default: false },
  metaType: { type: String, default: 'role' },
  loggedOutName: { type: String, default: '请登录账户' },
  loggedOutMeta: { type: String, default: '点击登录' }
})

const emit = defineEmits(['login'])

const router = useRouter()
const token = ref(localStorage.getItem('token') || '')
const username = ref(localStorage.getItem('username') || '')
const userRole = ref(localStorage.getItem('role') || localStorage.getItem('identity') || '')
const major = ref('')
const avatarUrl = ref(normalizeAvatarUrl(localStorage.getItem('avatar') || ''))
const showLogin = ref(false)

const isLoggedIn = computed(() => Boolean(token.value))
const accountName = computed(() => {
  return isLoggedIn.value ? username.value.trim() || '正在获取用户' : props.loggedOutName
})
const accountMeta = computed(() => {
  if (!isLoggedIn.value) return props.loggedOutMeta

  if (props.metaType === 'major') {
    return major.value || '暂未填写专业'
  }

  if (userRole.value === 'teacher') return '教师'
  if (userRole.value === 'student') return '学生'
  if (isAdminRole(userRole.value)) return '管理员'
  return '学生'
})
const avatarText = computed(() => {
  return isLoggedIn.value ? accountName.value.slice(0, 1).toUpperCase() : '登'
})

const normalizeProfile = result => {
  return result?.data || result?.user || result || {}
}

const loadAccountInfo = async () => {
  token.value = localStorage.getItem('token') || ''

  if (!token.value) {
    username.value = ''
    userRole.value = ''
    major.value = ''
    avatarUrl.value = ''
    return
  }

  try {
    const profile = normalizeProfile(await getUserProfile())

    username.value = profile.username || localStorage.getItem('username') || '已登录账户'
    userRole.value = profile.role || profile.identity || localStorage.getItem('role') || ''
    major.value = profile.major || ''
    avatarUrl.value = normalizeAvatarUrl(profile.avatar || localStorage.getItem('avatar') || '')

    if (profile.username) {
      localStorage.setItem('username', profile.username)
    }

    if (profile.role || profile.identity) {
      localStorage.setItem('role', profile.role || profile.identity)
    }
    if (profile.avatar) {
      localStorage.setItem('avatar', profile.avatar)
    }
  } catch (error) {
    username.value = localStorage.getItem('username') || '已登录账户'
  }
}

const handleClick = async () => {
  if (!isLoggedIn.value) {
    showLogin.value = true
    return
  }

  await router.push('/profile')
}

const handleLoginSuccess = async () => {
  showLogin.value = false
  await loadAccountInfo()
  emit('login')
  if (isAdminRole(userRole.value)) {
    await router.push('/admin')
  }
}

const handleAvatarUpdated = event => {
  avatarUrl.value = normalizeAvatarUrl(event?.detail?.avatar || localStorage.getItem('avatar') || '')
}

const handleLogout = () => {
  token.value = ''
  username.value = ''
  userRole.value = ''
  major.value = ''
  avatarUrl.value = ''
}

onMounted(() => {
  window.addEventListener('zhiban:user-avatar-updated', handleAvatarUpdated)
  window.addEventListener('zhiban:user-logged-out', handleLogout)
  loadAccountInfo()
})

onBeforeUnmount(() => {
  window.removeEventListener('zhiban:user-avatar-updated', handleAvatarUpdated)
  window.removeEventListener('zhiban:user-logged-out', handleLogout)
})
</script>

<style scoped>
.account-entry-wrap {
  display: inline-flex;
}

.account-entry-wrap.corner {
  position: absolute;
  top: 24px;
  right: 28px;
  z-index: 120;
}

.account-entry {
  min-height: 56px;
  padding: 7px 12px 7px 7px;
  border-radius: 999px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  background: rgba(250, 250, 250, 0.72);
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
  font: inherit;
  text-decoration: none;
  backdrop-filter: blur(18px) saturate(135%);
  -webkit-backdrop-filter: blur(18px) saturate(135%);
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.14),
    inset 0 1px 0 rgba(250, 250, 250, 0.76);
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    background 0.22s ease,
    border-color 0.22s ease;
}

.account-entry:hover {
  background: rgba(250, 250, 250, 0.86);
  transform: translateY(-2px);
  box-shadow:
    0 18px 40px rgba(22, 63, 143, 0.18),
    inset 0 1px 0 rgba(250, 250, 250, 0.8);
}

.account-entry:active {
  transform: translateY(0) scale(0.98);
}

.account-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #163f8f;
  color: #fafafa;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  flex-shrink: 0;
  overflow: hidden;
}

.account-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.account-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.15;
  text-align: left;
  white-space: nowrap;
}

.account-text strong {
  max-width: 96px;
  overflow: hidden;
  color: #163f8f;
  font-size: 14px;
  text-overflow: ellipsis;
}

.account-text small {
  max-width: 118px;
  overflow: hidden;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 700;
  text-overflow: ellipsis;
}

.account-entry.home {
  border-color: rgba(255, 255, 255, 0.62);
  background:
    radial-gradient(circle at 18% 0%, rgba(255, 255, 255, 0.88), transparent 44%),
    rgba(255, 255, 255, 0.42);
}

.account-entry.home:hover {
  background:
    radial-gradient(circle at 18% 0%, rgba(255, 255, 255, 0.94), transparent 44%),
    rgba(255, 255, 255, 0.62);
}

.account-entry.dark {
  min-width: 132px;
  height: 70px;
  padding: 0 20px;
  border-color: rgba(22, 63, 143, 0.92);
  background: #163f8f;
  color: #fafafa;
  box-shadow:
    0 14px 30px rgba(22, 63, 143, 0.18),
    inset 0 1px 0 rgba(250, 250, 250, 0.18);
}

.account-entry.dark:hover {
  background: #1d5dab;
  border-color: #1d5dab;
}

.account-entry.dark .account-avatar {
  width: 38px;
  height: 38px;
  background: rgba(250, 250, 250, 0.96);
  color: #163f8f;
  font-size: 15px;
}

.account-entry.dark .account-text {
  align-items: center;
  justify-content: center;
  text-align: center;
}

.account-entry.dark .account-text strong,
.account-entry.dark .account-text small {
  max-width: 84px;
}

.account-entry.dark .account-text strong {
  color: #fafafa;
}

.account-entry.dark .account-text small {
  color: rgba(250, 250, 250, 0.78);
}

@media (max-width: 640px) {
  .account-entry-wrap.corner {
    top: 14px;
    right: 16px;
  }

  .account-text {
    display: none;
  }
}
</style>
