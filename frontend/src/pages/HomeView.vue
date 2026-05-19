<template>
  <main class="home-cover">
    <FloatingHomeNav />

    <router-link class="account-corner" to="/profile" :aria-label="isLoggedIn ? '个人信息' : '登录'">
      <span class="avatar">{{ avatarText }}</span>
      <span class="account-text">
        <strong>{{ accountName }}</strong>
        <small>{{ accountRole }}</small>
      </span>
    </router-link>

    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Personal Learning Companion</p>
        <h1>知伴</h1>
        <p class="lead">
          专属于你的学习助手
        </p>

        <div class="hero-actions">
          <router-link class="primary-action" to="/chat">开始 AI 对话</router-link>
          <router-link class="secondary-action" to="/mine/resources">查看我的资源</router-link>
        </div>
      </div>

      <div class="hero-board" aria-label="首页功能预览">
        <router-link class="feature-card main-card" to="/chat">
          <div class="feature-head">
            <img src="../assets/pic/message.svg" alt="" />
            <span>AI 对话</span>
          </div>
          <p>根据你的问题、资料和画像生成学习建议。</p>
          <div class="chat-preview">
            <span>这章怎么复习？</span>
            <span>先看重点概念，再做错题归因。</span>
            <span>为你整理 3 个练习方向。</span>
          </div>
        </router-link>

        <router-link class="feature-card" to="/resources">
          <div class="feature-head">
            <img src="../assets/pic/yonghuhuaxiang.svg" alt="" />
            <span>个性化学习资源推荐</span>
          </div>
          <div class="tag-row">
            <span>兴趣匹配</span>
            <span>资源推荐</span>
            <span>重点优先</span>
          </div>
          <div class="resource-preview">
            <span>高频知识点讲义</span>
            <span>错题巩固清单</span>
          </div>
        </router-link>
      
        <router-link class="feature-card wide-card" to="/mine/path">
          <div class="feature-head">
            <img src="../assets/pic/todolist.svg" alt="" />
            <span>学习路径规划</span>
          </div>
           <div class="progress-list">
            <span>目标拆解</span>
            <span>阶段任务</span>
            <span>复盘调整</span>
          </div>
        </router-link>

         <router-link class="feature-card status-card" to="/mine/situation">
          <div class="feature-head">
            <img src="../assets/pic/xuexiqingkuang.svg" alt="" />
            <span>学习情况分析</span>
          </div>
          <div class="status-metrics">
            <span>进度追踪</span>
            <span>活跃趋势</span>
            <span>薄弱点</span>
          </div>
        </router-link>
      </div>
    </section>

    <LoginView
      :visible="showLogin"
      @close="showLogin = false"
      @login="handleLoginSuccess"
    />
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getUserProfile } from '../api/apis'
import FloatingHomeNav from '../components/FloatingHomeNav.vue'
import LoginView from '../components/LoginView.vue'

const router = useRouter()
const token = ref(localStorage.getItem('token') || '')
const username = ref(localStorage.getItem('username') || '')
const userRole = ref(localStorage.getItem('role') || localStorage.getItem('identity') || '')
const showLogin = ref(false)

const isLoggedIn = computed(() => Boolean(token.value))
const accountName = computed(() => (isLoggedIn.value ? username.value.trim() || '正在获取用户' : '请登录账户'))
const accountRole = computed(() => {
  if (!isLoggedIn.value) return '点击进入个人信息'
  if (userRole.value === 'teacher') return '教师'
  if (userRole.value === 'student') return '学生'
  return '学生'
})
const avatarText = computed(() => {
  return isLoggedIn.value ? accountName.value.slice(0, 1).toUpperCase() : '登'
})

const normalizeProfile = (result) => {
  return result?.data || result?.user || result || {}
}

const loadAccountInfo = async () => {
  if (!token.value) return

  try {
    const profile = normalizeProfile(await getUserProfile())

    if (profile.username) {
      username.value = profile.username
      localStorage.setItem('username', profile.username)
    }

    if (profile.role || profile.identity) {
      userRole.value = profile.role || profile.identity
      localStorage.setItem('role', userRole.value)
    }
  } catch (error) {
    username.value = localStorage.getItem('username') || '已登录账户'
  }
}

const openLogin = () => {
  showLogin.value = true
}

const handleLoginSuccess = async () => {
  token.value = localStorage.getItem('token') || ''
  showLogin.value = false
  await loadAccountInfo()
  await router.push('/')
}

const handleAccountClick = event => {
  if (token.value) return

  const accountEntry = event.target.closest?.('.account-corner')

  if (!accountEntry) return

  event.preventDefault()
  openLogin()
}

onMounted(() => {
  loadAccountInfo()
  document.addEventListener('click', handleAccountClick, true)
})

onUnmounted(() => {
  document.removeEventListener('click', handleAccountClick, true)
})
</script>

