<template>
  <div class="profile-page">
    <section class="profile-header">
      <div class="avatar-wrap">
        <img class="avatar" :src="profileAvatarUrl" alt="用户头像" />
        <label class="avatar-edit" title="更换头像">
          <input type="file" accept="image/*" :disabled="avatarUploading" @change="handleAvatarChange" />
          {{ avatarUploading ? '...' : '更换' }}
        </label>
        <span class="online-dot"></span>
      </div>

      <div class="user-text">
        <h2>{{ displayValue(profile.username) }}</h2>
        <p>{{ profileSubtitle }}</p>
      </div>

      <div class="header-actions">
        <button class="edit-btn" type="button" @click="toggleEdit">
          {{ isEditing ? '取消编辑' : hasProfile ? '编辑资料' : '完善资料' }}
        </button>
      </div>
    </section>

    <section class="profile-content">
      <article class="info-card">
        <header class="card-title">
          <div>
            <h3>基本信息</h3>
            <span>Personal Information</span>
          </div>
          <p v-if="loading" class="state-text">正在加载个人信息...</p>
          <p v-else-if="!hasProfile && !isEditing" class="state-text">请完善个人信息</p>
        </header>

        <form v-if="isEditing" class="profile-form" @submit.prevent="saveProfile">
          <label class="form-item">
            <span>用户名</span>
            <input v-model.trim="form.username" type="text" placeholder="请输入用户名" />
          </label>

          <label class="form-item">
            <span>专业</span>
            <input v-model.trim="form.major" type="text" placeholder="请输入专业" />
          </label>

          <label class="form-item">
            <span>年级</span>
            <select v-model="form.grade">
              <option value="">请选择年级</option>
              <option value="大一">大一</option>
              <option value="大二">大二</option>
              <option value="大三">大三</option>
              <option value="大四">大四</option>
            </select>
          </label>

          <label class="form-item">
            <span>邮箱</span>
            <input v-model.trim="form.email" type="email" placeholder="请输入邮箱" />
          </label>

          <label class="form-item">
            <span>手机号</span>
            <input v-model.trim="form.phonenum" type="tel" inputmode="tel" placeholder="请输入手机号" />
          </label>

          <label class="form-item form-wide">
            <span>个人简介</span>
            <textarea v-model.trim="form.profile" maxlength="200" placeholder="请输入个人简介"></textarea>
          </label>

          <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
          <p v-if="successMessage" class="success-message">{{ successMessage }}</p>

          <div class="form-actions">
            <button class="save-btn" type="submit" :disabled="saving">
              {{ saving ? '保存中...' : '保存资料' }}
            </button>
            <button class="cancel-btn" type="button" :disabled="saving" @click="cancelEdit">取消</button>
          </div>
        </form>

        <div v-else class="info-list">
          <div v-for="item in infoItems" :key="item.key" class="info-item">
            <span class="label">{{ item.label }}</span>
            <span class="value">{{ displayValue(profile[item.key]) }}</span>
          </div>
        </div>
      </article>

      <aside class="side-card">
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
          <h3>快捷操作</h3>
          <button type="button" @click="startEdit">完善/修改资料</button>
          <button class="logout-btn" type="button" @click="logout">退出登录</button>
          <button class="delete-account-btn" type="button" @click="deleteAccount">注销账户</button>
        </div>
      </aside>
    </section>

    <div v-if="cropModalOpen" class="crop-backdrop" @click.self="closeAvatarCrop">
      <section class="crop-dialog" role="dialog" aria-modal="true" aria-label="裁剪头像">
        <header class="crop-title">
          <h3>裁剪头像</h3>
          <button class="crop-close" type="button" :disabled="avatarUploading" @click="closeAvatarCrop">×</button>
        </header>

        <div
          ref="cropViewport"
          class="crop-viewport"
          @pointerdown="startCropDrag"
          @pointermove="moveCropDrag"
          @pointerup="endCropDrag"
          @pointercancel="endCropDrag"
          @pointerleave="endCropDrag"
        >
          <img
            ref="cropImageEl"
            class="crop-image"
            :src="cropImageUrl"
            alt="头像裁剪预览"
            draggable="false"
            :style="cropImageStyle"
          />
          <span class="crop-circle"></span>
        </div>

        <label class="crop-zoom">
          <span>缩放</span>
          <input v-model.number="cropZoom" type="range" min="1" max="3" step="0.01" />
        </label>

        <div class="crop-actions">
          <button type="button" :disabled="avatarUploading" @click="resetAvatarCrop">重置</button>
          <button type="button" :disabled="avatarUploading" @click="closeAvatarCrop">取消</button>
          <button class="save-btn" type="button" :disabled="avatarUploading" @click="confirmAvatarCrop">
            {{ avatarUploading ? '上传中...' : '确认上传' }}
          </button>
        </div>
      </section>
    </div>

    <LoginView :visible="showLogin" @close="showLogin = false" @login="handleLogin" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  deleteUser,
  generateLearningPathsFromProfile,
  getUserProfile,
  normalizeAvatarUrl,
  updateUserProfile,
  uploadUserAvatar
} from '../../api/apis'
import LoginView from '../../components/LoginView.vue'

