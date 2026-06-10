<template>
  <main class="admin-page">
    <header class="admin-header">
      <div>
        <span class="eyebrow">Admin Console</span>
        <h1>管理员工作台</h1>
      </div>
      <button class="icon-button" type="button" title="刷新" :disabled="loading" @click="refreshAll">
        <RefreshCw :size="18" :class="{ spinning: loading }" />
      </button>
    </header>

    <section class="metric-row" aria-label="管理概览">
      <article class="metric">
        <span>待审核</span>
        <strong>{{ pendingResources.length }}</strong>
      </article>
      <article class="metric">
        <span>资源总数</span>
        <strong>{{ managedResources.length }}</strong>
      </article>
      <article class="metric">
        <span>基础资源</span>
        <strong>{{ knowledgeBase.length }}</strong>
      </article>
      <article class="metric">
        <span>用户数</span>
        <strong>{{ users.length }}</strong>
      </article>
    </section>

    <p v-if="errorMessage" class="notice">
      <AlertCircle :size="17" />
      {{ errorMessage }}
    </p>
    <p v-if="successMessage" class="notice success">
      <CheckCircle2 :size="17" />
      {{ successMessage }}
    </p>

    <section class="workspace">
      <aside class="admin-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <component :is="tab.icon" :size="17" />
          <span>{{ tab.label }}</span>
          <small v-if="tab.count !== null">{{ tab.count }}</small>
        </button>
      </aside>

      <section v-if="activeTab === 'review'" class="panel">
        <div class="panel-head">
          <div>
            <h2>公开资源申请</h2>
            <p>审核用户提交到资源中心的公开资源申请。</p>
          </div>
        </div>

        <div v-if="loadingReview" class="empty-line">正在加载待审核资源...</div>
        <div v-else-if="!pendingResources.length" class="empty-line">当前没有待审核申请。</div>

        <article v-for="resource in pendingResources" :key="resource.id" class="review-item">
          <div class="resource-main">
            <span class="type-chip">{{ resource.typeLabel }}</span>
            <h3>{{ resource.title }}</h3>
            <p>{{ resource.excerpt }}</p>
            <div class="meta-line">
              <span>申请人：{{ resource.ownerName || '未知用户' }}</span>
              <span>{{ formatDate(resource.createdAt) }}</span>
              <span>{{ resource.visibility }}</span>
            </div>
          </div>
          <div class="review-actions">
            <button type="button" class="ghost" @click="openEdit(resource)">查看/编辑</button>
            <button type="button" class="danger-soft" :disabled="isBusy(resource.id)" @click="rejectResource(resource)">拒绝</button>
            <button type="button" class="primary" :disabled="isBusy(resource.id)" @click="approveResource(resource)">通过</button>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'resources'" class="panel">
        <div class="panel-head">
          <div>
            <h2>资源中心管理</h2>
            <p>更改公开状态、标题、类型，或删除资源中心资源。</p>
          </div>
          <label class="search-box">
            <Search :size="16" />
            <input v-model.trim="keyword" type="search" placeholder="搜索标题、作者、类型" />
          </label>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>资源</th>
                <th>类型</th>
                <th>作者</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loadingResources">
                <td colspan="6">正在加载资源...</td>
              </tr>
              <tr v-else-if="!filteredResources.length">
                <td colspan="6">暂无匹配资源。</td>
              </tr>
              <tr v-for="resource in filteredResources" :key="resource.id">
                <td>
                  <strong>{{ resource.title }}</strong>
                  <small>{{ resource.excerpt }}</small>
                </td>
                <td>{{ resource.typeLabel }}</td>
                <td>{{ resource.ownerName || '-' }}</td>
                <td>
                  <span :class="['status', resource.visibility]">{{ visibilityText(resource.visibility) }}</span>
                </td>
                <td>{{ formatDate(resource.updatedAt || resource.createdAt) }}</td>
                <td class="row-actions">
                  <button type="button" title="编辑" @click="openEdit(resource)">
                    <Pencil :size="15" />
                  </button>
                  <button type="button" title="设为公开" :disabled="isBusy(resource.id)" @click="setResourceVisibility(resource, 'public')">
                    <Eye :size="15" />
                  </button>
                  <button type="button" title="设为私有" :disabled="isBusy(resource.id)" @click="setResourceVisibility(resource, 'private')">
                    <EyeOff :size="15" />
                  </button>
                  <button type="button" class="danger-icon" title="删除" :disabled="isBusy(resource.id)" @click="removeResource(resource)">
                    <Trash2 :size="15" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-else class="panel">
        <div class="panel-head">
          <div>
            <h2>基础资源导入</h2>
            <p>导入平台级基础资料，供资源中心和学习推荐使用。</p>
          </div>
        </div>

        <form class="import-form" @submit.prevent="submitImport">
          <label>
            <span>资源标题</span>
            <input v-model.trim="importForm.title" type="text" placeholder="例如：高等数学基础讲义" required />
          </label>
          <label>
            <span>资源类型</span>
            <select v-model="importForm.resourceType">
              <option value="document">文档</option>
              <option value="ppt">PPT</option>
              <option value="mindmap">思维导图</option>
              <option value="exercise">练习题</option>
              <option value="video">视频</option>
            </select>
          </label>
          <label>
            <span>分类</span>
            <input v-model.trim="importForm.category" type="text" placeholder="例如：公共基础课" />
          </label>
          <label>
            <span>资源文件</span>
            <input type="file" @change="handleImportFile" />
          </label>
          <label class="full">
            <span>正文/说明</span>
            <textarea v-model.trim="importForm.content" rows="9" placeholder="可以粘贴 Markdown 内容，或填写资源简介。"></textarea>
          </label>
          <div class="form-actions">
            <button type="submit" class="primary" :disabled="importing">
              <Upload :size="16" />
              {{ importing ? '导入中...' : '导入基础资源' }}
            </button>
          </div>
        </form>
      </section>
    </section>

    <Teleport to="body">
      <section v-if="editingResource" class="modal-mask" @click.self="closeEdit">
        <article class="edit-modal">
          <header>
            <h2>编辑资源</h2>
            <button type="button" aria-label="关闭" @click="closeEdit">×</button>
          </header>
          <form @submit.prevent="saveEdit">
            <label>
              <span>标题</span>
              <input v-model.trim="editForm.title" type="text" required />
            </label>
            <label>
              <span>类型</span>
              <select v-model="editForm.resourceType">
                <option value="document">文档</option>
                <option value="ppt">PPT</option>
                <option value="mindmap">思维导图</option>
                <option value="exercise">练习题</option>
                <option value="image">图片</option>
                <option value="video">视频</option>
              </select>
            </label>
            <label>
              <span>可见性</span>
              <select v-model="editForm.visibility">
                <option value="public">公开</option>
                <option value="private">私有</option>
              </select>
            </label>
            <label class="full">
              <span>内容</span>
              <textarea v-model.trim="editForm.content" rows="10"></textarea>
            </label>
            <footer>
              <button type="button" class="ghost" @click="closeEdit">取消</button>
              <button type="submit" class="primary" :disabled="isBusy(editingResource.id)">保存</button>
            </footer>
          </form>
        </article>
      </section>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  AlertCircle,
  CheckCircle2,
  ClipboardCheck,
  Database,
  Eye,
  EyeOff,
  FileStack,
  Pencil,
  RefreshCw,
  Search,
  Trash2,
  Upload
} from 'lucide-vue-next'
import {
  approvePublicResourceApplication,
  deleteAdminResource,
  getAdminKnowledgeBase,
  getAdminPendingResources,
  getAdminResources,
  getAdminUsers,
  importAdminBaseResource,
  rejectPublicResourceApplication,
  updateAdminResource
} from '../api/apis'

