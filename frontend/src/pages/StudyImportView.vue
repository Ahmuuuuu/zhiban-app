<template>
  <div class="import-page">
    <main class="import-main">
      <header class="topbar">
        <div>
          <h1>学习资料导入</h1>
          <p>上传文字资料，后续可用于知识库解析、资源匹配和 AI 学习建议。</p>
        </div>
      </header>

      <section class="import-workspace">
        <div class="upload-panel">
          <div
            class="drop-zone"
            :class="{ dragging: isDragging, ready: selectedFile }"
            @dragenter.prevent="isDragging = true"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInputRef"
              class="file-input"
              type="file"
              accept=".txt,.md,.csv,.json,.pdf,.docx,text/plain,text/markdown,text/csv,application/json,application/pdf"
              @change="handleFileChange"
            />

            <div class="upload-mark">文</div>
            <h2>{{ selectedFile ? selectedFile.name : '选择或拖入文字文件' }}</h2>
            <p>{{ selectedFile ? fileMetaText : '当前支持 txt、pdf、docx、md、csv、json 等文字文件' }}</p>

            <div class="upload-actions">
              <button type="button" class="primary-btn" @click="openFilePicker">
                选择文件
              </button>
              <button
                v-if="selectedFile"
                type="button"
                class="ghost-btn"
                @click="clearFile"
              >
                重新选择
              </button>
            </div>
          </div>

          <form class="meta-form" @submit.prevent="submitMaterial">
            <label>
              <span>资料标题</span>
              <input v-model="materialTitle" type="text" placeholder="例如：高数第一章笔记" />
            </label>

            <label>
              <span>资料说明</span>
              <textarea
                v-model="materialDescription"
                rows="4"
                placeholder="可填写课程、章节、来源或需要 AI 重点理解的内容"
              ></textarea>
            </label>

            <fieldset class="visibility-group">
              <legend>资料可见性</legend>
              <label class="radio-option">
                <input v-model="visibility" type="radio" value="private" />
                <span>仅我可见</span>
                <small>只有你可以访问和使用这份资料</small>
              </label>
              <label class="radio-option">
                <input v-model="visibility" type="radio" value="public" />
                <span>全员可见</span>
                <small>所有用户都可以查看和使用（需管理员权限）</small>
              </label>
            </fieldset>

            <fieldset class="category-group">
              <legend>资料类型</legend>
              <div class="category-options">
                <label
                  v-for="cat in categoryOptions"
                  :key="cat.value"
                  class="cat-label"
                  :class="{ active: category === cat.value }"
                >
                  <input v-model="category" type="radio" :value="cat.value" />
                  <span>{{ cat.label }}</span>
                </label>
              </div>
            </fieldset>

            <p v-if="statusMessage" class="status-message" :class="statusType">
              {{ statusMessage }}
            </p>

            <button class="submit-btn" type="submit" :disabled="!selectedFile || uploading">
              {{ uploading ? '导入中...' : '导入学习资料' }}
            </button>
          </form>
        </div>

        <aside class="preview-panel">
          <div class="preview-head">
            <h2>内容预览</h2>
            <span>{{ previewText ? `${previewText.length} 字` : '等待文件' }}</span>
          </div>

          <div v-if="previewText" class="preview-box">
            {{ previewText }}
          </div>

          <div v-else class="empty-preview">
            选择文字文件后，这里会显示前 3000 个字符，便于你确认资料内容。
          </div>
        </aside>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { uploadStudyMaterial } from '../api/apis'

const fileInputRef = ref(null)
const selectedFile = ref(null)
const previewText = ref('')
const materialTitle = ref('')
const materialDescription = ref('')
const visibility = ref('private')
const category = ref('knowledge_point')
const statusMessage = ref('')
const statusType = ref('')
const uploading = ref(false)
const isDragging = ref(false)

const allowedExtensions = ['txt', 'md', 'csv', 'json', 'pdf', 'docx']

// 与后端 KB_CATEGORIES 对齐
const categoryOptions = [
  { value: 'knowledge_point', label: '知识点讲解' },
  { value: 'exercise', label: '习题/题库' },
  { value: 'textbook', label: '教科书章节' },
  { value: 'note', label: '学习笔记' },
  { value: 'case_study', label: '实操案例' },
  { value: 'reference', label: '参考资料' },
]

const fileMetaText = computed(() => {
  if (!selectedFile.value) return ''

  const size = selectedFile.value.size / 1024
  return `${size < 1024 ? size.toFixed(1) + ' KB' : (size / 1024).toFixed(2) + ' MB'}`
})

const openFilePicker = () => {
  fileInputRef.value?.click()
}

const isTextFile = (file) => {
  const extension = file.name.split('.').pop()?.toLowerCase()
  return file.type.startsWith('text/') || allowedExtensions.includes(extension)
}