const router = useRouter()
const defaultAvatar = 'https://api.dicebear.com/7.x/avataaars/svg?seed=Zhiban'
const AUTO_PATH_PROFILE_KEY = 'zhiban_auto_path_profile_key'

const token = ref(localStorage.getItem('token') || '')
const loading = ref(false)
const saving = ref(false)
const avatarUploading = ref(false)
const isEditing = ref(false)
const showLogin = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const cropModalOpen = ref(false)
const cropImageUrl = ref('')
const cropFileName = ref('avatar.png')
const cropZoom = ref(1)
const cropViewport = ref(null)
const cropImageEl = ref(null)
const cropOffset = reactive({ x: 0, y: 0 })
const cropDrag = reactive({
  active: false,
  pointerId: null,
  startX: 0,
  startY: 0,
  originX: 0,
  originY: 0
})

const profile = reactive({
  id: '',
  username: '',
  major: '',
  grade: '',
  email: '',
  phonenum: '',
  profile: '',
  avatar: ''
})

const form = reactive({ ...profile })

const infoItems = [
  { key: 'username', label: '用户名' },
  { key: 'major', label: '专业' },
  { key: 'grade', label: '年级' },
  { key: 'email', label: '邮箱' },
  { key: 'phonenum', label: '手机号' },
  { key: 'profile', label: '个人简介' }
]

const hasProfile = computed(() => infoItems.some(item => Boolean(String(profile[item.key] || '').trim())))
const profileAvatarUrl = computed(() => normalizeAvatarUrl(profile.avatar) || defaultAvatar)
const profileSubtitle = computed(() => {
  const parts = [profile.major, profile.grade].map(item => String(item || '').trim()).filter(Boolean)
  return parts.length ? parts.join(' · ') : displayValue('')
})
const cropImageStyle = computed(() => ({
  transform: `translate(${cropOffset.x}px, ${cropOffset.y}px) scale(${cropZoom.value})`
}))

const displayValue = value => String(value || '').trim() || '请完善个人信息'
const normalizeProfile = result => result?.data || result?.user || result || {}

const dispatchAvatarUpdated = avatar => {
  if (avatar) {
    localStorage.setItem('avatar', avatar)
  } else {
    localStorage.removeItem('avatar')
  }
  window.dispatchEvent(new CustomEvent('zhiban:user-avatar-updated', { detail: { avatar } }))
}

const syncForm = () => {
  Object.keys(form).forEach(key => {
    form[key] = String(profile[key] ?? '')
  })
}