const activeTab = ref('review')
const keyword = ref('')
const loadingReview = ref(false)
const loadingResources = ref(false)
const loadingBase = ref(false)
const importing = ref(false)
const busyMap = ref({})
const errorMessage = ref('')
const successMessage = ref('')
const pendingResources = ref([])
const managedResources = ref([])
const knowledgeBase = ref([])
const users = ref([])
const editingResource = ref(null)
const editForm = reactive({
  title: '',
  resourceType: 'document',
  visibility: 'private',
  content: ''
})
const importForm = reactive({
  title: '',
  resourceType: 'document',
  category: '',
  content: '',
  file: null
})

const loading = computed(() => loadingReview.value || loadingResources.value || loadingBase.value || importing.value)

const tabs = computed(() => [
  { key: 'review', label: '公开审核', icon: ClipboardCheck, count: pendingResources.value.length },
  { key: 'resources', label: '资源管理', icon: FileStack, count: managedResources.value.length },
  { key: 'import', label: '基础导入', icon: Database, count: null }
])

const filteredResources = computed(() => {
  const key = keyword.value.toLowerCase()
  if (!key) return managedResources.value
  return managedResources.value.filter(item => {
    return [item.title, item.ownerName, item.typeLabel, item.visibility]
      .some(value => String(value || '').toLowerCase().includes(key))
  })
})

