<template>
  <div class="chat-page">
    <header class="sketch-topbar">
      <div class="topbar-left">
        <router-link class="round-icon-btn home-link" to="/" aria-label="返回首页">
          <House :size="30" stroke-width="1.6" />
        </router-link>
        <button class="menu-btn" type="button" aria-label="打开最近对话" @click="showHistoryPanel = !showHistoryPanel">
          <Menu :size="34" stroke-width="1.25" />
        </button>
        <button class="menu-btn" type="button" aria-label="管理个人智能体 Skill" title="管理个人智能体 Skill" @click="openSkillPanel">
          <Bot :size="31" stroke-width="1.35" />
        </button>
      </div>
      <UserAccountButton variant="home" logged-out-meta="点击登录" />
    </header>

    <aside class="history-panel" :class="{ open: showHistoryPanel }">

      <button class="new-chat-btn" @click="createNewChat">
        <Plus :size="18" />
        新对话
      </button>

     <div class="recent-section">
  <div class="section-title">
    <span>最近对话</span>
    <span class="delete-icon"></span>
  </div>

  <div v-if="recentChats.length === 0" class="empty-history">
    暂无历史对话
  </div>

  <div v-else class="recent-list">
    <div
      v-for="item in recentChats"
      :key="item.id"
      class="recent-item"
      :class="{ active: activeConversationId === item.id }"
      @click="openConversation(item.id)"
    >
      <span class="chat-dot"></span>

      <div class="recent-main">
        <div class="recent-title">
          {{ item.title }}
        </div>

        <div class="recent-desc">
          {{ item.lastMessage }}
        </div>
      </div>

      <span class="recent-time">
        {{ item.time }}
      </span>
    </div>
  </div>
</div>

    </aside>

    <main class="main">
<section class="chat-content" ref="chatContentRef">
  <div v-if="historyLoading" class="history-loading">
    正在加载历史对话...
  </div>

  <div v-else-if="messages.length === 0" class="empty-chat">
    <h1>ready to create<br>your <span class="empty-chat__sub">learning resources ?</span></h1>
    <div class="resource-hero-visual" aria-hidden="true">
      <article class="hero-card hero-card--left">
        <span class="hero-card__icon">▰</span>
        <strong>整理资料</strong>
        <p>把笔记、文档和知识点快速归纳成学习资源。</p>
      </article>
      <article class="hero-card hero-card--center">
        <span class="hero-card__icon">✦</span>
        <strong>生成内容</strong>
        <p>PPT、图片、题目和思维导图都可以从对话开始。</p>
      </article>
      <article class="hero-card hero-card--right">
        <span class="hero-card__icon">☑</span>
        <strong>开始练习</strong>
        <p>生成题目后进入题库，一题一题完成练习。</p>
      </article>
      <img class="hero-pet" :src="petHeroImage" alt="" />
    </div>
  </div>

  <template v-else>
    <div
      v-for="message in messages"
      :key="message.id"
      class="message-row"
      :class="message.role"
    >
      <div v-if="message.role === 'assistant'" class="ai-avatar">
        ✦
      </div>

      <div class="message-body">
        <div
          v-if="message.type === 'quiz'"
          class="quiz-bubble"
        >
          <div class="file-head">
            <span class="file-icon">✓</span>
            <div class="file-title">
              <strong>{{ message.title || '题目已生成' }}</strong>
              <span>{{ message.questionCount || 0 }} 道题，已放入题库</span>
            </div>
          </div>
          <router-link class="quiz-action" :to="`/question-bank/${message.quizId}`">开始练习</router-link>
          <button
            v-if="message.sourceId"
            class="quiz-action"
            type="button"
            :disabled="message.centerSaveStatus === 'saving' || message.centerSaveStatus === 'saved'"
            @click="saveGeneratedQuizToResources(message)"
          >
            {{ centerSaveLabel(message) }}
          </button>
        </div>

        <div
          v-else-if="message.type === 'file'"
          class="file-bubble"
        >
          <div class="file-head">
            <span class="file-icon">{{ fileIcon(message.fileType) }}</span>
            <div class="file-title">
              <strong>{{ message.filename }}</strong>
              <span>{{ fileTypeLabel(message.fileType) }}</span>
            </div>
          </div>

          <div v-if="message.fileType === 'image' && message.previewUrl" class="file-image-preview">
            <img :src="message.previewUrl" :alt="message.filename" loading="lazy" @error="e => e.target.style.display = 'none'" />
          </div>

          <MindmapPreview
            v-else-if="isMindmapFile(message) && message.content"
            class="chat-mindmap-preview"
            :content="message.content"
            :title="message.filename"
          />

          <div v-else-if="isPptFile(message)" class="file-placeholder">
            PPT 已生成，可以打开幻灯片预览。
          </div>

          <pre v-else-if="message.content" class="file-preview">{{ message.content }}</pre>

          <div v-else class="file-placeholder">
            文件已生成，等待后端提供可预览内容。
          </div>

          <div v-if="message.previewUrl || message.downloadUrl || message.fileId || message.content" class="file-actions">
            <button v-if="isPptFile(message) && canOpenPptPreview(message)" type="button" @click="openPptPreview(message)">
              {{ pptPreview.loading && pptPreview.messageId === message.id ? '加载中...' : '预览' }}
            </button>
            <a v-else-if="message.previewUrl" :href="message.previewUrl" target="_blank" rel="noopener noreferrer">预览</a>
            <button v-if="message.downloadUrl" type="button" @click="downloadGeneratedFile(message)">下载</button>
            <button
              type="button"
              :disabled="message.centerSaveStatus === 'saving' || message.centerSaveStatus === 'saved'"
              @click="saveGeneratedFileToResourceCenter(message)"
            >
              {{ centerSaveLabel(message) }}
            </button>
          </div>
        </div>

        <div
          v-else-if="message.role === 'assistant'"
          class="bubble rich-bubble markdown-body"
          v-html="renderMarkdown(message.content)"
        ></div>

        <div v-else class="bubble">
          {{ message.content }}
        </div>

        <div class="message-time">
          {{ message.time }}
          <span v-if="message.role === 'user'"> ✓✓</span>
        </div>
      </div>
    </div>
  </template>
</section>
      <footer class="input-area">
  <div class="input-box">
    <button class="add-btn" type="button" title="更多操作" @click.stop="showAddMenu = !showAddMenu">
      <Plus :size="34" stroke-width="1.6" />
    </button>

    <div v-if="showAddMenu" class="add-menu" @click.stop>
      <button type="button" @click="handleAddFile">
        <FileText :size="17" stroke-width="1.7" />
        添加文件
      </button>
      <button type="button" @click="handleAddImage">
        <Image :size="17" stroke-width="1.7" />
        添加图片
      </button>
      <button type="button" @click="startNewConversation">
        <Plus :size="17" stroke-width="1.7" />
        开启新对话
      </button>
      <button type="button" @click="showAgentSkillListInChat">
        <Bot :size="17" stroke-width="1.7" />
        能力列表
      </button>
    </div>

    <textarea
      v-model="inputValue"
      rows="1"
      :placeholder="inputPlaceholder"
      @keydown.enter="handleEnter"
    ></textarea>

    <div class="input-actions">
      <div class="quick-tools">
        <button
          v-for="tool in resourceTools"
          :key="tool.label"
          class="quick-tool"
          :class="{ active: selectedResourceTool?.label === tool.label }"
          type="button"
          @click="selectResourceTool(tool)"
        >
          <component :is="tool.icon" :size="15" stroke-width="1.5" />
          <span>{{ tool.label }}</span>
        </button>
        <button class="more-tool" type="button" title="更多">
          <MoreHorizontal :size="22" stroke-width="1.5" />
        </button>
      </div>

      <div class="right-tools">
        <button class="voice-btn" type="button" title="语音输入">
          <Mic :size="20" stroke-width="1.8" />
        </button>
        <button
          class="send-btn"
          type="button"
          :disabled="!inputValue.trim() || loading"
          @click="sendMessage"
        >
          <SendHorizontal :size="22" stroke-width="1.8" />
        </button>
      </div>
    </div>
  </div>
