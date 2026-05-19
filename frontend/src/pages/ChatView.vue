<template>
  <div class="chat-page">
    <!-- 左侧栏 -->
    <aside class="sidebar">
      <div class="brand">
        <router-link class="home-link" to="/" aria-label="返回首页">←</router-link>
        <div class="brand-left">
        
        </div>
      </div>

      <button class="new-chat-btn" @click="createNewChat">
        <span class="plus">＋</span>
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

    <!-- 右侧主区域 -->
    <main class="main">
      <header class="topbar">
        <h1>知伴</h1>
      </header>
<section class="chat-content" ref="chatContentRef">
  <div v-if="historyLoading" class="history-loading">
    正在加载历史对话...
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
          v-if="message.type === 'file'"
          class="file-bubble"
        >
          <div class="file-head">
            <span class="file-icon">{{ fileIcon(message.fileType) }}</span>
            <div class="file-title">
              <strong>{{ message.filename }}</strong>
              <span>{{ fileTypeLabel(message.fileType) }}</span>
            </div>
          </div>

          <pre v-if="message.content" class="file-preview">{{ message.content }}</pre>

          <div v-else class="file-placeholder">
            文件已生成，等待后端提供可预览内容。
          </div>

          <div v-if="message.previewUrl || message.downloadUrl" class="file-actions">
            <a v-if="message.previewUrl" :href="message.previewUrl" target="_blank" rel="noopener noreferrer">预览</a>
            <a v-if="message.downloadUrl" :href="message.downloadUrl" target="_blank" rel="noopener noreferrer">下载</a>
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
    <textarea
      v-model="inputValue"
      rows="1"
      placeholder="输入你的问题，Enter 发送，Shift + Enter 换行"
      @keydown.enter="handleEnter"
    ></textarea>

    <div class="input-actions">
      <div class="left-tools">
        <button class="tool-btn resource-tool-btn" @click="openResourceSidebar" title="生成学习资源">📄</button>
      </div>

      <button
        class="send-btn"
        :disabled="!inputValue.trim() || loading"
        @click="sendMessage"
      >
        ➤
      </button>
    </div>
  </div>
</footer>
    </main>
    <ResourceSidebar
      :visible="showResourceSidebar"
      :contextTopic="resourceTopic"
      @toggle="showResourceSidebar = !showResourceSidebar"
    />
    <PortraitSetupModal />
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { streamChatMessage, getConversationList, getConversationMessages } from '../api/apis'
import PortraitSetupModal from '../components/PortraitSetupModal.vue'
import ResourceSidebar from '../components/ResourceSidebar.vue'

const showResourceSidebar = ref(false)
const resourceTopic = ref('')

const openResourceSidebar = () => {
  // 用最近一条用户消息作为默认主题
  const lastUserMsg = [...messages.value].reverse().find(m => m.role === 'user')
  resourceTopic.value = lastUserMsg?.content?.slice(0, 80) || ''
  showResourceSidebar.value = true
}

const inputValue = ref('')
const recentChats = ref([])
const activeConversationId = ref(null)
const historyLoading = ref(false)
const loading = ref(false)
// 选择智能体
// const currentAgentId = ref('study-assistant')
const chatContentRef = ref(null)