const setMessage = (message, type = 'success') => {
  if (type === 'error') {
    errorMessage.value = message
    successMessage.value = ''
    return
  }
  successMessage.value = message
  errorMessage.value = ''
}

const unwrapList = result => {
  const data = result?.data?.data ?? result?.data ?? result
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.list)) return data.list
  if (Array.isArray(data?.items)) return data.items
  if (Array.isArray(data?.records)) return data.records
  if (Array.isArray(data?.resources)) return data.resources
  if (Array.isArray(data?.applications)) return data.applications
  return []
}

const typeLabels = {
  document: '文档',
  ppt: 'PPT',
  mindmap: '思维导图',
  exercise: '练习题',
  image: '图片',
  video: '视频',
  resource: '资源'
}

const normalizeResource = item => {
  const id = String(item.application_id || item.applicationId || item.resource_id || item.resourceId || item.id || item.doc_id || '')
  const resourceType = item.resource_type || item.resourceType || item.file_type || item.fileType || item.type || 'resource'
  const title = item.title || item.topic || item.name || item.filename || '未命名资源'
  const content = item.content || item.preview || item.preview_content || item.description || ''
  return {
    id,
    raw: item,
    title,
    content,
    excerpt: String(content || item.summary || item.reason || '暂无内容摘要').replace(/\s+/g, ' ').slice(0, 110),
    resourceType,
    typeLabel: typeLabels[resourceType] || resourceType,
    visibility: item.visibility || item.status || 'pending',
    ownerName: item.owner_name || item.ownerName || item.username || item.user_name || item.author || '',
    createdAt: item.created_at || item.createdAt || item.apply_time || item.applyTime || '',
    updatedAt: item.updated_at || item.updatedAt || ''
  }
}

const normalizeResources = result => unwrapList(result).map(normalizeResource).filter(item => item.id)

const formatDate = value => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16)
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const visibilityText = visibility => {
  if (visibility === 'public') return '公开'
  if (visibility === 'private') return '私有'
  if (visibility === 'pending') return '待审核'
  if (visibility === 'rejected') return '已拒绝'
  return visibility || '-'
}

const isBusy = id => Boolean(busyMap.value[id])

const setBusy = (id, value) => {
  busyMap.value = { ...busyMap.value, [id]: value }
}

const loadPendingResources = async () => {
  loadingReview.value = true
  try {
    pendingResources.value = normalizeResources(await getAdminPendingResources({ status: 'pending' }))
  } catch (error) {
    pendingResources.value = []
    setMessage(getErrorMessage(error, '待审核资源加载失败，请确认后端管理员审核接口是否已启用。'), 'error')
  } finally {
    loadingReview.value = false
  }
}

const loadManagedResources = async () => {
  loadingResources.value = true
  try {
    managedResources.value = normalizeResources(await getAdminResources({ scope: 'all' }))
  } catch (error) {
    managedResources.value = []
    setMessage(getErrorMessage(error, '资源管理列表加载失败，请确认后端管理员资源列表接口是否已启用。'), 'error')
  } finally {
    loadingResources.value = false
  }
}

const loadBaseInfo = async () => {
  loadingBase.value = true
  try {
    const [kbResult, userResult] = await Promise.allSettled([getAdminKnowledgeBase(), getAdminUsers()])
    knowledgeBase.value = kbResult.status === 'fulfilled' ? unwrapList(kbResult.value) : []
    users.value = userResult.status === 'fulfilled' ? unwrapList(userResult.value) : []
  } finally {
    loadingBase.value = false
  }
}

const refreshAll = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  await Promise.all([loadPendingResources(), loadManagedResources(), loadBaseInfo()])
}

const approveResource = async resource => {
  setBusy(resource.id, true)
  try {
    await approvePublicResourceApplication(resource.id, { visibility: 'public' })
    pendingResources.value = pendingResources.value.filter(item => item.id !== resource.id)
    await loadManagedResources()
    setMessage('资源已审核通过。')
  } catch (error) {
    setMessage(getErrorMessage(error, '审核通过失败。'), 'error')
  } finally {
    setBusy(resource.id, false)
  }
}