</footer>
    </main>

    <Teleport to="body">
      <section v-if="pptPreview.visible" class="ppt-dialog" @click.self="closePptPreview">
        <article class="ppt-dialog__panel">
          <header class="ppt-dialog__header">
            <div>
              <span>PPT Preview</span>
              <h2>{{ pptPreview.title }}</h2>
            </div>
            <button type="button" aria-label="关闭 PPT 预览" @click="closePptPreview">
              <X :size="20" />
            </button>
          </header>

          <div class="ppt-dialog__body">
            <div v-if="pptPreview.loading" class="ppt-dialog__loading">正在加载 PPT 预览...</div>
            <PptPreview
              v-else-if="pptPreview.slides.length"
              :slides="pptPreview.slides"
              :title="pptPreview.title"
            />
            <div v-else class="ppt-dialog__loading">暂无可预览的幻灯片内容。</div>
          </div>
        </article>
      </section>
    </Teleport>

    <Teleport to="body">
      <section v-if="saveDialog.visible" class="save-dialog" @click.self="closeSaveDialog">
        <article class="save-dialog__panel">
          <h2>保存生成资源</h2>
          <p>选择保存位置，公开后会出现在资源中心；仅自己可见会出现在我的资源。</p>
          <div class="save-dialog__options">
            <label :class="{ active: saveDialog.visibility === 'private' }">
              <input v-model="saveDialog.visibility" type="radio" value="private" />
              <span>仅自己可见</span>
            </label>
            <label :class="{ active: saveDialog.visibility === 'public' }">
              <input v-model="saveDialog.visibility" type="radio" value="public" />
              <span>公开到资源中心</span>
            </label>
          </div>
          <div class="save-dialog__actions">
            <button type="button"  class="primary" @click="closeSaveDialog">取消</button>
            <button type="button" class="primary" @click="confirmSaveGeneratedResource">保存</button>
          </div>
        </article>
      </section>
    </Teleport>

    <Teleport to="body">
      <section v-if="skillPanel.visible" class="skill-dialog" @click.self="closeSkillPanel">
        <article class="skill-dialog__panel">
          <header class="skill-dialog__header">
            <div>
              <span>Personal Agent</span>
              <h2>智能体 Skill</h2>
            </div>
            <button type="button" aria-label="关闭 Skill 管理" @click="closeSkillPanel">
              <X :size="20" />
            </button>
          </header>

          <div class="skill-dialog__body">
            <aside class="skill-list-pane">
              <div class="skill-list-head">
                <strong>已配置</strong>
                <button type="button" @click="startCreateSkill">
                  <Plus :size="15" />
                  新建
                </button>
              </div>

              <p v-if="skillPanel.loading" class="skill-empty">正在加载...</p>
              <p v-else-if="!agentSkills.length" class="skill-empty">暂无自定义 Skill</p>

              <template v-else>
                <article
                  v-for="skill in agentSkills"
                  :key="skill.skill_id || skill.resource_type || skill.name"
                  class="skill-list-item"
                  :class="{ active: selectedSkillKey === skillKey(skill) }"
                  @click="editSkill(skill)"
                >
                  <span>
                    <strong>{{ skill.name }}</strong>
                    <small>{{ skillLabel(skill) }}</small>
                  </span>
                  <button
                    class="skill-delete-btn"
                    type="button"
                    aria-label="删除 Skill"
                    @click.stop="removeSkill(skill)"
                  >
                    <Trash2 :size="15" />
                  </button>
                </article>
              </template>
            </aside>

            <form class="skill-editor" @submit.prevent="saveSkill">
              <div class="skill-editor__top">
                <div>
                  <span>{{ skillFormMode === 'create' ? 'Create' : 'Edit' }}</span>
                  <h3>{{ skillFormMode === 'create' ? '新建智能体能力' : '编辑智能体能力' }}</h3>
                </div>
                <button type="submit" :disabled="skillPanel.saving || !canSaveSkill">
                  <Save :size="16" />
                  保存
                </button>
              </div>

              <label>
                <span>能力名称</span>
                <input v-model.trim="skillForm.name" type="text" placeholder="例如：check_weather" />
              </label>

              <label>
                <span>能力描述</span>
                <input v-model.trim="skillForm.tool_description" type="text" placeholder="例如：当用户询问某地天气时，调用该能力查询实时天气。" />
              </label>

              <div class="skill-form-grid">
                <label>
                  <span>调用方式</span>
                  <select v-model="skillForm.action_config.method">
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                  </select>
                </label>

                <label>
                  <span>动作类型</span>
                  <select v-model="skillForm.action_type">
                    <option value="http">HTTP</option>
                  </select>
                </label>
              </div>

              <label>
                <span>接口地址</span>
                <input v-model.trim="skillForm.action_config.url" type="text" placeholder="https://api.example.com/weather?city={{city}}" />
              </label>

              <label class="skill-prompt-field">
                <span>参数说明 JSON</span>
                <textarea
                  v-model="skillParamsText"
                  rows="8"
                  placeholder='{"city":"城市名称，例如 Beijing"}'
                ></textarea>
              </label>

              <button class="skill-example-btn" type="button" @click="fillWeatherSkillExample">
                <CloudSun :size="16" />
                填入天气能力示例
              </button>

              <p v-if="skillPanel.error" class="skill-error">{{ skillPanel.error }}</p>
            </form>
          </div>
        </article>
      </section>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, ref, nextTick, onMounted } from 'vue'
import {
  downloadWithToken,
  deleteAgentSkill,
  getAgentSkill,
  getAgentSkills,
  streamChatMessage,
  getConversationList,
  getConversationMessages,
  getGeneratedResource,
  upsertAgentActionSkill,
  resolveApiUrl
} from '../api/apis'
import { detectGenerationIntent, executeGeneration } from '../composables/useResourceGeneration'
import UserAccountButton from '../components/UserAccountButton.vue'
import MindmapPreview from '../components/MindmapPreview.vue'
import PptPreview from '../components/PptPreview.vue'
import {
  FileText,
  GitBranch,
  House,
  Image,
  Menu,
  Mic,
  MoreHorizontal,
  Music,
  Plus,
  Presentation,
  CircleHelp,
  Bot,
  CloudSun,
  Save,
  SendHorizontal,
  Trash2,
  X,
  Video
} from 'lucide-vue-next'
import petHeroImage from '../assets/pic/zhiban-pet-base.png'
import { looksLikeQuizContent, upsertQuizSet } from '../utils/quizBank'
import { saveGeneratedResourceRef } from '../utils/savedResources'

const showHistoryPanel = ref(false)
const showAddMenu = ref(false)
const selectedResourceTool = ref(null)

const resourceTools = [
  {
    label: 'music',
    icon: Music,
    prompt: '帮我生成一份音乐学习资源：',
    generateMode: 'resource',
    resourceTypes: ['document']
  },
  {
    label: 'image',
    icon: Image,
    prompt: '帮我生成一张学习配图：',
    generateMode: 'image',
    aspectRatio: '1:1',
    imageCount: 1
  },
  {
    label: 'ppt',
    icon: Presentation,
    prompt: '帮我生成一份 PPT 学习资源：',
    generateMode: 'resource',
    resourceTypes: ['ppt']
  },
  {
    label: 'word',
    icon: FileText,
    prompt: '帮我生成一份 Word 学习文档：',
    generateMode: 'resource',
    resourceTypes: ['document']
  },
  {
    label: 'video',
    icon: Video,
    prompt: '帮我规划一个学习视频脚本：',
    generateMode: 'resource',
    resourceTypes: ['document']
  },
  {
    label: 'skill',
    icon: Bot,
    prompt: '帮我学习并创建一个智能体能力：',
    agentSkillMode: true
  },
  {
    label: 'mindmap',
    icon: GitBranch,
    prompt: '帮我生成一份思维导图：',
    generateMode: 'resource',
    resourceTypes: ['mindmap']
  },
  {
    label: 'quiz',
    icon: CircleHelp,
    prompt: '帮我生成一套练习题，题目要包含题干、选项（如有）、正确答案和解析：',
    generateMode: 'resource',
    resourceTypes: ['exercise']
  }
]

const selectResourceTool = tool => {
  if (selectedResourceTool.value?.label === tool.label) {
    selectedResourceTool.value = null
    return
  }

  selectedResourceTool.value = tool
  nextTick(() => {
    document.querySelector('.input-box textarea')?.focus()
  })
}

const selectedResourceToolName = computed(() => {
  const label = selectedResourceTool.value?.label
  const names = {
    music: '音乐',
    image: '图片',
    ppt: 'PPT',
    word: 'Word',
    video: '视频',
    skill: '智能体能力',
    mindmap: '思维导图',
    quiz: '题目'
  }

  return names[label] || label || ''
})

const inputPlaceholder = computed(() => {
  return selectedResourceTool.value
    ? `请描述你想要的（${selectedResourceToolName.value}）`
    : 'Create something you want...'
})

const stripTypedResourceInstruction = value => {
  return String(value || '').replace(/\n\n【生成类型指令】[\s\S]*$/, '')
}

const stripAgentSkillInstruction = value => {
  return String(value || '').replace(/\n\n【智能体能力指令】[\s\S]*$/, '')
}

const stripInternalInstructions = value => stripAgentSkillInstruction(stripTypedResourceInstruction(value))

const isAgentSkillCreateIntent = value => {
  const text = String(value || '')
  return /(学|学习|创建|添加|新增|接入|掌握|教你|给你).{0,12}(技能|能力|工具|智能体)/.test(text) ||
    /(技能|能力|工具|智能体).{0,12}(学|学习|创建|添加|新增|接入|掌握)/.test(text)
}

const isAgentSkillListIntent = value => {
  const text = String(value || '')
  return /(查看|看看|列出|显示|有什么|有哪些).{0,12}(技能|能力|工具|智能体)/.test(text) ||
    /(技能|能力|工具|智能体).{0,12}(列表|清单|有哪些|有什么)/.test(text)
}

const withAgentSkillInstruction = value => `${value}

【智能体能力指令】
如果用户要求你学习、创建、添加、接入某个可执行能力，请优先使用 create_action_skill 创建动作 Skill，而不是只给文字建议。
创建动作 Skill 前必须确认或找到真实可用的 HTTP API。action_type 使用 "http"。
action_config 必须是 JSON 字符串，包含 url、method、params；url 中动态参数使用 {{参数名}} 占位。
如果用户要求查看已有能力，请调用 list_skills。`

const handleAddFile = () => {
  showAddMenu.value = false
}

const handleAddImage = () => {
  showAddMenu.value = false
}

const startNewConversation = () => {
  showAddMenu.value = false
  createNewChat()
}

const inputValue = ref('')
const recentChats = ref([])
const activeConversationId = ref(null)
const historyLoading = ref(false)
const loading = ref(false)
const chatContentRef = ref(null)
const saveDialog = ref({
  visible: false,
  visibility: 'private',
  message: null
})
const skillPanel = ref({
  visible: false,
  loading: false,
  saving: false,
  error: ''
})
const agentSkills = ref([])
const selectedSkillKey = ref('')
const skillFormMode = ref('create')
const skillForm = ref({
  name: '',
  action_type: 'http',
  action_config: {
    method: 'GET',
    url: ''
  },
  tool_description: ''
})
const skillParamsText = ref('{\n  "city": "城市名称，例如 Beijing"\n}')