const fillProfile = data => {
  Object.keys(profile).forEach(key => {
    profile[key] = String(data?.[key] ?? '')
  })
  if (data?.avatar) dispatchAvatarUpdated(data.avatar)
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

const buildProfilePayload = () => ({
  username: form.username.trim() || null,
  major: form.major.trim() || null,
  grade: form.grade.trim() || null,
  email: form.email.trim() || null,
  phonenum: form.phonenum.trim() || null,
  profile: form.profile.trim() || null
})

const notifyPet = (message, duration = 5200) => {
  window.dispatchEvent(new CustomEvent('zhiban-pet-notice', {
    detail: { message, duration }
  }))
}

const unwrapApiData = result => result?.data?.data ?? result?.data ?? result

const triggerProfilePathGeneration = async previousProfile => {
  const major = String(profile.major || '').trim()
  const grade = String(profile.grade || '').trim()
  const previousMajor = String(previousProfile?.major || '').trim()
  const previousGrade = String(previousProfile?.grade || '').trim()
  const majorChanged = major !== previousMajor
  const gradeChanged = grade !== previousGrade
  const profileKey = [
    String(profile.id || localStorage.getItem('user_id') || profile.username || '').trim(),
    major,
    grade
  ].join('|')
  const hasGeneratedForProfile = localStorage.getItem(AUTO_PATH_PROFILE_KEY) === profileKey

  if (!previousProfile || !major || !grade || (!majorChanged && !gradeChanged) || hasGeneratedForProfile) return

  notifyPet(`正在根据${grade}${major}为你生成学习路径。`, 6000)

  try {
    const result = await generateLearningPathsFromProfile({ course_limit: 3 })
    const data = unwrapApiData(result) || {}
    const paths = Array.isArray(data.paths) ? data.paths : []
    const firstPath = paths[0] || null
    if (paths.length) localStorage.setItem(AUTO_PATH_PROFILE_KEY, profileKey)
    window.sessionStorage.setItem('zhiban_path_needs_refresh', '1')
    window.dispatchEvent(new CustomEvent('zhiban:path-generated', {
      detail: { path: firstPath, paths, major, grade, courses: data.courses || [] }
    }))
    notifyPet(paths.length
      ? `已按${grade}${major}生成 ${paths.length} 条学习路径，学习路径页已准备好。`
      : `已根据${grade}${major}更新学习路径。`, 7200)
  } catch (error) {
    notifyPet(error?.response?.data?.detail || error?.message || '学习路径自动生成失败，请稍后再试。', 7200)
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
  await loadProfile()
}

const saveProfile = async () => {
  if (!token.value) {
    errorMessage.value = '请先登录'
    return
  }

  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  const previousProfile = { ...profile }

  try {
    await updateUserProfile(buildProfilePayload())
    const profileResult = await getUserProfile()
    fillProfile(normalizeProfile(profileResult))
    successMessage.value = '个人信息已保存'
    isEditing.value = false
    void triggerProfilePathGeneration(previousProfile)
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

const ensureCanUploadAvatar = () => {
  if (!token.value) {
    errorMessage.value = '请先登录'
    return false
  }

  return true
}

const resetAvatarCrop = () => {
  cropZoom.value = 1
  cropOffset.x = 0
  cropOffset.y = 0
}

const revokeCropUrl = () => {
  if (cropImageUrl.value) {
    URL.revokeObjectURL(cropImageUrl.value)
  }
}

const closeAvatarCrop = () => {
  if (avatarUploading.value) return
  cropModalOpen.value = false
  revokeCropUrl()
  cropImageUrl.value = ''
  resetAvatarCrop()
}

const startCropDrag = event => {
  if (avatarUploading.value) return
  cropDrag.active = true
  cropDrag.pointerId = event.pointerId
  cropDrag.startX = event.clientX
  cropDrag.startY = event.clientY
  cropDrag.originX = cropOffset.x
  cropDrag.originY = cropOffset.y
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

const moveCropDrag = event => {
  if (!cropDrag.active || cropDrag.pointerId !== event.pointerId) return
  cropOffset.x = cropDrag.originX + event.clientX - cropDrag.startX
  cropOffset.y = cropDrag.originY + event.clientY - cropDrag.startY
}

const endCropDrag = event => {
  if (cropDrag.pointerId === event.pointerId) {
    cropDrag.active = false
    cropDrag.pointerId = null
  }
}

const cropAvatarToFile = () => new Promise((resolve, reject) => {
  const image = cropImageEl.value
  const viewport = cropViewport.value
  if (!image || !viewport || !image.naturalWidth || !image.naturalHeight) {
    reject(new Error('头像图片还没有加载完成'))
    return
  }

  const size = 512
  const rect = viewport.getBoundingClientRect()
  const viewWidth = rect.width
  const viewHeight = rect.height
  const baseScale = Math.max(viewWidth / image.naturalWidth, viewHeight / image.naturalHeight)
  const scale = baseScale * cropZoom.value
  const renderedWidth = image.naturalWidth * scale
  const renderedHeight = image.naturalHeight * scale
  const left = (viewWidth - renderedWidth) / 2 + cropOffset.x
  const top = (viewHeight - renderedHeight) / 2 + cropOffset.y
  const sourceX = Math.max(0, -left / scale)
  const sourceY = Math.max(0, -top / scale)
  const sourceWidth = Math.min(image.naturalWidth - sourceX, viewWidth / scale)
  const sourceHeight = Math.min(image.naturalHeight - sourceY, viewHeight / scale)
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, size, size)
  ctx.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, size, size)

  canvas.toBlob(blob => {
    if (!blob) {
      reject(new Error('头像裁剪失败'))
      return
    }

    resolve(new File([blob], cropFileName.value.replace(/\.\w+$/, '') + '.png', { type: 'image/png' }))
  }, 'image/png', 0.92)
})

const uploadAvatarFile = async file => {
  avatarUploading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const result = await uploadUserAvatar(file)
    const data = result?.data || result || {}
    const avatar = data.avatar || data.user?.avatar || ''
    if (avatar) {
      profile.avatar = avatar
      dispatchAvatarUpdated(avatar)
    } else {
      const profileResult = await getUserProfile()
      fillProfile(normalizeProfile(profileResult))
    }
    successMessage.value = '头像已更新'
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.detail ||
      error?.response?.data?.msg ||
      error?.message ||
      '头像上传失败'
  } finally {
    avatarUploading.value = false
  }
}

const confirmAvatarCrop = async () => {
  if (!ensureCanUploadAvatar()) return

  try {
    const croppedFile = await cropAvatarToFile()
    await uploadAvatarFile(croppedFile)
    cropModalOpen.value = false
    revokeCropUrl()
    cropImageUrl.value = ''
    resetAvatarCrop()
  } catch (error) {
    errorMessage.value = error?.message || '头像裁剪失败'
  }
}

const handleAvatarChange = event => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || avatarUploading.value) return
  if (!ensureCanUploadAvatar()) return
  if (!file.type.startsWith('image/')) {
    errorMessage.value = '请选择图片文件'
    return
  }

  revokeCropUrl()
  cropFileName.value = file.name || 'avatar.png'
  cropImageUrl.value = URL.createObjectURL(file)
  resetAvatarCrop()
  cropModalOpen.value = true
  errorMessage.value = ''
  successMessage.value = ''
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
    localStorage.removeItem('avatar')
    router.push('/learning-resources')
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
  localStorage.removeItem('avatar')
  localStorage.removeItem('zhiban_generation_tasks_v2')
  dispatchAvatarUpdated('')
  window.dispatchEvent(new CustomEvent('zhiban:user-logged-out'))
  router.push('/')
}

