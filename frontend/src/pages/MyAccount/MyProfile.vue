<template>
  <div class="profile-page">
    <div class="profile-container">
      <section class="profile-header">
        <div class="user-main">
          <div class="avatar-wrap">
            <img class="avatar" :src="defaultAvatar" alt="用户头像" />
            <span class="online-dot"></span>
          </div>

          <div class="user-text">
            <h2>{{ displayValue(profile.username) }}</h2>
            <p>{{ displayValue(profile.major) }}</p>
          </div>

          <div class="header-actions">
            <button class="home-btn" type="button" @click="goHome">返回首页</button>
            <button class="edit-btn" @click="toggleEdit">
            {{ isEditing ? '取消编辑' : hasProfile ? '编辑资料' : '完善资料' }}
            </button>
          </div>
        </div>
      </section>

      <section class="profile-content">
        <div class="info-card">
          <div class="card-title">
            <div>
              <h3>基本信息</h3>
              <span>Personal Information</span>
            </div>
            <p v-if="loading" class="state-text">正在加载个人信息...</p>
            <p v-else-if="!hasProfile && !isEditing" class="state-text">请完善个人信息</p>
          </div>

          <form v-if="isEditing" class="profile-form" @submit.prevent="saveProfile">
            <div class="form-item">
              <label>用户名</label>
              <input v-model="form.username" type="text" placeholder="请输入用户名" />
            </div>

            <div class="form-item">
              <label>专业</label>
              <input v-model="form.major" type="text" placeholder="请输入专业" />
            </div>

            <div class="form-item">
              <label>邮箱</label>
              <input v-model="form.email" type="email" placeholder="请输入邮箱" />
            </div>

            <div class="form-item">
              <label>手机号</label>
              <input v-model="form.phonenum" type="tel" placeholder="请输入手机号" />
            </div>

            <div class="form-item form-wide">
              <label>个人简介</label>
              <textarea v-model="form.profile" maxlength="200" placeholder="请输入个人简介"></textarea>
            </div>

            <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
            <p v-if="successMessage" class="success-message">{{ successMessage }}</p>

            <div class="form-actions">
              <button class="save-btn" type="submit" :disabled="saving">
                {{ saving ? '保存中...' : '保存资料' }}
              </button>
              <button class="cancel-btn" type="button" :disabled="saving" @click="cancelEdit">
                取消
              </button>
            </div>
          </form>

          <div v-else class="info-list">
            <div v-for="item in infoItems" :key="item.key" class="info-item">
              <span class="label">{{ item.label }}</span>
              <span class="value">{{ displayValue(profile[item.key]) }}</span>
            </div>
          </div>
        </div>

        <div class="side-card">
          <div class="account-card">
            <h3>账号状态</h3>

            <div class="status-box">
              <div>
                <strong>{{ token ? '已登录' : '未登录' }}</strong>
                <p>{{ token ? '资料已保存' : '请先登录后再完善资料' }}</p>
              </div>
              <button class="status-tag" type="button" @click="openLogin">
                {{ token ? 'Active' : 'Login' }}
              </button>
            </div>
          </div>

          <div class="quick-card">
            <button class="delete-account-btn" @click="deleteAccount">注销账户</button>
            <h3>快捷操作</h3>
            <button @click="startEdit">完善/修改资料</button>
            <button class="logout-btn" @click="logout">退出登录</button>
          </div>
        </div>
      </section>

      <LoginView
        :visible="showLogin"
        @close="showLogin = false"
        @login="handleLogin"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { deleteUser, getUserProfile, updateUserProfile } from '../../api/apis'
import LoginView from '../../components/LoginView.vue'

const router = useRouter()
const defaultAvatar = 'https://api.dicebear.com/7.x/avataaars/svg?seed=Zhiban'

const token = ref(localStorage.getItem('token') || '')
const loading = ref(false)
const saving = ref(false)
const isEditing = ref(false)
const showLogin = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const profile = reactive({
  id:'',
  username: '',
  major: '',
  email: '',
  phonenum: '',
  profile: ''
})

const form = reactive({ ...profile })

const infoItems = [
  { key: 'username', label: '用户名' },
  { key: 'major', label: '专业' },
  { key: 'email', label: '邮箱' },
  { key: 'phonenum', label: '手机号' },
  { key: 'profile', label: '个人简介' }
]

const hasProfile = computed(() => {
  return infoItems.some(item => Boolean(String(profile[item.key] || '').trim()))
})

const displayValue = (value) => {
  return String(value || '').trim() || '请完善个人信息'
}

const normalizeProfile = (result) => {
  return result?.data || result?.user || result || {}
}

const syncForm = () => {
  Object.keys(form).forEach(key => {
    form[key] = profile[key] || ''
  })
}

const fillProfile = (data) => {
  Object.keys(profile).forEach(key => {
    profile[key] = data?.[key] ?? ''
  })
  syncForm()
}