const canSaveSkill = computed(() => {
  return Boolean(
    skillForm.value.name.trim() &&
    skillForm.value.tool_description.trim() &&
    skillForm.value.action_config.url.trim()
  )
})

const getResponseData = (res) => {
  return res?.data ?? res ?? {}
}

const skillKey = skill => {
  if (skill?.resource_type) return skill.resource_type
  if (skill?.skill_type === 'action' && skill?.name) return `action:${skill.name}`
  return skill?.name || ''
}

const skillLabel = skill => {
  if (skill?.skill_type === 'action') return `动作 Skill · ${skill.action_type || 'action'}`
  return `生成 Skill · ${skill.resource_type || 'resource'}`
}

const formatAgentSkillList = skills => {
  if (!skills.length) return '你现在还没有学会额外的智能体能力。'

  return [
    `当前已学会 ${skills.length} 个智能体能力：`,
    ...skills.map(skill => `- ${skill.name}：${skill.tool_description || skill.action_type || '可执行能力'}`)
  ].join('\n')
}

const resetSkillForm = () => {
  selectedSkillKey.value = ''
  skillFormMode.value = 'create'
  skillForm.value = {
    name: '',
    action_type: 'http',
    action_config: {
      method: 'GET',
      url: ''
    },
    tool_description: ''
  }
  skillParamsText.value = '{\n  "city": "城市名称，例如 Beijing"\n}'
}

const loadAgentSkills = async () => {
  skillPanel.value.loading = true
  skillPanel.value.error = ''
  try {
    agentSkills.value = normalizeList(await getAgentSkills()).filter(skill => skill.skill_type === 'action')
  } catch (err) {
    console.error('[ChatView] load agent skills failed:', err)
    skillPanel.value.error = err?.response?.data?.detail || err?.message || 'Skill 加载失败'
  } finally {
    skillPanel.value.loading = false
  }
}

const openSkillPanel = async () => {
  skillPanel.value.visible = true
  resetSkillForm()
  await loadAgentSkills()
}

const showAgentSkillListInChat = async () => {
  showAddMenu.value = false
  await loadAgentSkills()
  messages.value.push({
    id: Date.now(),
    role: 'assistant',
    type: 'text',
    content: formatAgentSkillList(agentSkills.value),
    time: getNowTime()
  })
  await scrollToBottom()
}

const closeSkillPanel = () => {
  skillPanel.value.visible = false
  skillPanel.value.error = ''
}

const startCreateSkill = () => {
  skillPanel.value.error = ''
  resetSkillForm()
}

const editSkill = async skill => {
  const key = skillKey(skill)
  selectedSkillKey.value = key
  skillPanel.value.error = ''

  if (skill.skill_type !== 'action') {
    skillPanel.value.error = '这里管理的是智能体动作能力，不编辑资源生成 Skill。'
    return
  }

  skillFormMode.value = 'edit'
  skillForm.value = {
    name: skill.name || '',
    action_type: skill.action_type || 'http',
    action_config: {
      method: 'GET',
      url: ''
    },
    tool_description: skill.tool_description || ''
  }

  try {
    const detailEnvelope = getResponseData(await getAgentSkill(key))
    const detail = detailEnvelope?.data || detailEnvelope
    const actionConfig = typeof detail.action_config === 'string'
      ? JSON.parse(detail.action_config || '{}')
      : detail.action_config || {}
    skillForm.value = {
      name: detail.name || skill.name || '',
      action_type: detail.action_type || skill.action_type || 'http',
      action_config: {
        method: actionConfig.method || 'GET',
        url: actionConfig.url || ''
      },
      tool_description: detail.tool_description || skill.tool_description || ''
    }
    skillParamsText.value = JSON.stringify(actionConfig.params || {}, null, 2)
  } catch (err) {
    console.error('[ChatView] load agent skill failed:', err)
    skillPanel.value.error = err?.response?.data?.detail || err?.message || 'Skill 详情加载失败'
  }
}

const saveSkill = async () => {
  if (!canSaveSkill.value || skillPanel.value.saving) return

  skillPanel.value.saving = true
  skillPanel.value.error = ''
  try {
    let params = {}
    try {
      params = JSON.parse(skillParamsText.value || '{}')
    } catch {
      skillPanel.value.error = '参数说明 JSON 格式不正确'
      return
    }

    await upsertAgentActionSkill({
      name: skillForm.value.name.trim(),
      action_type: skillForm.value.action_type,
      action_config: {
        method: skillForm.value.action_config.method,
        url: skillForm.value.action_config.url.trim(),
        params
      },
      tool_description: skillForm.value.tool_description.trim()
    })
    await loadAgentSkills()
    selectedSkillKey.value = `action:${skillForm.value.name.trim()}`
    skillFormMode.value = 'edit'
  } catch (err) {
    console.error('[ChatView] save agent skill failed:', err)
    skillPanel.value.error = err?.response?.data?.detail || err?.message || 'Skill 保存失败'
  } finally {
    skillPanel.value.saving = false
  }
}

const fillWeatherSkillExample = () => {
  skillForm.value = {
    name: 'check_weather',
    action_type: 'http',
    action_config: {
      method: 'GET',
      url: 'https://api.open-meteo.com/v1/forecast?latitude={{latitude}}&longitude={{longitude}}&current_weather=true'
    },
    tool_description: '当用户询问某地天气时，先确定地点经纬度，再调用该能力查询当前天气。'
  }
  skillParamsText.value = JSON.stringify({
    latitude: '地点纬度，例如 39.9042',
    longitude: '地点经度，例如 116.4074'
  }, null, 2)
}

const removeSkill = async skill => {
  const key = skillKey(skill)
  if (!key) return
  const confirmed = window.confirm(`确定删除「${skill.name || key}」吗？`)
  if (!confirmed) return

  skillPanel.value.error = ''
  try {
    await deleteAgentSkill(key)
    if (selectedSkillKey.value === key) resetSkillForm()
    await loadAgentSkills()
  } catch (err) {
    console.error('[ChatView] delete agent skill failed:', err)
    skillPanel.value.error = err?.response?.data?.detail || err?.message || 'Skill 删除失败'
  }
}

const normalizeList = (res) => {
  const data = getResponseData(res)
  const list = data?.data || data?.records || data?.list || data
  return Array.isArray(list) ? list : []
}

const getRecordTime = (record) => {
  return record?.created_time || record?.created_at || record?.createTime || record?.updated_at || record?.updateTime
}

const getRecordId = (record, fallback) => {
  return record?.id || record?.index || fallback
}

const buildMessagesFromHistory = (records, conversationId) => {
  return records
    .flatMap((item, index) => {
      const time = formatTime(getRecordTime(item))
      const id = getRecordId(item, index)

      const assistantMessage = normalizeHistoryAssistantMessage(item, `${conversationId}-${id}-res`, time)
      return [
        {
          id: `${conversationId}-${id}-req`,
          role: 'user',
          type: 'text',
          content: stripInternalInstructions(item.req),
          time
        },
        assistantMessage
      ].filter(message => message.type !== 'text' || message.content)
    })
}

const normalizeHistoryGroups = (res) => {
  const data = getResponseData(res)
  const groups = data?.data || data

  if (Array.isArray(groups)) {
    return groups
  }

  if (!groups || typeof groups !== 'object') {
    return []
  }

  return Object.entries(groups).map(([groupId, records]) => {
    const list = Array.isArray(records) ? records : []
    const firstRecord = list[0] || {}
    const lastRecord = list[list.length - 1] || firstRecord

    return {
      id: Number(groupId) || firstRecord.chat_group_id || groupId,
      title: stripInternalInstructions(firstRecord.req) || `对话 ${groupId}`,
      lastMessage: stripInternalInstructions(lastRecord.req) || lastRecord.res || '',
      time: formatTime(getRecordTime(lastRecord))
    }
  })
}

const escapeHtml = (value) => {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const renderInlineMarkdown = (value) => {
  let text = escapeHtml(value)

  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  text = text.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
  text = text.replace(/_([^_\n]+)_/g, '<em>$1</em>')
  text = text.replace(/!\[([^\]]*)\]\(((?:https?:\/\/|\/)[^\s)]+)\)/g, (_, label, url) => {
    const href = escapeHtml(resolveApiUrl(url))
    return `<a class="md-image-link" href="${href}" target="_blank" rel="noopener noreferrer"><img class="md-generated-image" src="${href}" alt="${label}" loading="lazy" /></a>`
  })
  text = text.replace(/\[([^\]]+)\]\(((?:https?:\/\/|mailto:|\/)[^\s)]+)\)/g, (_, label, url) => {
    const href = escapeHtml(resolveApiUrl(url))

    if (!/^mailto:/i.test(url) && isImageResourceUrl(url)) {
      return `<a class="md-image-link" href="${href}" target="_blank" rel="noopener noreferrer"><img class="md-generated-image" src="${href}" alt="${label}" loading="lazy" /></a>`
    }

    return `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`
  })

  return text
}