onMounted(loadProfile)
onBeforeUnmount(revokeCropUrl)
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  padding: 26px 30px 30px;
  background: #fdfcf7;
  color: #163f8f;
  font-family: "Open Sans", "PingFang SC", "Microsoft YaHei", sans-serif;
  box-sizing: border-box;
}

.profile-header,
.info-card,
.side-card > div {
  border: 1px solid #c9dce9;
  border-radius: 28px;
  background: rgba(250, 250, 250, 0.78);
  box-shadow: 0 14px 34px rgba(22, 63, 143, 0.1);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 24px 30px;
}

.avatar-wrap {
  position: relative;
  width: 104px;
  height: 104px;
  flex-shrink: 0;
}

.avatar-edit {
  position: absolute;
  left: 50%;
  bottom: 8px;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(22, 63, 143, 0.9);
  color: #fff;
  font-size: 12px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  transform: translateX(-50%);
  cursor: pointer;
}

.avatar-edit input {
  display: none;
}

.avatar {
  width: 100%;
  height: 100%;
  border: 6px solid rgba(255, 255, 255, 0.78);
  border-radius: 22px;
  object-fit: cover;
  background: #fff;
}

.online-dot {
  position: absolute;
  right: 4px;
  bottom: 8px;
  width: 16px;
  height: 16px;
  border: 4px solid #fff;
  border-radius: 50%;
  background: #5f8fc3;
}