const getResponseData = (res) => {
  return res?.data ?? res ?? {}
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

      return [
        {
          id: `${conversationId}-${id}-req`,
          role: 'user',
          type: 'text',
          content: item.req || '',
          time
        },
        {
          id: `${conversationId}-${id}-res`,
          role: 'assistant',
          type: 'text',
          content: item.res || '',
          time
        }
      ].filter(message => message.content)
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
      title: firstRecord.req || `对话 ${groupId}`,
      lastMessage: lastRecord.req || lastRecord.res || '',
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
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')

  return text
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

//初始信息展示
const messages = ref([
  {
    id: Date.now(),
    role: 'assistant',
    type: 'text',
    content: '你好，我是知伴 AI，有什么可以帮你？',
    time: '10:00'
  }
])

const normalizeFileMessage = data => {
  const fileType = data.file_type || data.fileType || data.resource_type || data.resourceType || 'file'
  const filename =
    data.filename ||
    data.file_name ||
    data.name ||
    `${fileTypeLabel(fileType)}.${fileExtension(fileType)}`

  return {
    id: `file-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    type: 'file',
    fileType,
    filename,
    content: data.content || data.text || data.preview_content || data.previewContent || '',
    fileId: data.file_id || data.fileId || data.resource_id || data.resourceId || '',
    previewUrl: data.preview_url || data.previewUrl || data.preview || '',
    downloadUrl: data.download_url || data.downloadUrl || data.url || '',
    time: getNowTime()
  }
}

const fileExtension = type => {
  const normalizedType = String(type || '').toLowerCase()

  if (normalizedType.includes('ppt')) return 'pptx'
  if (normalizedType.includes('txt') || normalizedType.includes('document')) return 'txt'
  if (normalizedType.includes('pdf')) return 'pdf'
  return 'file'
}

const fileTypeLabel = type => {
  const normalizedType = String(type || '').toLowerCase()

  if (normalizedType.includes('ppt')) return 'PPT 文件'
  if (normalizedType.includes('txt')) return 'TXT 文档'
  if (normalizedType.includes('document')) return '学习文档'
  if (normalizedType.includes('pdf')) return 'PDF 文件'
  return '文件'
}

const fileIcon = type => {
  const normalizedType = String(type || '').toLowerCase()

  if (normalizedType.includes('ppt')) return '📊'
  if (normalizedType.includes('txt') || normalizedType.includes('document')) return '📄'
  if (normalizedType.includes('pdf')) return '📕'
  return '📁'
}

const scrollToBottom = async () => {
  await nextTick()

  if (chatContentRef.value) {
    chatContentRef.value.scrollTop = chatContentRef.value.scrollHeight
  }
}


//获取对话消息
const sendMessage = async () => {
  const text = inputValue.value.trim()

  if (!text || loading.value) return

  const loadingMessageId = Date.now() + 1

  messages.value.push({
    id: Date.now(),
    role: 'user',
    type: 'text',
    content: text,
    time: getNowTime()
  })

  inputValue.value = ''

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
    let hasReceivedChunk = false

    await streamChatMessage({
      user_req: text,
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

        messages.value.push(normalizeFileMessage(fileData))
        await scrollToBottom()
      },
      onDone: data => {
        const chatGroupId = data?.chat_group_id || activeConversationId.value

        if (chatGroupId) {
          activeConversationId.value = chatGroupId
        }
      }
    })

    await scrollToBottom()
    await loadConversationList()

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
        title: item.title || `对话 ${id}`,
        lastMessage: item.lastMessage || item.req || '',
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

  messages.value = [
    {
      id: Date.now(),
      role: 'assistant',
      type: 'text',
      content: '你好，我是知伴 AI，有什么可以帮你？',
      time: getNowTime()
    }
  ]
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
/* 
  可用色：
  深蓝：#163f8f
  中蓝：#5f8fc3
  浅蓝：#c9dce9
  米白：#f0efdd
  新增：#fafafa
*/

* {
  box-sizing: border-box;
}

.chat-page {
  position: relative;
  width: 100%;
  height: 100vh;
  display: flex;
  background:
    radial-gradient(ellipse 72% 46% at 8% 14%, rgba(196, 226, 248, 0.28) 0 24%, rgba(196, 226, 248, 0.08) 48%, transparent 74%),
    radial-gradient(ellipse 58% 34% at 86% 82%, rgba(168, 215, 246, 0.18) 0 22%, transparent 70%),
    linear-gradient(145deg, #ffffff 0%, #f9fdff 52%, #eef8ff 100%);
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

.chat-page::before {
  content: "";
  position: fixed;
  left: -30vw;
  right: -18vw;
  bottom: -30vh;
  height: 54vh;
  pointer-events: none;
  background:
    radial-gradient(ellipse 44% 60% at 10% 52%, rgba(196, 226, 248, 0.22) 0 34%, rgba(196, 226, 248, 0.08) 62%, transparent 88%),
    radial-gradient(ellipse 42% 58% at 62% 44%, rgba(168, 215, 246, 0.16) 0 30%, rgba(168, 215, 246, 0.06) 58%, transparent 86%);
  filter: blur(34px);
  opacity: 0.42;
}

/* 左侧栏 */
.sidebar {
  position: relative;
  z-index: 1;
  width: 220px;
  height: 100%;
  padding: 20px 14px;
  background:
    radial-gradient(circle at 18% 0%, rgba(255, 255, 255, 0.72), transparent 42%),
    rgba(255, 255, 255, 0.3);
  border-right: 1px solid rgba(255, 255, 255, 0.48);
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.home-link {
  width: 30px;
  height: 30px;
  border: 1px solid rgba(255, 255, 255, 0.62);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.46);
  color: #163f8f;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 800;
  flex-shrink: 0;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.home-link:hover {
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);
  transform: translateY(-1px);
}

.brand {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: #163f8f;
}

.new-chat-btn {
  height: 48px;
  border: 1px solid rgba(255, 255, 255, 0.58);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.46);
  color: #123b86;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow:
    0 12px 24px rgba(22, 63, 143, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  transition: all 0.2s ease;
}

.new-chat-btn:hover {
  background: rgba(255, 255, 255, 0.68);
  transform: translateY(-1px);
}

.plus {
  margin-right: 6px;
  font-size: 18px;
}

/* 最近对话 */
.recent-section {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.recent-list {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.delete-icon {
  cursor: pointer;
  color: rgba(22, 63, 143, 0.56);
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}


.recent-item:hover {
  background: rgba(255, 255, 255, 0.42);
}

.recent-item.active {
  background: rgba(255, 255, 255, 0.58);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
}

.chat-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  border: 1.5px solid #5f8fc3;
  flex-shrink: 0;
}

.recent-text {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.recent-time {
  color: rgba(22, 63, 143, 0.56);
  font-size: 12px;
}

/* 主区域 */
.main {
  position: relative;
  z-index: 1;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.2);
}

.topbar {
  height: 68px;
  padding: 0 34px;
  background: rgba(255, 255, 255, 0.72);
  border-bottom: 1px solid rgba(196, 226, 248, 0.38);
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.topbar h1 {
  margin: 0;
  color: #163f8f;
  font-size: 20px;
  font-weight: 700;
}

/* 聊天内容 */
.chat-content {
  flex: 1;
  padding: 34px 56px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 26px;
  background:
    radial-gradient(ellipse 48% 32% at 14% 16%, rgba(196, 226, 248, 0.14), transparent 70%),
    rgba(255, 255, 255, 0.44);
}

.message-row {
  display: flex;
  gap: 14px;
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
  background: rgba(255, 255, 255, 0.5);
  color: #163f8f;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
}

.message-body {
  max-width: 560px;
}

.bubble {
  padding: 16px 18px;
  border-radius: 18px;
  font-size: 15px;
  line-height: 1.8;
  border: 1px solid rgba(255, 255, 255, 0.54);
  backdrop-filter: blur(16px) saturate(145%);
  -webkit-backdrop-filter: blur(16px) saturate(145%);
  box-shadow:
    0 10px 24px rgba(22, 63, 143, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.58);
}

.assistant .bubble {
  background: rgba(255, 255, 255, 0.48);
  color: #163f8f;
  border-top-left-radius: 6px;
}

.user .bubble {
  background: rgba(255, 255, 255, 0.62);
  color: #123b86;
  border-top-right-radius: 6px;
}

.file-bubble {
  width: min(520px, 100%);
  padding: 16px;
  border: 1px solid rgba(196, 226, 248, 0.58);
  border-radius: 18px;
  border-top-left-radius: 6px;
  background: rgba(255, 255, 255, 0.62);
  color: #163f8f;
  backdrop-filter: blur(16px) saturate(145%);
  -webkit-backdrop-filter: blur(16px) saturate(145%);
  box-shadow:
    0 10px 24px rgba(22, 63, 143, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.62);
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
  color: #163f8f;
  font-size: 15px;
  line-height: 1.35;
  word-break: break-word;
}

.file-title span,
.file-placeholder {
  color: rgba(22, 63, 143, 0.62);
  font-size: 12px;
}

.file-preview {
  max-height: 260px;
  margin: 14px 0 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid rgba(196, 226, 248, 0.52);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.58);
  color: #163f8f;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.file-placeholder {
  margin-top: 12px;
}

.file-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.file-actions a {
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: #163f8f;
  color: #ffffff;
  text-decoration: none;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.bubble p {
  margin: 0;
}

.bubble ol,
.bubble ul {
  margin: 10px 0;
  padding-left: 22px;
}

.bubble li {
  margin: 4px 0;
}

.rich-bubble {
  min-width: min(420px, 100%);
  white-space: normal;
}

.bubble-footer {
  margin-top: 10px !important;
}

.markdown-body :deep(p) {
  margin: 0;
  color: #163f8f;
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
  border-left: 3px solid #5f8fc3;
  color: #163f8f;
  line-height: 1.45;
}

.markdown-body :deep(h3:first-child),
.markdown-body :deep(h4:first-child),
.markdown-body :deep(h5:first-child),
.markdown-body :deep(h6:first-child) {
  margin-top: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 10px 0 0;
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin: 5px 0;
  padding-left: 2px;
  color: #163f8f;
}

.markdown-body :deep(blockquote) {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-left: 3px solid #5f8fc3;
  background: rgba(255, 255, 255, 0.34);
  color: #163f8f;
  border-radius: 6px;
}

.markdown-body :deep(code) {
  padding: 2px 5px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.52);
  color: #163f8f;
  font-family:
    "SFMono-Regular",
    Consolas,
    "Liberation Mono",
    monospace;
  font-size: 0.92em;
}

.markdown-body :deep(.md-code-block) {
  margin-top: 12px;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.52);
  background: rgba(255, 255, 255, 0.38);
}

.markdown-body :deep(.md-code-block span) {
  display: block;
  padding: 7px 12px;
  color: #5f8fc3;
  font-size: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.48);
}

.markdown-body :deep(pre) {
  margin: 0;
  padding: 14px;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
  color: #163f8f;
  white-space: pre;
}

.markdown-body :deep(a) {
  color: #163f8f;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.markdown-body :deep(.md-table-wrap) {
  margin-top: 12px;
  overflow-x: auto;
  border: 1px solid rgba(255, 255, 255, 0.52);
  border-radius: 8px;
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
  border-bottom: 1px solid rgba(255, 255, 255, 0.48);
  border-right: 1px solid rgba(255, 255, 255, 0.48);
  text-align: left;
  vertical-align: top;
}

.markdown-body :deep(th) {
  color: #163f8f;
  background: rgba(255, 255, 255, 0.5);
  font-weight: 700;
}

.markdown-body :deep(td) {
  color: #163f8f;
}

.message-time {
  margin-top: 6px;
  color: rgba(22, 63, 143, 0.68);
  font-size: 12px;
}

.user .message-time {
  text-align: right;
}

/* 输入框 */
.input-area {
  padding: 18px 56px 28px;
  background: rgba(255, 255, 255, 0.46);
}

.input-box {
  padding: 14px 16px;
  border: 1.5px solid rgba(196, 226, 248, 0.54);
  background: rgba(255, 255, 255, 0.78);
  border-radius: 18px;
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
  box-shadow:
    0 14px 36px rgba(22, 63, 143, 0.13),
    inset 0 1px 0 rgba(255, 255, 255, 0.66);
}

textarea {
  width: 100%;
  min-height: 28px;
  resize: none;
  border: none;
  outline: none;
  background: transparent;
  color: #123b86;
  font-size: 14px;
  line-height: 1.6;
  font-family: inherit;
}

textarea::placeholder {
  color: rgba(22, 63, 143, 0.48);
}

.input-actions {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left-tools {
  display: flex;
  gap: 8px;
}

.left-tools button {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #163f8f;
  font-size: 17px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.left-tools button:hover {
  background: rgba(255, 255, 255, 0.52);
}

.send-btn {
  width: 44px;
  height: 38px;
  border: none;
  border-radius: 12px;
  background: #163f8f;
  color: #ffffff;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.send-btn:hover {
  background: #1d5dab;
  transform: translateY(-1px);
}

.send-btn:disabled {
  background: rgba(22, 63, 143, 0.48);
  cursor: not-allowed;
  transform: none;
}

/* 简单响应式 */
@media (max-width: 900px) {
  .sidebar {
    width: 200px;
  }

  .chat-content {
    padding: 28px;
  }

  .input-area {
    padding: 16px 28px 24px;
  }

}

@media (max-width: 700px) {
  .sidebar {
    display: none;
  }

  .chat-content {
    padding: 20px;
  }

  .input-area {
    padding: 14px 20px 20px;
  }

  .message-body {
    max-width: 86%;
  }

}

/* //补充 */
.recent-item {
  min-height: 56px;
  padding: 9px 10px;
  display: flex;
  align-items: center;
  gap: 9px;
  border-radius: 12px;
  font-size: 13px;
  color: #163f8f;
  cursor: pointer;
  transition: all 0.2s ease;
}

.recent-item:hover {
  background: rgba(255, 255, 255, 0.42);
}

.recent-item.active {
  background: rgba(255, 255, 255, 0.58);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
}

.recent-main {
  flex: 1;
  min-width: 0;
}

.recent-title {
  color: #123b86;
  font-weight: 600;
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

.empty-history {
  padding: 16px 10px;
  color: rgba(22, 63, 143, 0.62);
  font-size: 13px;
}

.history-loading {
  margin: auto;
  color: #ffffff;
  font-size: 14px;
}
</style>