const isImageResourceUrl = url => {
  return /\.(png|jpe?g|webp|gif|bmp|svg)(?:[?#].*)?$/i.test(String(url || ''))
}

const isTableSeparator = (line) => {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line)
}

const renderTable = (tableLines) => {
  const rows = tableLines.map(line => {
    return line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map(cell => renderInlineMarkdown(cell.trim()))
  })

  const header = rows[0] || []
  const body = rows.slice(2)

  return `
    <div class="md-table-wrap">
      <table>
        <thead><tr>${header.map(cell => `<th>${cell}</th>`).join('')}</tr></thead>
        <tbody>${body.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>
      </table>
    </div>
  `
}

const renderMarkdown = (content) => {
  const text = String(content || '').trim()
  if (!text) return ''

  const lines = text.split(/\r?\n/)
  const html = []
  let paragraph = []
  let listItems = []
  let listType = ''
  let codeLines = []
  let inCodeBlock = false
  let codeLanguage = ''

  const flushParagraph = () => {
    if (!paragraph.length) return
    html.push(`<p>${paragraph.map(renderInlineMarkdown).join('<br>')}</p>`)
    paragraph = []
  }

  const flushList = () => {
    if (!listItems.length) return
    const tag = listType === 'ol' ? 'ol' : 'ul'
    html.push(`<${tag}>${listItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</${tag}>`)
    listItems = []
    listType = ''
  }

  const flushCode = () => {
    const languageLabel = codeLanguage ? `<span>${escapeHtml(codeLanguage)}</span>` : ''
    html.push(`<div class="md-code-block">${languageLabel}<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre></div>`)
    codeLines = []
    codeLanguage = ''
  }

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index]
    const line = rawLine.trim()

    if (line.startsWith('```')) {
      if (inCodeBlock) {
        flushCode()
        inCodeBlock = false
      } else {
        flushParagraph()
        flushList()
        inCodeBlock = true
        codeLanguage = line.replace(/^```/, '').trim()
      }
      continue
    }

    if (inCodeBlock) {
      codeLines.push(rawLine)
      continue
    }

    if (!line) {
      flushParagraph()
      flushList()
      continue
    }

    if (line.includes('|') && lines[index + 1] && isTableSeparator(lines[index + 1])) {
      flushParagraph()
      flushList()
      const tableLines = [rawLine, lines[index + 1]]
      index += 2
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        tableLines.push(lines[index])
        index += 1
      }
      index -= 1
      html.push(renderTable(tableLines))
      continue
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      const level = Math.min(headingMatch[1].length + 2, 6)
      html.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`)
      continue
    }

    const blockquoteMatch = line.match(/^>\s?(.+)$/)
    if (blockquoteMatch) {
      flushParagraph()
      flushList()
      html.push(`<blockquote>${renderInlineMarkdown(blockquoteMatch[1])}</blockquote>`)
      continue
    }

    const orderedMatch = line.match(/^\d+\.\s+(.+)$/)
    const unorderedMatch = line.match(/^[-*]\s+(.+)$/)

    if (orderedMatch || unorderedMatch) {
      flushParagraph()
      const currentType = orderedMatch ? 'ol' : 'ul'

      if (listType && listType !== currentType) {
        flushList()
      }

      listType = currentType
      listItems.push((orderedMatch?.[1] || unorderedMatch?.[1] || '').trim())
      continue
    }

    flushList()
    paragraph.push(rawLine)
  }

  if (inCodeBlock) {
    flushCode()
  }
  flushParagraph()
  flushList()

  return html.join('')
}

//格式化后端时间
const formatTime = (timeString) => {
  if (!timeString) return ''

  const date = new Date(timeString)
  const now = new Date()

  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()

  if (isToday) {
    return `${String(date.getHours()).padStart(2, '0')}:${String(
      date.getMinutes()
    ).padStart(2, '0')}`
  }

  return `${date.getMonth() + 1}-${date.getDate()}`
}