const rejectResource = async resource => {
  const reason = window.prompt(`请输入拒绝「${resource.title}」的原因：`, '')
  if (reason === null) return
  setBusy(resource.id, true)
  try {
    await rejectPublicResourceApplication(resource.id, { reason })
    pendingResources.value = pendingResources.value.filter(item => item.id !== resource.id)
    setMessage('资源申请已拒绝。')
  } catch (error) {
    setMessage(getErrorMessage(error, '拒绝申请失败。'), 'error')
  } finally {
    setBusy(resource.id, false)
  }
}

const openEdit = resource => {
  editingResource.value = resource
  editForm.title = resource.title
  editForm.resourceType = resource.resourceType || 'document'
  editForm.visibility = resource.visibility === 'public' ? 'public' : 'private'
  editForm.content = resource.content || ''
}

const closeEdit = () => {
  editingResource.value = null
}

const saveEdit = async () => {
  if (!editingResource.value) return
  const id = editingResource.value.id
  setBusy(id, true)
  try {
    await updateAdminResource(id, {
      title: editForm.title,
      topic: editForm.title,
      resource_type: editForm.resourceType,
      visibility: editForm.visibility,
      content: editForm.content
    })
    closeEdit()
    await Promise.all([loadManagedResources(), loadPendingResources()])
    setMessage('资源已保存。')
  } catch (error) {
    setMessage(getErrorMessage(error, '保存资源失败。'), 'error')
  } finally {
    setBusy(id, false)
  }
}

const setResourceVisibility = async (resource, visibility) => {
  setBusy(resource.id, true)
  try {
    await updateAdminResource(resource.id, { visibility })
    resource.visibility = visibility
    setMessage(`资源已设为${visibilityText(visibility)}。`)
  } catch (error) {
    setMessage(getErrorMessage(error, '更新资源可见性失败。'), 'error')
  } finally {
    setBusy(resource.id, false)
  }
}

const removeResource = async resource => {
  if (!window.confirm(`确定删除「${resource.title}」吗？删除后不可恢复。`)) return
  setBusy(resource.id, true)
  try {
    await deleteAdminResource(resource.id)
    managedResources.value = managedResources.value.filter(item => item.id !== resource.id)
    pendingResources.value = pendingResources.value.filter(item => item.id !== resource.id)
    setMessage('资源已删除。')
  } catch (error) {
    setMessage(getErrorMessage(error, '删除资源失败。'), 'error')
  } finally {
    setBusy(resource.id, false)
  }
}

const handleImportFile = event => {
  importForm.file = event.target.files?.[0] || null
}

const submitImport = async () => {
  importing.value = true
  try {
    let payload
    if (importForm.file) {
      payload = new FormData()
      payload.append('file', importForm.file)
      payload.append('title', importForm.title)
      payload.append('resource_type', importForm.resourceType)
      payload.append('category', importForm.category)
      payload.append('content', importForm.content)
      payload.append('visibility', 'public')
    } else {
      payload = {
        title: importForm.title,
        topic: importForm.title,
        resource_type: importForm.resourceType,
        category: importForm.category,
        content: importForm.content,
        visibility: 'public'
      }
    }
    await importAdminBaseResource(payload)
    importForm.title = ''
    importForm.category = ''
    importForm.content = ''
    importForm.file = null
    await Promise.all([loadManagedResources(), loadBaseInfo()])
    setMessage('基础资源已导入。')
  } catch (error) {
    setMessage(getErrorMessage(error, '导入基础资源失败。'), 'error')
  } finally {
    importing.value = false
  }
}

const getErrorMessage = (error, fallback) => {
  return error?.response?.data?.detail ||
    error?.response?.data?.msg ||
    error?.response?.data?.message ||
    error?.message ||
    fallback
}

onMounted(refreshAll)
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  padding: 96px 28px 40px;
  background: #f5f7f9;
  color: #172033;
}