const startEdit = () => {
  successMessage.value = ''
  errorMessage.value = ''
  syncForm()
  isEditing.value = true
}

const cancelEdit = () => {
  syncForm()
  isEditing.value = false
  errorMessage.value = ''
}

const toggleEdit = () => {
  if (isEditing.value) {
    cancelEdit()
    return
  }

  startEdit()
}

const goHome = () => {
  router.push('/')
}

const buildProfilePayload = () => {
  return {
    username: form.username.trim() || null,
    major: form.major.trim() || null,
    email: form.email.trim() || null,
    phonenum: form.phonenum ? Number(form.phonenum) : null,
    profile: form.profile.trim() || null
  }
}

const loadProfile = async () => {
  if (!token.value) {
    errorMessage.value = '请先登录'
    isEditing.value = true
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const result = await getUserProfile()
    fillProfile(normalizeProfile(result))
    isEditing.value = !hasProfile.value
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.response?.data?.msg ||
      error?.message ||
      '获取个人信息失败'
    isEditing.value = true
  } finally {
    loading.value = false
  }
}

const openLogin = () => {
  if (token.value) return

  showLogin.value = true
}

const handleLogin = async () => {
  token.value = localStorage.getItem('token') || ''
  showLogin.value = false
  await router.push('/')
}

const saveProfile = async () => {
  if (!token.value) {
    errorMessage.value = '请先登录'
    return
  }

  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const payload = buildProfilePayload()
    await updateUserProfile(payload)
    const profileResult = await getUserProfile()

    fillProfile(normalizeProfile(profileResult))
    successMessage.value = '个人信息已保存'
    isEditing.value = false
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.response?.data?.msg ||
      error?.message ||
      '保存个人信息失败'
  } finally {
    saving.value = false
  }
}

const deleteAccount = async () => {
  if (!token.value) {
    errorMessage.value = '请先登录'
    return
  }

  if (!window.confirm('确认注销账户吗？此操作不可恢复。')) return

  const password = window.prompt('请输入密码确认注销账户')

  if (!password) return

  try {
    const result = await deleteUser({ password })

    if (result?.code && result.code !== 200) {
      throw new Error(result.msg || '注销账户失败')
    }

    localStorage.removeItem('token')
    localStorage.removeItem('user_id')
    router.push('/mine/resources')
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.response?.data?.msg ||
      error?.message ||
      '注销账户失败'
  }
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user_id')
  localStorage.removeItem('username')
  localStorage.removeItem('role')
  localStorage.removeItem('identity')
  router.push('/')
}

onMounted(loadProfile)
</script>

<style scoped>
.profile-page {
  position: relative;
  min-height: 100vh;
  background: #fdfcf7;
  color: #163f8f;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  padding: 26px 30px 30px;
  box-sizing: border-box;
  overflow: hidden;
}

.profile-page::before {
  content: "";
  position: fixed;
  left: -32vw;
  right: -20vw;
  bottom: -28vh;
  height: 68vh;
  pointer-events: none;
  background:
    radial-gradient(ellipse 62% 44% at 8% 12%, rgba(201, 220, 233, 0.36), transparent 68%),
    radial-gradient(ellipse 54% 36% at 84% 88%, rgba(240, 239, 221, 0.32), transparent 72%);
  filter: blur(22px);
  opacity: 0.72;
}

.profile-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: none;
  min-height: calc(100vh - 56px);
  margin: 0 auto;
}

.profile-header {
  position: relative;
  background: rgba(250, 250, 250, 0.68);
  border-radius: 28px;
  overflow: hidden;
  border: 1px solid #c9dce9;
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.1),
    inset 0 1px 0 rgba(250, 250, 250, 0.64);
  backdrop-filter: blur(18px) saturate(135%);
  -webkit-backdrop-filter: blur(18px) saturate(135%);
}

.user-main {
  position: relative;
  display: flex;
  align-items: center;
  padding: 24px 30px 28px;
  margin-top: 0;
}

.avatar-wrap {
  position: relative;
  width: 104px;
  height: 104px;
  flex-shrink: 0;
}

.avatar {
  width: 104px;
  height: 104px;
  border-radius: 22px;
  object-fit: cover;
  background: rgba(255, 255, 255, 0.66);
  border: 6px solid rgba(255, 255, 255, 0.78);
  box-shadow: 0 14px 30px rgba(22, 63, 143, 0.16);
}

.online-dot {
  position: absolute;
  right: 4px;
  bottom: 8px;
  width: 16px;
  height: 16px;
  background: #5f8fc3;
  border-radius: 50%;
  border: 4px solid rgba(255, 255, 255, 0.9);
}

.user-text {
  margin-left: 22px;
}

.user-text h2 {
  margin: 0;
  color: #163f8f;
  font-size: 28px;
  font-weight: 700;
}

.user-text p {
  margin: 8px 0 0;
  color: rgba(22, 63, 143, 0.68);
  font-size: 15px;
}