//展示用户信息发送时间
const getNowTime = () => {
  const now = new Date()
  const h = String(now.getHours()).padStart(2, '0')
  const m = String(now.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

// 初始空状态展示草图里的学习资源引导
const messages = ref([])
const pptPreview = ref({
  visible: false,
  loading: false,
  messageId: '',
  title: '',
  slides: []
})

const normalizeFileMessage = data => {
  const fileType = data.file_type || data.fileType || data.resource_type || data.resourceType || 'file'
  const rawFilename =
    data.filename ||
    data.file_name ||
    data.name ||
    `${data.topic || fileTypeLabel(fileType)}.${fileExtension(fileType)}`
  const filename = normalizeFileName(rawFilename, fileType)
  const fileId = data.file_id || data.fileId || data.resource_id || data.resourceId || ''

  return {
    id: fileId ? `file-${fileId}` : `file-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    type: 'file',
    fileType,
    filename,
    content: data.content || data.text || data.preview_content || data.previewContent || '',
    slides: Array.isArray(data.slides) ? data.slides : [],
    narration: data.narration || null,
    fileId,
    resourceKind: data.resourceKind || data.kind || 'resource',
    previewUrl: resolveApiUrl(data.preview_url || data.previewUrl || data.preview || ''),
    downloadUrl: resolveApiUrl(data.download_url || data.downloadUrl || data.url || (fileId ? `/resource/${fileId}/download` : '')),
    centerSaveStatus: data.centerSaveStatus || '',
    time: getNowTime()
  }
}

const isExerciseFile = fileData => {
  const type = String(fileData?.file_type || fileData?.fileType || fileData?.resource_type || fileData?.resourceType || '').toLowerCase()
  const content = fileData?.content || fileData?.text || fileData?.preview_content || fileData?.previewContent || ''
  return type.includes('exercise') || type.includes('quiz') || type.includes('question') || looksLikeQuizContent(content)
}

const tryParseJson = value => {
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

const parseResourceHistoryMessage = value => {
  const text = String(value || '')

  // 匹配 /resource/{id}/download 或 /image/{id}/download 格式
  const resourceMatch = text.match(/\[([^\]]+)\]\((\/(?:resource|image)\/(\d+)\/download)\)/)
  if (resourceMatch) {
    const filename = resourceMatch[1]
    const downloadUrl = resourceMatch[2]
    const resourceId = resourceMatch[3]
    const lower = filename.toLowerCase()
    const fileType = lower.includes('exercise') || lower.includes('quiz') || lower.includes('题')
      ? 'exercise'
      : lower.includes('ppt')
        ? 'ppt'
        : lower.includes('mind')
          ? 'mindmap'
          : 'document'

    return {
      file_id: resourceId,
      file_type: fileType,
      filename,
      download_url: downloadUrl,
      content: ''
    }
  }

  // 匹配 markdown 图片 ![](url)，支持任意 URL 格式
  const imageMatch = text.match(/!\[([^\]]*)\]\(([^)]+)\)/)
  if (imageMatch) {
    const filename = imageMatch[1] || '图片'
    const url = imageMatch[2]
    return {
      file_id: url,
      file_type: 'image',
      resourceKind: 'image',
      filename: /\.\w+$/.test(filename) ? filename : `${filename}.jpg`,
      preview_url: url,
      download_url: url,
      content: ''
    }
  }

  // 匹配 [文件名](图片链接) 格式 — 后端可能存为链接而非图片标记
  const linkMatch = text.match(/\[([^\]]+)\]\(([^)]+)\)/)
  if (linkMatch) {
    const url = linkMatch[2]
    if (/\.(png|jpe?g|webp|gif|bmp|svg)(?:[?#].*)?$/i.test(url)) {
      return {
        file_id: url,
        file_type: 'image',
        resourceKind: 'image',
        filename: /\.\w+$/.test(linkMatch[1]) ? linkMatch[1] : `${linkMatch[1]}.jpg`,
        preview_url: url,
        download_url: url,
        content: ''
      }
    }
  }

  return null
}

const normalizeHistoryAssistantMessage = (item, id, time) => {
  const rawContent = item.res || item.content || item.answer || ''
  const parsed = typeof rawContent === 'string' ? tryParseJson(rawContent) : rawContent
  const resourceHistory = parseResourceHistoryMessage(rawContent)

  if (resourceHistory) {
    return { ...normalizeFileMessage(resourceHistory), id, time }
  }

  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    const hasFileShape =
      parsed.file_type ||
      parsed.fileType ||
      parsed.filename ||
      parsed.file_id ||
      parsed.fileId ||
      parsed.resource_id ||
      parsed.resourceId ||
      parsed.download_url ||
      parsed.preview_url

    if (hasFileShape) {
      return { ...normalizeFileMessage(parsed), id, time }
    }
  }

  if (looksLikeQuizContent(rawContent)) {
    const quiz = upsertQuizSet({
      id: `history-quiz-${id}`,
      title: '历史生成题目',
      filename: '历史生成题目',
      fileType: 'exercise',
      content: rawContent
    })

    if (quiz) {
      return {
        id,
        role: 'assistant',
        type: 'quiz',
        quizId: quiz.id,
        title: quiz.title,
        content: quiz.content,
        questionCount: quiz.questionCount,
        time
      }
    }
  }

  return {
    id,
    role: 'assistant',
    type: 'text',
    content: stripInternalInstructions(rawContent),
    time
  }
}

const isPptFile = fileData => {
  return String(fileData?.fileType || fileData?.file_type || fileData?.resource_type || fileData?.filename || '')
    .toLowerCase()
    .match(/ppt|powerpoint|presentation|slide/)
}

const getFileResourceId = fileData => {
  const directId = fileData?.fileId || fileData?.file_id || fileData?.resourceId || fileData?.resource_id || ''
  if (directId) return directId
  const match = String(fileData?.downloadUrl || fileData?.download_url || fileData?.previewUrl || fileData?.preview_url || '')
    .match(/\/resource\/([^/?#]+)(?:\/download)?/i)
  return match?.[1] || ''
}

const canOpenPptPreview = message => {
  return Boolean(message?.slides?.length || message?.content || getFileResourceId(message))
}

const parsePptSlidesFromContent = content => {
  const text = String(content || '').trim()
  if (!text) return []

  try {
    const parsed = JSON.parse(text)
    const list = Array.isArray(parsed) ? parsed : parsed.slides || parsed.pages || parsed.items || []
    if (Array.isArray(list) && list.length) {
      return list.map((slide, index) => ({
        index,
        title: slide.title || slide.heading || `第 ${index + 1} 页`,
        text: slide.text || slide.content || slide.body || '',
        notes: slide.notes || slide.speaker_notes || ''
      }))
    }
  } catch {
    // fall through to markdown/plain-text parsing
  }

  const blocks = text
    .replace(/^```(?:json|markdown|md)?\s*/i, '')
    .replace(/```$/i, '')
    .split(/\n\s*---+\s*\n|(?=\n\s*#{1,3}\s+)/)
    .map(block => block.trim())
    .filter(Boolean)

  return blocks.map((block, index) => {
    const lines = block.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
    const titleLine = lines.find(line => /^#{1,3}\s+/.test(line)) || lines[0] || `第 ${index + 1} 页`
    const title = titleLine.replace(/^#{1,3}\s+/, '').replace(/^第?\s*\d+\s*[页章、.：:-]?\s*/, '').trim()
    const body = lines
      .filter(line => line !== titleLine)
      .map(line => line.replace(/^[-*•]\s+/, '').trim())
      .filter(Boolean)
      .join('\n')

    return {
      index,
      title: title || `第 ${index + 1} 页`,
      text: body,
      notes: ''
    }
  }).filter(slide => slide.title || slide.text)
}

const hydratePptPreview = async message => {
  const resourceId = getFileResourceId(message)
  if (message.slides?.length) return message.slides

  if (resourceId) {
    const res = await getGeneratedResource(resourceId)
    const data = getResponseData(res)?.data || getResponseData(res)
    const content = data.content || message.content || ''
    const slides = Array.isArray(data.slides) && data.slides.length
      ? data.slides
      : parsePptSlidesFromContent(content)

    Object.assign(message, {
      content,
      slides,
      narration: data.narration || message.narration || null
    })

    return slides
  }

  const slides = parsePptSlidesFromContent(message.content)
  Object.assign(message, { slides })
  return slides
}

const openPptPreview = async message => {
  pptPreview.value = {
    visible: true,
    loading: true,
    messageId: message.id,
    title: message.filename || 'PPT 预览',
    slides: message.slides || []
  }

  try {
    const slides = await hydratePptPreview(message)
    pptPreview.value = {
      ...pptPreview.value,
      loading: false,
      slides: slides || []
    }
  } catch (err) {
    console.error('[ChatView] load ppt preview failed:', err)
    pptPreview.value = {
      ...pptPreview.value,
      loading: false,
      slides: parsePptSlidesFromContent(message.content)
    }
  }
}

const closePptPreview = () => {
  pptPreview.value = {
    visible: false,
    loading: false,
    messageId: '',
    title: '',
    slides: []
  }
}

const appendQuizMessage = async fileData => {
  const fileType = fileData.file_type || fileData.fileType || fileData.resource_type || fileData.resourceType || 'exercise'
  const sourceId = fileData.file_id || fileData.fileId || fileData.resource_id || fileData.resourceId || ''
  const filename = fileData.filename || fileData.file_name || fileData.name || 'AI 生成题目'
  const existingQuiz = sourceId
    ? messages.value.find(item => item.type === 'quiz' && item.sourceId === sourceId)
    : null
  const quiz = await upsertQuizSet({
    id: existingQuiz?.quizId,
    sourceId,
    title: fileTitleWithoutExtension(filename),
    filename,
    fileType,
    content: fileData.content || fileData.text || fileData.preview_content || fileData.previewContent || existingQuiz?.content || ''
  })
  if (!quiz) return
  const quizMessage = {
    id: `quiz-${quiz.id}`,
    role: 'assistant',
    type: 'quiz',
    quizId: quiz.id,
    sourceId,
    fileType,
    title: quiz.title,
    content: quiz.content,
    questionCount: quiz.questionCount,
    time: getNowTime()
  }

  if (existingQuiz) {
    Object.assign(existingQuiz, quizMessage)
    return
  }

  messages.value.push(quizMessage)
}

const replaceTextWithQuizMessage = async (message, title = 'AI 生成题目') => {
  if (!message?.content || !looksLikeQuizContent(message.content)) return false

  const quiz = upsertQuizSet({
    id: message.quizId,
    title,
    filename: title,
    fileType: 'exercise',
    content: message.content
  })

  if (!quiz) return false

  Object.assign(message, {
    id: `quiz-${quiz.id}`,
    role: 'assistant',
    type: 'quiz',
    quizId: quiz.id,
    title: quiz.title,
    content: '',
    questionCount: quiz.questionCount,
    time: getNowTime()
  })

  return true
}

const appendFileMessage = async fileData => {
  if (isExerciseFile(fileData)) {
    await appendQuizMessage(fileData)
    return
  }

  const fileMessage = normalizeFileMessage(fileData)
  const existingIndex = messages.value.findIndex(item => {
    return item.type === 'file' && item.fileId && item.fileId === fileMessage.fileId
  })
  const fallbackIndex = existingIndex === -1 && fileMessage.fileType
    ? messages.value.findIndex(item => item.type === 'file' && !item.fileId && item.fileType === fileMessage.fileType)
    : existingIndex

  if (fallbackIndex === -1) {
    messages.value.push(fileMessage)
    return
  }

  messages.value[fallbackIndex] = {
    ...messages.value[fallbackIndex],
    ...fileMessage,
    content: fileMessage.content || messages.value[fallbackIndex].content,
    centerSaveStatus: messages.value[fallbackIndex].centerSaveStatus || fileMessage.centerSaveStatus
  }
}

const appendImageMessage = imageData => {
  const imageId = imageData?.image_id || imageData?.imageId || imageData?.id || ''
  const imageUrl = resolveApiUrl(imageData?.url || imageData?.image_url || imageData?.imageUrl || '')
  const filename = imageData?.filename || imageData?.name || `生成图片${imageId ? `-${imageId}` : ''}.jpg`

  appendFileMessage({
    resourceKind: 'image',
    file_id: imageId || imageUrl || `image-${Date.now()}`,
    file_type: 'image',
    filename,
    preview_url: imageUrl,
    download_url: imageId ? `/image/${imageId}/download` : imageUrl,
    content: imageData?.prompt || ''
  })
}

const centerSaveLabel = message => {
  if (message.centerSaveStatus === 'saving') return '保存中...'
  if (message.centerSaveStatus === 'saved') return message.savedVisibility === 'public' ? '已公开到资源中心' : '已存入我的资源'
  if (message.centerSaveStatus === 'error') return '重新保存'
  return '保存资源'
}

const fileTitleWithoutExtension = filename => String(filename || '生成资源').replace(/\.[^.\\/]+$/, '')

const saveGeneratedFileToResourceCenter = async message => {
  if (!message || message.centerSaveStatus === 'saving' || message.centerSaveStatus === 'saved') return
  saveDialog.value = {
    visible: true,
    visibility: 'private',
    message
  }
}

const saveGeneratedQuizToResources = message => {
  Object.assign(message, {
    fileId: message.sourceId,
    resourceKind: 'resource',
    fileType: message.fileType || 'exercise',
    filename: message.title || 'AI 生成题目',
    content: message.content || ''
  })
  saveGeneratedFileToResourceCenter(message)
}

const closeSaveDialog = () => {
  saveDialog.value.visible = false
  saveDialog.value.message = null
}

const confirmSaveGeneratedResource = async () => {
  const message = saveDialog.value.message
  if (!message || message.centerSaveStatus === 'saving' || message.centerSaveStatus === 'saved') return

  message.centerSaveStatus = 'saving'

  try {
    const category = isExerciseFile(message)
      ? 'exercise'
      : String(message.fileType || '').toLowerCase().includes('ppt')
        ? 'reference'
        : 'reference'

    saveGeneratedResourceRef({
      sourceId: message.fileId || '',
      kind: message.resourceKind || 'resource',
      fileType: message.fileType,
      category,
      quizId: message.quizId || '',
      title: fileTitleWithoutExtension(message.filename),
      filename: message.filename,
      previewUrl: message.previewUrl || '',
      downloadUrl: message.downloadUrl || '',
      content: message.content || '',
      visibility: saveDialog.value.visibility,
      createdAt: new Date().toISOString()
    })

    message.centerSaveStatus = 'saved'
    message.savedVisibility = saveDialog.value.visibility
    closeSaveDialog()
  } catch (error) {
    console.error('存入资源中心失败：', error)
    message.centerSaveStatus = 'error'
    window.alert(error?.message || '保存资源失败，请稍后再试。')
  }
}

const normalizeFileName = (filename, type) => {
  const extension = fileExtension(type)
  const rawName = String(filename || '').trim()
  const safeName = rawName || `${fileTypeLabel(type)}.${extension}`

  if (extension === 'file') return safeName

  if (/\.[^.\\/]+$/.test(safeName)) {
    return safeName.replace(/\.[^.\\/]+$/, `.${extension}`)
  }

  return `${safeName}.${extension}`
}

const getDownloadName = message => {
  return normalizeFileName(message.filename, message.fileType)
}

const downloadGeneratedFile = async message => {
  if (!message?.downloadUrl) return

  try {
    await downloadWithToken(message.downloadUrl, getDownloadName(message))
  } catch (error) {
    console.error('下载生成文件失败：', error)
    window.alert('下载失败，请确认登录状态和后端服务是否正常。')
  }
}

const fileExtension = type => {
  const normalizedType = String(type || '').toLowerCase()

  if (normalizedType.includes('ppt')) return 'pptx'
  if (normalizedType.includes('image')) return 'jpg'
  if (normalizedType.includes('mindmap') || normalizedType.includes('mind')) return 'xmind'
  if (normalizedType.includes('txt') || normalizedType.includes('document')) return 'txt'
  if (normalizedType.includes('pdf')) return 'pdf'
  return 'file'
}

const fileTypeLabel = type => {
  const normalizedType = String(type || '').toLowerCase()

  if (normalizedType.includes('ppt')) return 'PPT 文件'
  if (normalizedType.includes('image')) return '图片'
  if (normalizedType.includes('mind')) return '思维导图'
  if (normalizedType.includes('txt')) return 'TXT 文档'
  if (normalizedType.includes('document')) return '学习文档'
  if (normalizedType.includes('pdf')) return 'PDF 文件'
  return '文件'
}

const fileIcon = type => {
  const normalizedType = String(type || '').toLowerCase()

  if (normalizedType.includes('ppt')) return '📊'
  if (normalizedType.includes('image')) return '🖼️'
  if (normalizedType.includes('mind')) return '🧠'
  if (normalizedType.includes('txt') || normalizedType.includes('document')) return '📄'
  if (normalizedType.includes('pdf')) return '📕'
  return '📁'
}

const isMindmapFile = message => {
  const text = String(`${message?.fileType || ''} ${message?.filename || ''} ${message?.title || ''}`).toLowerCase()
  return text.includes('mindmap') ||
    text.includes('mind_map') ||
    text.includes('mind-map') ||
    text.includes('mind') ||
    text.includes('xmind') ||
    text.includes('思维') ||
    text.includes('导图')
}

const scrollToBottom = async () => {
  await nextTick()

  if (chatContentRef.value) {
    chatContentRef.value.scrollTop = chatContentRef.value.scrollHeight
  }
}

const handleGenerationDone = async eventData => {
  const chatGroupId = eventData?.chat_group_id || activeConversationId.value

  if (chatGroupId) {
    activeConversationId.value = chatGroupId
  }

  if (Array.isArray(eventData?.resources)) {
    for (const resource of eventData.resources) {
      await appendFileMessage(resource)
    }
  }

  await loadConversationList()
}


//获取对话消息
const sendMessage = async () => {
  const text = inputValue.value.trim()

  if (!text || loading.value) return

  showAddMenu.value = false
  const activeTool = selectedResourceTool.value
  const backendText = activeTool?.prompt ? `${activeTool.prompt}${text}` : text
  const shouldHandleAgentSkills = Boolean(activeTool?.agentSkillMode) || isAgentSkillCreateIntent(text) || isAgentSkillListIntent(text)
  const chatRequestText = shouldHandleAgentSkills ? withAgentSkillInstruction(backendText) : text
  const loadingMessageId = Date.now() + 1

  messages.value.push({
    id: Date.now(),
    role: 'user',
    type: 'text',
    content: text,
    time: getNowTime()
  })

  inputValue.value = ''
  selectedResourceTool.value = null

  messages.value.push({
    id: loadingMessageId,
    role: 'assistant',
    type: 'text',
    content: '正在思考中...',
    time: getNowTime()
  })

  await scrollToBottom()

  loading.value = true

  try {
    const target = messages.value.find(item => item.id === loadingMessageId)
    if (!target) return

    if (activeTool?.generateMode) {
      await executeGeneration(backendText, activeTool, activeConversationId.value, {
        onProgress: (msg) => { target.content = msg; target.time = getNowTime() },
        onFile: async (fileData) => { await appendFileMessage(fileData) },
        onImage: (imageData) => { appendImageMessage(imageData) },
        onDone: async (eventData) => {
          target.time = getNowTime()
          await handleGenerationDone(eventData)
        },
      })
      await scrollToBottom()
      return
    }

    // 关键词检测 — 自动路由到资源/图片生成
    const detectedTool = detectGenerationIntent(text)
    if (detectedTool?.generateMode) {
      await executeGeneration(text, detectedTool, activeConversationId.value, {
        onProgress: (msg) => { target.content = msg; target.time = getNowTime() },
        onFile: async (fileData) => { await appendFileMessage(fileData) },
        onImage: (imageData) => { appendImageMessage(imageData) },
        onDone: async (eventData) => {
          target.time = getNowTime()
          await handleGenerationDone(eventData)
        },
      })
      await scrollToBottom()
      return
    }

    let hasReceivedChunk = false

    await streamChatMessage({
      user_req: chatRequestText,
      chat_group_id: activeConversationId.value
    }, {
      onChunk: async chunk => {
        if (!target) return

        if (!hasReceivedChunk) {
          target.content = ''
          hasReceivedChunk = true
        }

        target.content += chunk
        target.time = getNowTime()
        await scrollToBottom()
      },
      onFile: async fileData => {
        if (target && !hasReceivedChunk) {
          target.content = '已生成文件，可以在下方查看预览。'
          target.time = getNowTime()
          hasReceivedChunk = true
        }

        await appendFileMessage(fileData)
        await scrollToBottom()
      },
      onDone: async data => {
        const chatGroupId = data?.chat_group_id || activeConversationId.value

        if (chatGroupId) {
          activeConversationId.value = chatGroupId
        }

        if (target && hasReceivedChunk) {
          await replaceTextWithQuizMessage(target, 'AI 生成题目')
        }

        if (shouldHandleAgentSkills) {
          await loadAgentSkills()
        }
      }
    })

    if (target && hasReceivedChunk) {
      await replaceTextWithQuizMessage(target, 'AI 生成题目')
    }

    await scrollToBottom()
    await loadConversationList()
    if (shouldHandleAgentSkills && isAgentSkillListIntent(text)) {
      await showAgentSkillListInChat()
    }

  } catch (error) {
    console.error(error)

    const target = messages.value.find(item => item.id === loadingMessageId)

    if (target) {
      target.content = '抱歉，服务器暂时没有响应，请稍后再试。'
      target.time = getNowTime()
    }
  } finally {
    loading.value = false
    await nextTick()
  }
}


// 获取历史对话
const loadConversationList = async () => {
  try {
    const res = await getConversationList()

    recentChats.value = normalizeHistoryGroups(res).map(item => {
      const id = item.id || item.conversationId || item.chat_group_id

      return {
        id,
        title: stripTypedResourceInstruction(item.title || item.req) || `对话 ${id}`,
        lastMessage: stripTypedResourceInstruction(item.lastMessage || item.req) || '',
        time: item.time || formatTime(item.updateTime || item.created_time)
      }
    })
  } catch (error) {
    console.error('获取历史对话失败：', error)
  }
}

// 点击左侧某一条历史对话
const openConversation = async (conversationId) => {
  if (historyLoading.value) return

  activeConversationId.value = conversationId
  showHistoryPanel.value = false
  showAddMenu.value = false
  historyLoading.value = true

  try {
    const res = await getConversationMessages(conversationId)

    messages.value = buildMessagesFromHistory(normalizeList(res), conversationId)
    await scrollToBottom()
  } catch (error) {
    console.error('获取历史对话详情失败：', error)

    messages.value = [
      {
        id: Date.now(),
        role: 'assistant',
        type: 'text',
        content: '历史对话加载失败，请稍后再试。',
        time: getNowTime()
      }
    ]
  } finally {
    historyLoading.value = false
  }
}

// 新建对话
const createNewChat = () => {
  activeConversationId.value = null
  inputValue.value = ''
  selectedResourceTool.value = null
  messages.value = []
  showHistoryPanel.value = false
  showAddMenu.value = false
}

//enter发送 enter+shift换行
const handleEnter = (event) => {
  if (event.shiftKey) {
    return
  }

  event.preventDefault()
  sendMessage()
}

onMounted(() => {
  loadConversationList()
})
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.chat-page {
  --primary: #163f8f;
  --primary-soft: #5f8fc3;
  --panel-border: rgba(22, 63, 143, 0.14);
  --panel-bg: rgba(255, 255, 255, 0.9);
  --text-muted: rgba(22, 63, 143, 0.58);
  --shadow-soft: 0 16px 40px rgba(22, 63, 143, 0.1);

  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  color: var(--primary);
  background:
    radial-gradient(ellipse 70% 42% at 8% 0%, rgba(209, 244, 250, 0.42), transparent 68%),
    linear-gradient(135deg, #fafafa 0%, #edf9fc 54%, #fafafa 100%);
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.sketch-topbar {
  position: absolute;
  z-index: 30;
  top: clamp(18px, 2.4vw, 32px);
  left: clamp(18px, 2.4vw, 32px);
  right: clamp(18px, 2.4vw, 32px);
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  pointer-events: none;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  pointer-events: auto;
}

.round-icon-btn,
.menu-btn,
.add-btn,
.more-tool,
.voice-btn,
.send-btn {
  border: 1px solid var(--panel-border);
  background: rgba(255, 255, 255, 0.86);
  color: var(--primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  text-decoration: none;
  flex-shrink: 0;
  box-shadow: var(--shadow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.72);
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.round-icon-btn,
.menu-btn {
  width: 58px;
  height: 58px;
  border-radius: 18px;
}

.sketch-topbar :deep(.account-entry-wrap) {
  pointer-events: auto;
}

.sketch-topbar :deep(.account-entry) {
  width: auto;
  min-width: 172px;
  min-height: 58px;
  padding: 7px 14px 7px 7px;
  border-radius: 18px;
}

.round-icon-btn:hover,
.menu-btn:hover,
.add-btn:hover,
.quick-tool:hover,
.more-tool:hover,
.voice-btn:hover,
.send-btn:hover:not(:disabled),
.new-chat-btn:hover,
.recent-item:hover {
  transform: translateY(-1px);
  border-color: rgba(95, 143, 195, 0.55);
  background: rgba(201, 220, 233, 0.58);
}

.round-icon-btn:focus-visible,
.menu-btn:focus-visible,
.add-btn:focus-visible,
.quick-tool:focus-visible,
.more-tool:focus-visible,
.voice-btn:focus-visible,
.send-btn:focus-visible,
.new-chat-btn:focus-visible,
.recent-item:focus-visible {
  outline: 2px solid rgba(95, 143, 195, 0.24);
  outline-offset: 2px;
}

.history-panel {
  position: absolute;
  z-index: 20;
  top: 0;
  left: 0;
  bottom: 0;
  width: min(360px, 82vw);
  height: 100vh;
  padding: 118px 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  border: 1px solid rgba(22, 63, 143, 0.12);
  border-left: 0;
  border-radius: 0 28px 28px 0;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 18px 0 48px rgba(22, 63, 143, 0.14);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  transform: translateX(-104%);
  pointer-events: none;
  transition: transform 260ms cubic-bezier(0.22, 1, 0.36, 1);
}

.history-panel.open {
  transform: translateX(0);
  pointer-events: auto;
}

.new-chat-btn {
  width: 100%;
  height: 44px;
  border: 1px solid rgba(201, 220, 233, 0.8);
  border-radius: 8px;
  background: #ffffff;
  color: #123b86;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  flex-shrink: 0;
}

.recent-section {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.section-title {
  height: 36px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 800;
}

.delete-icon {
  cursor: pointer;
  color: rgba(22, 63, 143, 0.56);
}

.empty-history {
  padding: 16px 10px;
  color: rgba(22, 63, 143, 0.62);
  font-size: 13px;
}

.recent-list {
  height: calc(100% - 36px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recent-item {
  min-height: 62px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 9px;
  border-radius: 8px;
  color: var(--primary);
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease;
}

.recent-item.active {
  background: rgba(201, 220, 233, 0.62);
}

.chat-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  border: 1.5px solid var(--primary-soft);
  background: #c9dce9;
  flex-shrink: 0;
}

.recent-main {
  flex: 1;
  min-width: 0;
}

.recent-title {
  color: #123b86;
  font-weight: 700;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.recent-desc {
  margin-top: 3px;
  color: rgba(22, 63, 143, 0.58);
  font-size: 12px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.recent-time {
  color: rgba(22, 63, 143, 0.56);
  font-size: 12px;
  flex-shrink: 0;
}

.main {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.chat-content {
  position: static;
  width: 100%;
  height: 100%;
  padding: 112px clamp(20px, 6vw, 96px) 220px;
  overflow-y: auto;
}

.history-loading {
  margin: 120px auto 0;
  width: fit-content;
  color: var(--primary);
  font-size: 14px;
}

.empty-chat {
  position: absolute;
  left: 50%;
  top: 43%;
  z-index: 2;
  width: min(900px, calc(100vw - 96px));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: clamp(10px, 1.6vh, 18px);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.empty-chat h1 {
  margin: 0;
  max-width: 880px;
  color: #25344a;
  font-size: clamp(28px, 2.8vw, 52px);
  font-weight: 400;
  line-height: 1.22;
  text-align: center;
}

.empty-chat__sub {
  color: #163f8f;
}

.resource-hero-visual {
  width: min(760px, 58vw);
  min-width: 420px;
  height: clamp(210px, 30vh, 340px);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
  position: relative;
}

.hero-card {
  position: absolute;
  top: 50%;
  width: clamp(150px, 13vw, 205px);
  min-height: clamp(158px, 20vh, 220px);
  padding: clamp(18px, 2vw, 24px);
  border: 1px solid rgba(226, 235, 244, 0.86);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 22px 48px rgba(56, 76, 112, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.86);
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
  transform: translateY(-50%);
}

.hero-card--left {
  left: 11%;
}

.hero-card--center {
  left: 50%;
  z-index: 2;
  min-height: clamp(184px, 24vh, 250px);
  transform: translate(-50%, -45%);
}

.hero-card--right {
  right: 11%;
}

.hero-card__icon {
  width: 36px;
  height: 36px;
  border-radius: 13px;
  background: rgba(201, 220, 233, 0.48);
  color: var(--primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 900;
}

.hero-card strong {
  color: #171d2d;
  font-size: clamp(16px, 1.4vw, 22px);
  line-height: 1.18;
}

.hero-card p {
  margin: 0;
  color: rgba(23, 29, 45, 0.62);
  font-size: clamp(12px, 0.95vw, 14px);
  line-height: 1.55;
}

.hero-pet {
  position: absolute;
  z-index: 3;
  right: 5%;
  top: -8%;
  width: clamp(94px, 10vw, 138px);
  height: auto;
  filter: drop-shadow(0 16px 26px rgba(95, 143, 195, 0.28));
}

.message-row {
  width: 100%;
  display: flex;
  gap: 14px;
  margin-bottom: 22px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.ai-avatar {
  width: 38px;
  height: 38px;
  margin-top: 4px;
  border-radius: 50%;
  border: 1px solid rgba(201, 220, 233, 0.78);
  background: var(--primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-body {
  max-width: min(760px, 82%);
}

.bubble,
.file-bubble,
.quiz-bubble {
  padding: 16px 18px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  color: var(--primary);
  font-size: 15px;
  line-height: 1.8;
  box-shadow: 0 10px 24px rgba(22, 63, 143, 0.08);
}

.assistant .bubble,
.file-bubble,
.quiz-bubble {
  border-top-left-radius: 6px;
}

.user .bubble {
  border-top-right-radius: 6px;
}

.rich-bubble {
  min-width: min(420px, 100%);
  white-space: normal;
}

.message-time {
  margin-top: 6px;
  color: rgba(22, 63, 143, 0.68);
  font-size: 12px;
}

.user .message-time {
  text-align: right;
}

.file-bubble,
.quiz-bubble {
  width: min(520px, 100%);
}

.file-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #c9dce9;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.file-title {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.file-title strong {
  color: var(--primary);
  font-size: 15px;
  line-height: 1.35;
  word-break: break-word;
}

.file-title span,
.file-placeholder {
  color: rgba(22, 63, 143, 0.62);
  font-size: 12px;
}

.file-image-preview {
  margin: 14px 0 0;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  max-height: 300px;
  background: rgba(237, 249, 252, 0.6);
}

.file-image-preview img {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  border-radius: 8px;
}

.file-preview {
  max-height: 260px;
  margin: 14px 0 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid rgba(196, 226, 248, 0.52);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.58);
  color: var(--primary);
  font-family: inherit;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.file-placeholder,
.file-actions {
  margin-top: 12px;
}

.file-actions {
  display: flex;
  gap: 8px;
}

.file-actions a,
.file-actions button {
  min-height: 30px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: var(--primary);
  color: #ffffff;
  text-decoration: none;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  font-family: inherit;
}

.file-actions button:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

.quiz-action {
  margin-top: 14px;
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  background: var(--primary);
  color: #ffffff;
  text-decoration: none;
  font-size: 13px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  font-family: inherit;
}

.quiz-action + .quiz-action {
  margin-left: 8px;
}

.quiz-action:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

.input-area {
  position: absolute;
  left: 50%;
  bottom: 34px;
  z-index: 4;
  width: min(1040px, calc(100vw - 120px));
  display: flex;
  align-items: flex-end;
  justify-content: center;
  transform: translateX(-50%);
}

.input-box {
  position: relative;
  width: 100%;
  min-height: 158px;
  padding: 22px 22px 18px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 44px rgba(22, 63, 143, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.76);
}

.input-box:focus-within {
  border-color: rgba(95, 143, 195, 0.5);
  box-shadow:
    0 18px 44px rgba(22, 63, 143, 0.1),
    0 0 0 1px rgba(95, 143, 195, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.76);
}

.add-btn,
.more-tool,
.voice-btn,
.send-btn {
  border-radius: 28px;
  width: 40px;
  height: 40px;
}

.add-btn {
  position: absolute;
  left: 20px;
  top: 20px;
  border-radius: 28px;
}

.add-menu {
  position: absolute;
  left: 20px;
  bottom: calc(100% - 14px);
  z-index: 6;
  width: 178px;
  padding: 8px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 16px 32px rgba(22, 63, 143, 0.12);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.add-menu button {
  width: 100%;
  min-height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 8px;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  text-align: left;
}

.add-menu button:hover {
  background: rgba(201, 220, 233, 0.5);
}

.right-tools {
  position: absolute;
  right: 20px;
  top: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}

textarea {
  width: 100%;
  min-height: 48px;
  max-height: 104px;
  padding: 2px 96px 0 58px;
  resize: none;
  border: none;
  outline: none;
  background: transparent;
  color: var(--primary);
  font-family: inherit;
  font-size: 15px;
  line-height: 1.65;
}

textarea::placeholder {
  color: rgba(22, 63, 143, 0.48);
}

.input-actions {
  
  margin-top: 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.quick-tools {
  
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.quick-tool {
  min-width: 96px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 22px;
  background: #ffffff;
  color: var(--primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.quick-tool.active {
  border-color: var(--primary);
  background: rgba(201, 220, 233, 0.72);
  box-shadow: inset 0 0 0 1px rgba(22, 63, 143, 0.12);
}

.send-btn:not(:disabled) {
  background: var(--primary);
  border-color: var(--primary);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(22, 63, 143, 0.16);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.markdown-body :deep(p) {
  margin: 0;
  color: var(--primary);
}

.markdown-body :deep(p + p),
.markdown-body :deep(p + ul),
.markdown-body :deep(p + ol),
.markdown-body :deep(ul + p),
.markdown-body :deep(ol + p),
.markdown-body :deep(.md-table-wrap + p),
.markdown-body :deep(.md-code-block + p) {
  margin-top: 12px;
}

.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 14px 0 8px;
  padding-left: 10px;
  border-left: 3px solid var(--primary-soft);
  color: var(--primary);
  line-height: 1.45;
}

.markdown-body :deep(h3:first-child),
.markdown-body :deep(h4:first-child),
.markdown-body :deep(h5:first-child),
.markdown-body :deep(h6:first-child) {
  margin-top: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol),
.bubble ol,
.bubble ul {
  margin: 10px 0 0;
  padding-left: 22px;
}

.markdown-body :deep(li),
.bubble li {
  margin: 5px 0;
  color: var(--primary);
}

.markdown-body :deep(blockquote) {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-left: 3px solid var(--primary-soft);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.34);
  color: var(--primary);
}

.markdown-body :deep(code) {
  padding: 2px 5px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.52);
  color: var(--primary);
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 0.92em;
}

.markdown-body :deep(.md-code-block) {
  margin-top: 12px;
  overflow: hidden;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.38);
}

.markdown-body :deep(.md-code-block span) {
  display: block;
  padding: 7px 12px;
  color: var(--primary-soft);
  font-size: 12px;
  border-bottom: 1px solid rgba(201, 220, 233, 0.56);
}

.markdown-body :deep(pre) {
  margin: 0;
  padding: 14px;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
  white-space: pre;
}

.markdown-body :deep(a) {
  color: var(--primary);
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.markdown-body :deep(.md-image-link) {
  display: block;
  margin-top: 10px;
  text-decoration: none;
}

.markdown-body :deep(.md-generated-image) {
  display: block;
  width: min(100%, 420px);
  max-height: 320px;
  object-fit: contain;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 12px 24px rgba(22, 63, 143, 0.1);
}

.markdown-body :deep(.md-table-wrap) {
  margin-top: 12px;
  overflow-x: auto;
  border: 1px solid rgba(201, 220, 233, 0.72);
  border-radius: 8px;
}

.skill-dialog {
  position: fixed;
  inset: 0;
  z-index: 4300;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(12, 28, 58, 0.3);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.skill-dialog__panel {
  width: min(920px, 100%);
  max-height: min(760px, 92vh);
  border: 1px solid rgba(201, 220, 233, 0.85);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 24px 70px rgba(22, 63, 143, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.skill-dialog__header {
  min-height: 74px;
  padding: 16px 18px 14px 22px;
  border-bottom: 1px solid rgba(201, 220, 233, 0.72);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.skill-dialog__header span,
.skill-editor__top span,
.skill-editor label span {
  color: var(--primary-soft);
  font-size: 12px;
  font-weight: 900;
}

.skill-dialog__header h2,
.skill-editor__top h3 {
  margin: 4px 0 0;
  color: var(--primary);
}

.skill-dialog__header h2 {
  font-size: 22px;
}

.skill-dialog__header button,
.skill-list-head button,
.skill-editor__top button,
.skill-delete-btn {
  min-height: 36px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: #fff;
  color: var(--primary);
  font: inherit;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
}

.skill-dialog__header button {
  width: 38px;
  padding: 0;
}

.skill-dialog__body {
  min-height: 0;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  flex: 1;
}

.skill-list-pane {
  min-height: 0;
  padding: 16px;
  border-right: 1px solid rgba(201, 220, 233, 0.72);
  overflow-y: auto;
}

.skill-list-head {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.skill-list-head strong {
  color: var(--primary);
}

.skill-list-head button {
  padding: 0 12px;
}

.skill-empty,
.skill-error {
  margin: 12px 0 0;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 800;
}

.skill-error {
  color: #b13d3d;
}

.skill-list-item {
  min-height: 62px;
  margin-bottom: 8px;
  padding: 10px;
  border: 1px solid rgba(201, 220, 233, 0.76);
  border-radius: 8px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  cursor: pointer;
}

.skill-list-item.active,
.skill-list-item:hover {
  border-color: rgba(95, 143, 195, 0.55);
  background: rgba(237, 249, 252, 0.78);
}

.skill-list-item span {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.skill-list-item strong,
.skill-list-item small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-list-item small {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.skill-delete-btn {
  width: 32px;
  min-height: 32px;
  padding: 0;
}

.skill-editor {
  min-height: 0;
  padding: 18px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}

.skill-editor__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.skill-editor__top button {
  min-width: 92px;
  padding: 0 14px;
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.skill-editor__top button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.skill-editor label {
  display: grid;
  gap: 7px;
}

.skill-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.skill-editor input,
.skill-editor select,
.skill-editor textarea {
  width: 100%;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: #fff;
  color: var(--primary);
  font: inherit;
  outline: none;
}

.skill-editor input,
.skill-editor select {
  min-height: 42px;
  padding: 0 12px;
}

.skill-editor textarea {
  min-height: 220px;
  max-height: none;
  padding: 12px;
  resize: vertical;
  line-height: 1.65;
}

.skill-example-btn {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 8px;
  background: rgba(237, 249, 252, 0.78);
  color: var(--primary);
  font: inherit;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  cursor: pointer;
  align-self: flex-start;
}

.save-dialog {
  position: fixed;
  inset: 0;
  z-index: 4200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(12, 28, 58, 0.28);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.ppt-dialog {
  position: fixed;
  inset: 0;
  z-index: 4300;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(12, 28, 58, 0.34);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.ppt-dialog__panel {
  width: min(1120px, 96vw);
  max-height: 92vh;
  border: 1px solid rgba(201, 220, 233, 0.85);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 28px 90px rgba(22, 63, 143, 0.24);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ppt-dialog__header {
  min-height: 68px;
  padding: 14px 18px;
  border-bottom: 1px solid rgba(201, 220, 233, 0.72);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.ppt-dialog__header span {
  color: var(--primary-soft);
  font-size: 12px;
  font-weight: 900;
}

.ppt-dialog__header h2 {
  margin: 3px 0 0;
  color: var(--primary);
  font-size: 20px;
  line-height: 1.3;
}

.ppt-dialog__header button {
  width: 38px;
  height: 38px;
  border: 1px solid rgba(201, 220, 233, 0.86);
  border-radius: 8px;
  background: #ffffff;
  color: var(--primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.ppt-dialog__body {
  min-height: 0;
  padding: 18px;
  overflow: auto;
}

.ppt-dialog__loading {
  min-height: 360px;
  display: grid;
  place-items: center;
  color: var(--primary-soft);
  font-weight: 900;
}

.save-dialog__panel {
  width: min(420px, 100%);
  padding: 22px;
  border: 1px solid rgba(201, 220, 233, 0.85);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 24px 70px rgba(22, 63, 143, 0.2);
}

.save-dialog__panel h2 {
  margin: 0;
  color: var(--primary);
  font-size: 20px;
}

.save-dialog__panel p {
  margin: 8px 0 18px;
  color: var(--text-muted);
  line-height: 1.6;
}

.save-dialog__options {
  display: grid;
  gap: 10px;
}

.save-dialog__options label {
  min-height: 48px;
  padding: 0 14px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 18px;
  background: #fff;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.save-dialog__options label.active {
  border-color: var(--primary);
  background: rgba(237, 249, 252, 0.78);
}

.save-dialog__actions {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.save-dialog__actions button {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: 18px;
  background: #fff;
  color: var(--primary);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.save-dialog__actions .primary {
  background: var(--primary);
  color: #123b86
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  background: rgba(255, 255, 255, 0.38);
  font-size: 14px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 9px 11px;
  border-bottom: 1px solid rgba(201, 220, 233, 0.56);
  border-right: 1px solid rgba(201, 220, 233, 0.56);
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  color: var(--primary);
  background: rgba(255, 255, 255, 0.5);
  font-weight: 700;
}

.chat-content::-webkit-scrollbar,
.recent-list::-webkit-scrollbar {
  width: 8px;
}

.chat-content::-webkit-scrollbar-track,
.recent-list::-webkit-scrollbar-track {
  background: transparent;
}

.chat-content::-webkit-scrollbar-thumb,
.recent-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(95, 143, 195, 0.42);
}

@media (max-width: 900px) {
  .sketch-topbar {
    top: 14px;
    left: 14px;
    right: 14px;
    height: 62px;
  }

  .round-icon-btn,
  .menu-btn {
    width: 46px;
    height: 46px;
    border-radius: 14px;
  }

  .sketch-topbar :deep(.account-entry) {
    min-width: 46px;
    min-height: 46px;
    padding: 4px;
    border-radius: 14px;
  }

  .history-panel {
    width: min(320px, 86vw);
    padding: 92px 16px 18px;
    border-radius: 0 22px 22px 0;
  }

  .chat-content {
    padding: 88px 14px 218px;
  }

  .skill-dialog {
    padding: 14px;
  }

  .skill-dialog__body {
    grid-template-columns: 1fr;
  }

  .skill-list-pane {
    max-height: 220px;
    border-right: 0;
    border-bottom: 1px solid rgba(201, 220, 233, 0.72);
  }

  .skill-form-grid {
    grid-template-columns: 1fr;
  }

  .empty-chat {
    top: 42%;
    width: calc(100vw - 28px);
  }

  .empty-chat h1 {
    font-size: clamp(28px, 8vw, 40px);
  }

  .resource-hero-visual {
    width: min(100%, 640px);
    min-width: 0;
    height: clamp(160px, 28vh, 280px);
  }

  .hero-card {
    width: clamp(118px, 31vw, 158px);
    min-height: 150px;
    padding: 14px;
    border-radius: 18px;
  }

  .hero-card--left {
    left: 0;
  }

  .hero-card--right {
    right: 0;
  }

  .hero-card p {
    display: none;
  }

  .hero-pet {
    right: 2%;
    top: -10%;
    width: clamp(74px, 20vw, 104px);
  }

  .input-area {
    bottom: 16px;
    width: calc(100vw - 28px);
  }

  .input-box {
    min-height: 170px;
    padding: 18px 16px 16px;
    border-radius: 20px;
  }

  .add-btn {
    left: 16px;
    top: 16px;
  }

  .add-menu {
    left: 16px;
    bottom: calc(100% - 12px);
  }

  .right-tools {
    right: 16px;
    top: 16px;
  }

  textarea {
    padding-left: 54px;
    padding-right: 92px;
  }

  .quick-tool {
    min-width: 0;
    height: 34px;
    padding: 0 10px;
  }

  .quick-tool span {
    display: none;
  }

  .message-body {
    max-width: 88%;
  }
}
</style>