.user-text {
  min-width: 0;
  flex: 1;
}

.user-text h2,
.user-text p,
.card-title h3,
.side-card h3 {
  margin: 0;
}

.user-text h2 {
  font-size: 28px;
}

.user-text p,
.card-title span,
.state-text,
.status-box p {
  color: #5f8fc3;
}

.header-actions,
.form-actions {
  display: flex;
  gap: 10px;
}

button {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid #c9dce9;
  border-radius: 18px;
  background: #fff;
  color: #163f8f;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.edit-btn,
.save-btn,
.status-tag {
  background: #163f8f;
  color: #fff;
}

.profile-content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 18px;
  margin-top: 18px;
}

.info-card,
.side-card > div {
  padding: 24px;
}

.side-card {
  display: grid;
  gap: 18px;
  align-content: start;
}

.card-title,
.status-box,
.info-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.profile-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 20px;
}

.form-item {
  display: grid;
  gap: 8px;
  font-weight: 800;
}

.form-wide,
.error-message,
.success-message,
.form-actions {
  grid-column: 1 / -1;
}

input,
select,
textarea {
  width: 100%;
  border: 1px solid #c9dce9;
  border-radius: 16px;
  background: #fff;
  color: #163f8f;
  font: inherit;
  box-sizing: border-box;
}

input {
  height: 44px;
  padding: 0 14px;
}

select {
  height: 44px;
  padding: 0 14px;
}

textarea {
  min-height: 116px;
  padding: 12px 14px;
  resize: vertical;
}

.info-list {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}

.info-item {
  min-height: 48px;
  padding: 0 16px;
  border-radius: 18px;
  background: rgba(237, 249, 252, 0.72);
}

.label {
  color: #5f8fc3;
  font-weight: 800;
}

.value {
  text-align: right;
}

.quick-card {
  display: grid;
  gap: 10px;
}

.delete-account-btn {
  color: #b24141;
}

.error-message {
  color: #b24141;
}

.success-message {
  color: #2f7d57;
}

.crop-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  padding: 24px;
  background: rgba(8, 24, 55, 0.42);
  display: grid;
  place-items: center;
}

.crop-dialog {
  width: min(92vw, 420px);
  padding: 20px;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(22, 63, 143, 0.24);
}

.crop-title,
.crop-actions,
.crop-zoom {
  display: flex;
  align-items: center;
  gap: 10px;
}

.crop-title {
  justify-content: space-between;
  margin-bottom: 14px;
}

.crop-title h3 {
  margin: 0;
  font-size: 18px;
}

.crop-close {
  width: 34px;
  min-height: 34px;
  padding: 0;
  border-radius: 50%;
  font-size: 20px;
}

.crop-viewport {
  position: relative;
  width: min(72vw, 300px);
  aspect-ratio: 1;
  margin: 0 auto;
  overflow: hidden;
  border-radius: 8px;
  background: #edf6fa;
  touch-action: none;
  cursor: grab;
}

.crop-viewport:active {
  cursor: grabbing;
}

.crop-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform-origin: center;
  user-select: none;
  pointer-events: none;
}

.crop-circle {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(255, 255, 255, 0.95);
  border-radius: 50%;
  box-shadow: 0 0 0 999px rgba(8, 24, 55, 0.24);
  pointer-events: none;
}

.crop-zoom {
  margin: 16px 0;
  font-weight: 800;
}

.crop-zoom input {
  height: auto;
  padding: 0;
}

.crop-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .profile-header,
  .profile-content,
  .profile-form {
    grid-template-columns: 1fr;
  }

  .profile-header {
    flex-wrap: wrap;
  }
}
</style>