const setStatus = (message, type = '') => {
  statusMessage.value = message
  statusType.value = type
}

const readFile = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file, 'utf-8')
  })
}

const loadFile = async (file) => {
  if (!file) return

  if (!isTextFile(file)) {
    setStatus('当前仅支持文字文件，请选择 txt、md、csv 或 json 文件', 'error')
    return
  }

  selectedFile.value = file
  materialTitle.value = materialTitle.value || file.name.replace(/\.[^.]+$/, '')
  setStatus('')

  try {
    const text = await readFile(file)
    previewText.value = text.slice(0, 3000)
  } catch (error) {
    clearFile()
    setStatus(error.message || '文件读取失败', 'error')
  }
}

const handleFileChange = (event) => {
  loadFile(event.target.files?.[0])
}

const handleDrop = (event) => {
  isDragging.value = false
  loadFile(event.dataTransfer.files?.[0])
}

const clearFile = () => {
  selectedFile.value = null
  previewText.value = ''
  statusMessage.value = ''

  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

const submitMaterial = async () => {
  if (!selectedFile.value || uploading.value) return

  uploading.value = true
  setStatus('')

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('title', materialTitle.value.trim() || selectedFile.value.name)
  formData.append('visibility', visibility.value)
  formData.append('category', category.value)

  try {
    const res = await uploadStudyMaterial(formData)

    if (res?.code && res.code !== 200) {
      throw new Error(res.msg || '资料导入失败')
    }

    setStatus('学习资料已提交，等待后端处理。', 'success')
  } catch (error) {
    setStatus(
      error?.response?.data?.detail ||
        error?.response?.data?.msg ||
        error?.message ||
        '资料导入失败，请稍后再试',
      'error'
    )
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.import-page {
  height: 100vh;
  overflow: hidden;
  background: #fafafa;
  color: #163f8f;
  font-family:
    Inter,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
}

.import-main {
  height: 100vh;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.topbar {
  min-height: 68px;
  padding: 18px 34px;
  background: #fafafa;
  border-bottom: 1px solid #c9dce9;
  display: flex;
  align-items: center;
}

.topbar h1 {
  margin: 0;
  color: #163f8f;
  font-size: 22px;
  font-weight: 700;
}

.topbar p {
  margin: 6px 0 0;
  color: #5f8fc3;
  font-size: 14px;
}

.import-workspace {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 34px 56px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 22px;
}

.upload-panel,
.preview-panel {
  min-width: 0;
  min-height: 0;
  border: 1px solid #c9dce9;
  background: #fafafa;
  border-radius: 8px;
}

.upload-panel {
  height: 100%;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
}

.drop-zone {
  min-height: 0;
  padding: 28px;
  border-right: 1px solid #c9dce9;
  background: #f0efdd;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
}

.drop-zone.dragging,
.drop-zone.ready {
  background: #c9dce9;
}

.file-input {
  display: none;
}

.upload-mark {
  width: 58px;
  height: 58px;
  margin-bottom: 18px;
  border-radius: 8px;
  background: #163f8f;
  color: #fafafa;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
}

.drop-zone h2,
.preview-head h2 {
  margin: 0;
  color: #163f8f;
  font-size: 20px;
}

.drop-zone p {
  margin: 10px 0 0;
  color: #5f8fc3;
  font-size: 14px;
}

.upload-actions {
  margin-top: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.primary-btn,
.ghost-btn,
.submit-btn {
  height: 40px;
  padding: 0 18px;
  border: 1px solid #163f8f;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.primary-btn,
.submit-btn {
  background: #163f8f;
  color: #fafafa;
}

.ghost-btn {
  background: #fafafa;
  color: #163f8f;
}

.meta-form {
  min-height: 0;
  overflow-y: auto;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.meta-form label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #5f8fc3;
  font-size: 13px;
  font-weight: 700;
}

.meta-form input,
.meta-form textarea {
  width: 100%;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #fafafa;
  color: #163f8f;
  font: inherit;
  outline: none;
  box-sizing: border-box;
}

.meta-form input {
  height: 42px;
  padding: 0 12px;
}

.meta-form textarea {
  padding: 12px;
  resize: vertical;
}

.meta-form input:focus,
.meta-form textarea:focus {
  border-color: #5f8fc3;
}

.status-message {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #c9dce9;
  color: #163f8f;
  font-size: 13px;
  line-height: 1.5;
}

.status-message.success {
  background: #c9dce9;
}

.status-message.error {
  background: #f0efdd;
}

.visibility-group {
  margin: 0;
  padding: 14px;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #f5f9fc;
}

.visibility-group legend {
  padding: 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #5f8fc3;
}

.radio-option {
  display: flex;
  align-items: flex-start;
  margin-top: 10px;
  cursor: pointer;
  gap: 10px;
}

.radio-option input[type="radio"] {
  margin-top: 3px;
  cursor: pointer;
  flex-shrink: 0;
}

.radio-option span {
  font-size: 14px;
  font-weight: 700;
  color: #163f8f;
}

.radio-option small {
  display: block;
  font-size: 12px;
  color: #5f8fc3;
  line-height: 1.4;
  margin-top: 4px;
}

/* 资料类型 */
.category-group {
  margin: 0;
  padding: 14px;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #f5f9fc;
}

.category-group legend {
  padding: 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #5f8fc3;
}

.category-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.cat-label {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.cat-label input {
  display: none;
}

.cat-label span {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid rgba(196, 226, 248, 0.5);
  font-size: 12px;
  font-weight: 600;
  color: rgba(22, 63, 143, 0.7);
  background: rgba(255, 255, 255, 0.5);
  transition: all 0.2s;
}

.cat-label.active span {
  background: #163f8f;
  color: #fafafa;
  border-color: #163f8f;
}

.cat-label:hover span {
  border-color: #5f8fc3;
}

.submit-btn {
  width: 100%;
  margin-top: auto;
}

.submit-btn:disabled {
  background: #5f8fc3;
  border-color: #5f8fc3;
  cursor: not-allowed;
}

.preview-panel {
  padding: 22px;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.preview-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.preview-head span {
  color: #5f8fc3;
  font-size: 13px;
  flex-shrink: 0;
}

.preview-box,
.empty-preview {
  flex: 1;
  min-height: 0;
  max-height: 100%;
  overflow-y: auto;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #f0efdd;
  color: #163f8f;
  line-height: 1.8;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.preview-box::-webkit-scrollbar,
.meta-form::-webkit-scrollbar {
  width: 9px;
}

.preview-box::-webkit-scrollbar-track,
.meta-form::-webkit-scrollbar-track {
  background: #c9dce9;
  border-radius: 999px;
}

.preview-box::-webkit-scrollbar-thumb,
.meta-form::-webkit-scrollbar-thumb {
  background: #163f8f;
  border-radius: 999px;
  border: 2px solid #c9dce9;
}

.preview-box,
.meta-form {
  scrollbar-color: #163f8f #c9dce9;
  scrollbar-width: thin;
}

.preview-box {
  padding: 18px;
}

.empty-preview {
  padding: 24px;
  display: flex;
  align-items: center;
}

@media (max-width: 1100px) {
  .import-main {
    overflow-y: auto;
  }

  .import-workspace {
    overflow: visible;
  }

  .import-workspace,
  .upload-panel {
    grid-template-columns: 1fr;
  }

  .preview-panel {
    height: 420px;
  }

  .drop-zone {
    border-right: none;
    border-bottom: 1px solid #c9dce9;
  }
}

@media (max-width: 700px) {
  .topbar {
    padding: 16px 20px;
  }

  .import-workspace {
    padding: 20px;
  }

  .drop-zone,
  .meta-form,
  .preview-panel {
    padding: 18px;
  }
}

/* Resource-center aligned skin */
.import-page {
  background:
    radial-gradient(ellipse 72% 44% at 10% 0%, rgba(209, 244, 250, 0.46), transparent 70%),
    linear-gradient(135deg, #fafafa 0%, rgb(237, 249, 252) 52%, #fafafa 100%);
}

.topbar {
  min-height: 82px;
  padding: 22px 34px 14px;
  border-bottom: 0;
  background: transparent;
}

.topbar h1 {
  font-size: 28px;
  font-weight: 900;
}

.topbar p {
  color: rgba(22, 63, 143, 0.66);
  font-weight: 700;
}

.import-workspace {
  padding: 20px 34px 30px;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 32px;
}

.upload-panel,
.preview-panel {
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 28px;
  background: rgba(250, 250, 250, 0.78);
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
}

.drop-zone {
  border-right: 1px solid rgba(201, 220, 233, 0.72);
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.92), rgba(237, 249, 252, 0.84)),
    #fafafa;
}

.drop-zone.dragging,
.drop-zone.ready {
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.96), rgba(201, 220, 233, 0.74)),
    #fafafa;
}

.upload-mark,
.primary-btn,
.submit-btn {
  background: #163f8f;
  color: #fafafa;
}

.primary-btn,
.ghost-btn,
.submit-btn,
.meta-form input,
.meta-form textarea,
.visibility-group,
.category-group,
.preview-box,
.empty-preview,
.status-message {
  border-radius: 18px;
}

.meta-form input,
.meta-form textarea,
.visibility-group,
.category-group,
.preview-box,
.empty-preview {
  border-color: rgba(201, 220, 233, 0.82);
  background: rgba(250, 250, 250, 0.76);
}

.preview-box,
.empty-preview {
  background: rgba(237, 249, 252, 0.58);
}
</style>