<style scoped>
.home-cover {
  position: relative;
  min-height: 100vh;
  background:
    radial-gradient(ellipse 118% 82% at -24% 58%, rgba(255, 255, 255, 0.42) 0 34%, rgba(255, 255, 255, 0.2) 58%, transparent 86%),
    radial-gradient(ellipse 88% 62% at 14% 18%, rgba(185, 222, 249, 0.36) 0 30%, rgba(185, 222, 249, 0.14) 56%, transparent 84%),
    radial-gradient(ellipse 72% 44% at 84% 18%, rgba(255, 255, 255, 0.26) 0 28%, rgba(255, 255, 255, 0.1) 52%, transparent 78%),
    radial-gradient(ellipse 86% 38% at 48% 88%, rgba(255, 255, 255, 0.28) 0 28%, rgba(255, 255, 255, 0.12) 52%, transparent 82%),
    linear-gradient(155deg, #174d9b 0%, #438bd2 26%, #a8d7f6 62%, #f2fbff 100%);
  color: #163f8f;
  font-family:
    Inter,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
  overflow: hidden;
}

.home-cover::before {
  content: "";
  position: fixed;
  left: -32vw;
  right: -20vw;
  bottom: -28vh;
  height: 68vh;
  pointer-events: none;
  background:
    radial-gradient(ellipse 42% 66% at 4% 48%, rgba(255, 255, 255, 0.8) 0 34%, rgba(255, 255, 255, 0.28) 62%, transparent 88%),
    radial-gradient(ellipse 40% 70% at 24% 32%, rgba(255, 255, 255, 0.74) 0 34%, rgba(255, 255, 255, 0.24) 62%, transparent 88%),
    radial-gradient(ellipse 40% 58% at 52% 44%, rgba(255, 255, 255, 0.62) 0 32%, rgba(255, 255, 255, 0.18) 58%, transparent 86%),
    radial-gradient(ellipse 36% 62% at 76% 34%, rgba(255, 255, 255, 0.68) 0 30%, rgba(255, 255, 255, 0.2) 56%, transparent 84%),
    radial-gradient(ellipse 32% 52% at 94% 52%, rgba(255, 255, 255, 0.62) 0 28%, rgba(255, 255, 255, 0.18) 54%, transparent 82%);
  filter: blur(30px);
  opacity: 0.66;
}

.primary-action,
.secondary-action,
.mini-import-btn {
  text-decoration: none;
}

.account-corner {
  position: fixed;
  top: 24px;
  right: 28px;
  z-index: 30;
  min-height: 56px;
  padding: 7px 12px 7px 7px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.62);
  background:
    radial-gradient(circle at 18% 0%, rgba(255, 255, 255, 0.88), transparent 44%),
    rgba(255, 255, 255, 0.42);
  color: #163f8f;
  text-decoration: none;
  backdrop-filter: blur(18px) saturate(135%);
  -webkit-backdrop-filter: blur(18px) saturate(135%);
  display: inline-flex;
  align-items: center;
  gap: 10px;
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.14),
    inset 0 1px 0 rgba(250, 250, 250, 0.76);
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    background 0.22s ease;
}

.account-corner:hover {
  background:
    radial-gradient(circle at 18% 0%, rgba(255, 255, 255, 0.94), transparent 44%),
    rgba(255, 255, 255, 0.62);
  transform: translateY(-2px);
  box-shadow:
    0 18px 40px rgba(22, 63, 143, 0.18),
    inset 0 1px 0 rgba(250, 250, 250, 0.8);
}

.account-corner:active {
  transform: translateY(0) scale(0.98);
}

.avatar {
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
}

.account-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.15;
  white-space: nowrap;
}

.account-text strong {
  color: #163f8f;
  font-size: 14px;
}

.account-text small {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 700;
}

.hero {
  min-height: 100vh;
  padding: 128px 7vw 54px;
  display: grid;
  grid-template-columns: minmax(320px, 0.95fr) minmax(420px, 1.05fr);
  gap: 46px;
  align-items: center;
}

.hero-copy {
  max-width: 560px;
}

.eyebrow {
  margin: 0 0 14px;
  color: #5f8fc3;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
}

.hero h1 {
  margin: 0;
  color: #163f8f;
  font-size: clamp(64px, 9vw, 118px);
  line-height: 0.92;
  letter-spacing: 0;
}

.lead {
  margin: 24px 0 0;
  color: #5f8fc3;
  font-size: 18px;
  line-height: 1.8;
}

.hero-actions {
  margin-top: 34px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.primary-action,
.secondary-action {
  position: relative;
  overflow: hidden;
  height: 46px;
  padding: 0 22px;
  border-radius: 999px;
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  font-size: 15px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    background 0.22s ease,
    border-color 0.22s ease;
}

.primary-action::after,
.secondary-action::after,
.mini-import-btn::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 0%, rgba(250, 250, 250, 0.46) 45%, transparent 70%);
  transform: translateX(-120%);
  transition: transform 0.55s ease;
}