.edit-btn,
.home-btn,
.save-btn,
.cancel-btn {
  height: 42px;
  padding: 0 22px;
  border: none;
  border-radius: 28px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.edit-btn:hover,
.home-btn:hover,
.save-btn:hover,
.status-tag:hover,
.quick-card button:hover {
  background: #c9dce9;
  color: #163f8f;
  border-color: #5f8fc3;
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);
  transform: translateY(-1px);
}

.edit-btn:active,
.home-btn:active,
.save-btn:active,
.status-tag:active,
.quick-card button:active {
  transform: translateY(0);
  box-shadow: none;
}

.cancel-btn:hover {
  background: rgba(201, 220, 233, 0.68);
  color: #163f8f;
}

.header-actions {
  margin-left: auto;
  display: flex;
  gap: 12px;
  align-items: center;
}

.home-btn {
  border: 1px solid #c9dce9;
  background: #fafafa;
  color: #163f8f;
}

.edit-btn {
  border: 1px solid #163f8f;
  background: #163f8f;
  color: #ffffff;
}

.profile-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 18px;
  margin-top: 18px;
  min-height: calc(100vh - 210px);
}

.info-card,
.account-card,
.quick-card {
  background: rgba(250, 250, 250, 0.68);
  border-radius: 28px;
  border: 1px solid #c9dce9;
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(250, 250, 250, 0.64);
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
}

.info-card,
.account-card,
.quick-card {
  padding: 24px;
}

.card-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.card-title h3,
.account-card h3,
.quick-card h3 {
  margin: 0;
  color: #163f8f;
  font-size: 20px;
}

.card-title span,
.state-text {
  display: block;
  margin-top: 6px;
  color: rgba(22, 63, 143, 0.62);
  font-size: 13px;
}

.info-list,
.profile-form {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  min-height: 72px;
  padding: 16px 18px;
  border-radius: 18px;
  background: #fafafa;
  border: 1px solid #c9dce9;
  box-sizing: border-box;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.info-item:hover {
  background: #dcebf4;
  border-color: #5f8fc3;
  transform: translateY(-1px);
}

.label,
.form-item label {
  display: block;
  color: rgba(22, 63, 143, 0.62);
  font-size: 13px;
  margin-bottom: 8px;
}

.value {
  display: block;
  color: #163f8f;
  font-size: 15px;
  font-weight: 600;
}

.form-item input,
.form-item textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #c9dce9;
  border-radius: 18px;
  padding: 0 14px;
  background: #fafafa;
  color: #163f8f;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-item input:focus,
.form-item textarea:focus {
  border-color: rgba(95, 143, 195, 0.76);
  box-shadow: 0 0 0 3px rgba(95, 143, 195, 0.18);
}

.form-item input {
  height: 46px;
}

.form-item textarea {
  min-height: 92px;
  padding-top: 12px;
  resize: vertical;
}

.form-wide,
.error-message,
.success-message,
.form-actions {
  grid-column: 1 / -1;
}

.error-message,
.success-message {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.error-message {
  color: #163f8f;
}

.success-message {
  color: #5f8fc3;
}

.form-actions {
  display: flex;
  gap: 12px;
}

.save-btn {
  background: #163f8f;
  color: #ffffff;
}

.cancel-btn {
  border: 1px solid #c9dce9;
  background: #fafafa;
  color: #163f8f;
}

.side-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-box {
  margin-top: 18px;
  padding: 16px;
  border-radius: 14px;
  background: #edf5fa;
  border: 1px solid #c9dce9;
  border-left: 4px solid #163f8f;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.status-box strong {
  color: #163f8f;
  font-size: 16px;
}

.status-box p {
  margin: 6px 0 0;
  color: rgba(22, 63, 143, 0.62);
  font-size: 13px;
  line-height: 1.6;
}

.status-tag {
  height: 28px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: #163f8f;
  color: #ffffff;
  font-size: 12px;
  line-height: 28px;
  flex-shrink: 0;
  cursor: pointer;
}

.quick-card button {
  width: 100%;
  height: 42px;
  margin-top: 14px;
  border: 1px solid #c9dce9;
  border-radius: 18px;
  background: #fafafa;
  color: #163f8f;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.quick-card .logout-btn {
  background: #163f8f;
  color: #ffffff;
  border-color: #163f8f;
}

.quick-card .delete-account-btn {
  background: #fafafa;
  color: #163f8f;
  border-color: #c9dce9;
}

@media (max-width: 900px) {
  .profile-content,
  .info-list,
  .profile-form {
    grid-template-columns: 1fr;
  }

  .user-main {
    flex-wrap: wrap;
  }

  .edit-btn {
    margin-top: 18px;
    width: 100%;
  }

  .header-actions {
    margin-left: 0;
    margin-top: 18px;
    width: 100%;
  }

  .home-btn {
    flex: 1;
  }
}
</style>