.admin-header {
  max-width: 1280px;
  margin: 0 auto 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.eyebrow {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.admin-header h1 {
  margin: 4px 0 0;
  font-size: 30px;
  letter-spacing: 0;
}

.icon-button,
.row-actions button {
  width: 36px;
  height: 36px;
  border: 1px solid #d7dee8;
  border-radius: 8px;
  background: #fff;
  color: #172033;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

.metric-row,
.workspace {
  max-width: 1280px;
  margin: 0 auto;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.metric {
  padding: 16px;
  border: 1px solid #dfe6ef;
  border-radius: 8px;
  background: #fff;
}

.metric span {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.metric strong {
  display: block;
  margin-top: 6px;
  font-size: 28px;
}

.notice {
  max-width: 1280px;
  margin: 0 auto 14px;
  padding: 10px 12px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  display: flex;
  align-items: center;
  gap: 8px;
}

.notice.success {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #166534;
}

.workspace {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 14px;
}

.admin-tabs {
  padding: 8px;
  border: 1px solid #dfe6ef;
  border-radius: 8px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-self: start;
}

.admin-tabs button {
  height: 42px;
  padding: 0 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  text-align: left;
  font: inherit;
  font-weight: 750;
}

.admin-tabs button.active {
  background: #172033;
  color: #fff;
}

.admin-tabs small {
  min-width: 24px;
  height: 22px;
  border-radius: 999px;
  background: rgba(100, 116, 139, 0.14);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.admin-tabs button.active small {
  background: rgba(255, 255, 255, 0.18);
}

.panel {
  min-width: 0;
  padding: 16px;
  border: 1px solid #dfe6ef;
  border-radius: 8px;
  background: #fff;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.panel h2 {
  margin: 0;
  font-size: 20px;
}

.panel p {
  margin: 4px 0 0;
  color: #64748b;
}

.search-box {
  width: min(340px, 100%);
  height: 38px;
  padding: 0 10px;
  border: 1px solid #d7dee8;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-box input,
.import-form input,
.import-form select,
.import-form textarea,
.edit-modal input,
.edit-modal select,
.edit-modal textarea {
  width: 100%;
  border: 1px solid #d7dee8;
  border-radius: 8px;
  background: #fff;
  color: #172033;
  font: inherit;
  box-sizing: border-box;
}

.search-box input {
  border: 0;
  outline: 0;
}

.empty-line {
  padding: 28px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  text-align: center;
}

.review-item {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
}

.review-item + .review-item {
  margin-top: 10px;
}

.type-chip,
.status {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: #eef2f7;
  color: #334155;
  font-size: 12px;
  font-weight: 800;
}

.resource-main h3 {
  margin: 8px 0 4px;
  font-size: 17px;
}

.resource-main p {
  line-height: 1.55;
}

.meta-line {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
}

.review-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.primary,
.ghost,
.danger-soft {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.primary {
  border: 1px solid #172033;
  background: #172033;
  color: #fff;
}

.ghost {
  border: 1px solid #d7dee8;
  background: #fff;
  color: #172033;
}

.danger-soft {
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #be123c;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.table-wrap {
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 820px;
}

th,
td {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  vertical-align: top;
}

th {
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  font-weight: 850;
}

td strong,
td small {
  display: block;
}

td small {
  max-width: 380px;
  margin-top: 4px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status.public {
  background: #dcfce7;
  color: #166534;
}

.status.private {
  background: #e0f2fe;
  color: #075985;
}

.status.pending {
  background: #fef3c7;
  color: #92400e;
}

.row-actions {
  white-space: nowrap;
}

.row-actions button + button {
  margin-left: 6px;
}

.danger-icon {
  color: #be123c !important;
}

.import-form,
.edit-modal form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.import-form label,
.edit-modal label {
  display: grid;
  gap: 7px;
  color: #334155;
  font-weight: 800;
}

.import-form .full,
.edit-modal .full {
  grid-column: 1 / -1;
}

.import-form input,
.import-form select,
.edit-modal input,
.edit-modal select {
  height: 40px;
  padding: 0 10px;
}

.import-form textarea,
.edit-modal textarea {
  padding: 10px;
  resize: vertical;
}

.form-actions,
.edit-modal footer {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 2000;
  padding: 24px;
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
}

.edit-modal {
  width: min(720px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.28);
}

.edit-modal header {
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.edit-modal header h2 {
  margin: 0;
}

.edit-modal header button {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: #f1f5f9;
  cursor: pointer;
  font-size: 22px;
}

.edit-modal form {
  padding: 16px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 900px) {
  .admin-page {
    padding: 76px 14px 28px;
  }

  .metric-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace {
    grid-template-columns: 1fr;
  }

  .admin-tabs {
    flex-direction: row;
    overflow-x: auto;
  }

  .admin-tabs button {
    min-width: 142px;
  }

  .review-item,
  .panel-head,
  .import-form,
  .edit-modal form {
    grid-template-columns: 1fr;
  }

  .review-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