.primary-action {
  background: rgba(255, 255, 255, 0.58);
  color: #123b86;
  border: 1px solid rgba(255, 255, 255, 0.72);
  box-shadow:
    0 16px 34px rgba(22, 63, 143, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.secondary-action {
  background: rgba(255, 255, 255, 0.42);
  color: #123b86;
  border: 1px solid rgba(255, 255, 255, 0.64);
}

.primary-action:hover,
.secondary-action:hover,
.mini-import-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 28px rgba(22, 63, 143, 0.16);
}

.primary-action:hover::after,
.secondary-action:hover::after,
.mini-import-btn:hover::after {
  transform: translateX(120%);
}

.primary-action:hover {
  background: rgba(255, 255, 255, 0.76);
  border-color: rgba(255, 255, 255, 0.92);
}

.secondary-action:hover,
.mini-import-btn:hover {
  background: rgba(255, 255, 255, 0.68);
  border-color: rgba(255, 255, 255, 0.86);
}

.primary-action:active,
.secondary-action:active,
.mini-import-btn:active {
  transform: translateY(0) scale(0.98);
  box-shadow: none;
}

.hero-board {
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.58);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(20px) saturate(145%);
  -webkit-backdrop-filter: blur(20px) saturate(145%);
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
   grid-template-rows: minmax(170px, 1fr) minmax(150px, 0.86fr) minmax(120px, auto);
  gap: 14px;
  box-shadow:
    0 24px 56px rgba(22, 63, 143, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.62);
}

.feature-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.62);
  background:
    radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.86), transparent 34%),
    rgba(255, 255, 255, 0.48);
  min-width: 0;
  color: #163f8f;
  text-decoration: none;
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    border-color 0.22s ease;
}

.feature-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.88);
  box-shadow:
    0 18px 38px rgba(22, 63, 143, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
}
.main-card {
  grid-column: 1;
  grid-row: span 2;
  background:
    radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.88), transparent 35%),
    rgba(255, 255, 255, 0.52);
}

.wide-card {
  grid-column: 1 / -1;
  grid-row: 3;
  background:
    linear-gradient(135deg, rgba(18, 59, 134, 0.84), rgba(72, 142, 211, 0.68)),
    rgba(255, 255, 255, 0.24);
  color: #ffffff;
}

.status-card {
  grid-column: 2;
  grid-row: 2;
  background:
    radial-gradient(circle at 20% 18%, rgba(255, 255, 255, 0.9), transparent 36%),
    rgba(255, 255, 255, 0.5);
}


.mini-import-btn {
  position: relative;
  overflow: hidden;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid #c9dce9;
  background: #fafafa;
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  justify-self: end;
  font-size: 13px;
  font-weight: 800;
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    background 0.22s ease;
}

.mini-import-btn:hover {
  background: #c9dce9;
}

.feature-head {
  display: flex;
  align-items: center;
  gap: 9px;
  color: inherit;
  font-size: 16px;
  font-weight: 800;
}

.feature-head img {
  width: 22px;
  height: 22px;
}

.feature-card p {
  margin: 14px 0 0;
  color: #5f8fc3;
  font-size: 14px;
  line-height: 1.7;
}

.main-card p {
  color: #163f8f;
}

.chat-preview {
  margin-top: 40px;
  display: grid;
  gap: 14px;
}

.chat-preview span,
.progress-list span {
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.66);
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
}

.chat-preview span:nth-child(2) {
  width: 78%;
  background: rgba(255, 255, 255, 0.46);
}

.chat-preview span:nth-child(3) {
  width: 58%;
}

.tag-row {
  margin-top: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-row span {
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.54);
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
}


.resource-preview {
  margin-top: 18px;
  display: grid;
  gap: 10px;
}

.resource-preview span {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.58);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.52);
  color: #5f8fc3;
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
}

.wide-card .feature-head {
  color: #fafafa;
}
.progress-list {
  margin-top: 26px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.progress-list span {
  background: rgba(255, 255, 255, 0.7);
}
.status-metrics {
  margin-top: 14px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}
.status-metrics span {
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
  color: #163f8f;
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
}
.progress-list span:nth-child(2) {
  width: auto;
}

.progress-list span:nth-child(3) {
  width: auto;
}

@media (max-width: 980px) {
  .hero {
    grid-template-columns: 1fr;
    padding-top: 154px;
  }
}

@media (max-width: 640px) {
  .account-corner {
    top: 14px;
    right: 16px;
  }

  .account-text {
    display: none;
  }

  .hero {
    padding: 150px 20px 30px;
  }

  .lead {
    font-size: 16px;
  }

   .hero-board {
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .main-card,
  .wide-card,
  .status-card {
    grid-column: auto;
    grid-row: auto;
  }

  .progress-list {
    grid-template-columns: 1fr;
  }
}
</style>
