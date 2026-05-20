<template>
  <div class="chat-page">
    <header class="sketch-topbar">
      <div class="topbar-left">
        <router-link class="round-icon-btn home-link" to="/" aria-label="返回首页">
          <CircleUserRound :size="34" stroke-width="1.35" />
        </router-link>
        <button class="menu-btn" type="button" aria-label="打开最近对话" @click="showHistoryPanel = !showHistoryPanel">
          <Menu :size="34" stroke-width="1.25" />
        </button>
      </div>
      <button class="round-icon-btn profile-btn" type="button" aria-label="个人中心">
        <CircleUserRound :size="44" stroke-width="1.2" />
      </button>
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
    <h1>ready to create your learning<br>resources ?</h1>
    <div class="resource-hero-visual" aria-hidden="true">
      <img :src="resourceHeroImage" alt="" />
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
            <button v-if="message.downloadUrl" type="button" @click="downloadGeneratedFile(message)">下载</button>
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
    <button class="add-btn" type="button" title="生成学习资源" @click="openResourceSidebar">
      <Plus :size="34" stroke-width="1.6" />
    </button>

    <textarea
      v-model="inputValue"
      rows="1"
      placeholder="Ask anything..."
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
    <ResourceSidebar
      :visible="showResourceSidebar"
      :contextTopic="resourceTopic"
      @toggle="showResourceSidebar = !showResourceSidebar"
    />
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import {
  streamChatMessage,
  streamResourceGeneration,
  generateImage,
  getConversationList,
  getConversationMessages,
  resolveApiUrl
} from '../api/apis'
import ResourceSidebar from '../components/ResourceSidebar.vue'
import {
  CircleUserRound,
  FileText,
  GitBranch,
  Image,
  Menu,
  Mic,
  MoreHorizontal,
  Music,
  Plus,
  Presentation,
  SendHorizontal,
  Video
} from 'lucide-vue-next'
import resourceHeroImage from '../assets/pic/资源生成背景.png'

const showResourceSidebar = ref(false)
const showHistoryPanel = ref(false)
const resourceTopic = ref('')
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
    label: 'mindmap',
    icon: GitBranch,
    prompt: '帮我生成一份思维导图：',
    generateMode: 'resource',
    resourceTypes: ['mindmap']
  }
]

const selectResourceTool = tool => {
  selectedResourceTool.value = tool
  inputValue.value = inputValue.value.trim()
    ? `${inputValue.value.trim()} ${tool.prompt}`
    : tool.prompt
}

const stripTypedResourceInstruction = value => {
  return String(value || '').replace(/\n\n【生成类型指令】[\s\S]*$/, '')
}

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
          content: stripTypedResourceInstruction(item.req),
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
      title: stripTypedResourceInstruction(firstRecord.req) || `对话 ${groupId}`,
      lastMessage: stripTypedResourceInstruction(lastRecord.req) || lastRecord.res || '',
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
    fileId,
    previewUrl: resolveApiUrl(data.preview_url || data.previewUrl || data.preview || ''),
    downloadUrl: resolveApiUrl(data.download_url || data.downloadUrl || data.url || (fileId ? `/resource/${fileId}/download` : '')),
    time: getNowTime()
  }
}

const appendFileMessage = fileData => {
  const fileMessage = normalizeFileMessage(fileData)
  const existingIndex = messages.value.findIndex(item => {
    return item.type === 'file' && item.fileId && item.fileId === fileMessage.fileId
  })

  if (existingIndex === -1) {
    messages.value.push(fileMessage)
    return
  }

  messages.value[existingIndex] = {
    ...messages.value[existingIndex],
    ...fileMessage,
    content: fileMessage.content || messages.value[existingIndex].content
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
    const token = localStorage.getItem('token')
    const response = await fetch(message.downloadUrl, {
      headers: {
        ...(token ? { token } : {})
      }
    })

    if (!response.ok) {
      throw new Error(`下载失败：${response.status}`)
    }

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = getDownloadName(message)
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('下载生成文件失败：', error)
    window.alert('下载失败，请确认登录状态和后端服务是否正常。')
  }
}

const extractToolTopic = (text, tool) => {
  const rawText = String(text || '').trim()
  const prompt = String(tool?.prompt || '').trim()

  if (prompt && rawText.startsWith(prompt)) {
    return rawText.slice(prompt.length).trim()
  }

  return rawText
}

const normalizeImageRecords = res => {
  const data = getResponseData(res)
  const list = Array.isArray(data) ? data : data?.data || data?.records || []

  return Array.isArray(list) ? list : []
}

const renderGeneratedImages = records => {
  if (!records.length) return '图片生成完成，但后端没有返回可展示的图片地址。'

  const links = records
    .map((item, index) => {
      const filename = item.filename || `生成图片 ${index + 1}`
      const url = item.url || item.image_url || item.imageUrl || ''

      return url ? `- [${filename}](${url})` : `- ${filename}`
    })
    .join('\n')

  return `已生成 ${records.length} 张图片：\n${links}`
}

const sendImageGeneration = async (target, text, tool) => {
  const prompt = extractToolTopic(text, tool)

  if (!prompt) {
    target.content = '请在 image 后面补充图片描述，比如“帮我生成一张学习配图：细胞结构示意图”。'
    return
  }

  target.content = '正在调用图片生成接口...'
  const result = await generateImage({
    prompt,
    aspect_ratio: tool.aspectRatio || '1:1',
    img_count: tool.imageCount || 1
  })

  target.content = renderGeneratedImages(normalizeImageRecords(result))
  target.time = getNowTime()
}

const sendResourceGeneration = async (target, text, tool) => {
  const topic = extractToolTopic(text, tool)
  const resourceTypes = tool.resourceTypes || ['document']

  if (!topic && !activeConversationId.value) {
    target.content = `请先补充要生成的主题，再点击发送。`
    return
  }

  target.content = `正在生成 ${resourceTypes.join(' / ')} 学习资源...`
  let hasFile = false

  await streamResourceGeneration(
    {
      topic,
      resource_types: resourceTypes,
      chat_group_id: activeConversationId.value || 0
    },
    {
      onProgress: async eventData => {
        const finished = Array.isArray(eventData.resources) ? eventData.resources : []
        target.content = finished.length
          ? `正在生成学习资源，已完成：${finished.join(' / ')}`
          : `正在生成 ${resourceTypes.join(' / ')} 学习资源...`
        target.time = getNowTime()
        await scrollToBottom()
      },
      onFile: async fileData => {
        hasFile = true
        appendFileMessage(fileData)
        target.content = '已生成文件，可以在下方查看预览。'
        target.time = getNowTime()
        await scrollToBottom()
      },
      onDone: async eventData => {
        if (eventData?.resources && Array.isArray(eventData.resources)) {
          eventData.resources.forEach(appendFileMessage)
          hasFile = true
        }

        if (!hasFile) {
          target.content = '学习资源生成完成。'
        }

        target.time = getNowTime()
        await scrollToBottom()
      }
    }
  )
}

const sendBackendGeneration = async (target, text, tool) => {
  if (tool.generateMode === 'image') {
    await sendImageGeneration(target, text, tool)
    return
  }

  await sendResourceGeneration(target, text, tool)
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

  const activeTool = selectedResourceTool.value
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
      await sendBackendGeneration(target, text, activeTool)
      await scrollToBottom()
      return
    }

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

        appendFileMessage(fileData)
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
  background: transparent;
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
  content: none;
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

.file-actions a,
.file-actions button {
  min-height: 30px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: #163f8f;
  color: #ffffff;
  text-decoration: none;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  font-family: inherit;
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

/* sketch redesign */
.chat-page {
  padding: 36px 52px;
  background: #fbfbf8;
  color: #282828;
  display: block;
}

.chat-page::after {
  content: "";
  position: absolute;
  inset: 36px 52px;
  border: 1.5px solid #737373;
  border-radius: 12px;
  pointer-events: none;
}

.sketch-topbar {
  position: relative;
  z-index: 4;
  height: 74px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 17px 38px 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 44px;
}

.round-icon-btn,
.menu-btn,
.add-btn,
.voice-btn,
.send-btn,
.more-tool {
  border: none;
  background: transparent;
  color: #282828;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-family: inherit;
}

.round-icon-btn {
  width: 66px;
  height: 66px;
  color: #4b4b4b;
  text-decoration: none;
}

.profile-btn {
  width: 84px;
  height: 84px;
}

.menu-btn {
  width: 74px;
  height: 54px;
}

.history-panel {
  position: absolute;
  z-index: 5;
  top: 126px;
  left: 90px;
  width: 310px;
  max-height: calc(100vh - 190px);
  padding: 16px;
  border: 1.5px solid #8b8b8b;
  border-radius: 10px;
  background: rgba(251, 251, 248, 0.94);
  box-shadow: 0 18px 46px rgba(34, 34, 34, 0.12);
  opacity: 0;
  transform: translateY(-8px);
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.history-panel.open {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

.new-chat-btn {
  width: 100%;
  height: 42px;
  border: 1.5px solid #8b8b8b;
  border-radius: 8px;
  background: transparent;
  color: #282828;
  box-shadow: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.new-chat-btn:hover,
.recent-item:hover,
.recent-item.active {
  background: #f2f2ee;
  box-shadow: none;
  transform: none;
}

.section-title,
.empty-history,
.recent-title,
.recent-desc,
.recent-time {
  color: #282828;
}

.main {
  position: relative;
  z-index: 2;
  height: calc(100vh - 110px);
  background: transparent;
}

.chat-content {
  height: calc(100% - 202px);
  padding: 72px min(12vw, 150px) 24px;
  background: transparent;
  gap: 22px;
}

.empty-chat {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transform: translateY(-18px);
}

.empty-chat h1 {
  margin: 0 0 16px;
  color: #242424;
  font-family: "Comic Sans MS", "Bradley Hand ITC", "Segoe Print", cursive;
  font-size: clamp(32px, 3vw, 50px);
  font-weight: 600;
  line-height: 1.28;
  letter-spacing: 0;
}

.learning-doodle {
  position: relative;
  width: min(56vw, 720px);
  min-width: 420px;
  aspect-ratio: 1.75;
  color: #2a2a2a;
}

.learning-doodle > div,
.learning-doodle span {
  position: absolute;
  border-color: currentColor;
}

.book {
  left: 10%;
  top: 28%;
  width: 31%;
  height: 43%;
  border-bottom: 3px solid currentColor;
  transform: rotate(-2deg);
}

.book::before,
.book::after {
  content: "";
  position: absolute;
  bottom: 5%;
  width: 48%;
  height: 88%;
  border: 2px solid currentColor;
  border-bottom-left-radius: 28px;
  border-bottom-right-radius: 12px;
}

.book::before {
  left: 0;
  border-right: none;
  transform: skewY(-8deg);
}

.book::after {
  right: 0;
  border-left: none;
  transform: skewY(5deg);
}

.book span {
  left: 9%;
  width: 23%;
  height: 2px;
  background: currentColor;
  border: none;
  transform: rotate(-22deg);
}

.book span:nth-child(1) { top: 28%; }
.book span:nth-child(2) { top: 43%; }
.book span:nth-child(3) { top: 58%; }

.image-card {
  left: 42%;
  top: 18%;
  width: 24%;
  height: 50%;
  border: 3px solid currentColor;
  border-radius: 8px;
  transform: rotate(7deg);
}

.image-card .sun {
  right: 18%;
  top: 20%;
  width: 34px;
  height: 34px;
  border: 2px solid currentColor;
  border-radius: 50%;
}

.image-card .mountain {
  bottom: 15%;
  height: 2px;
  background: currentColor;
  border: none;
  transform-origin: left center;
}

.image-card .mountain.one {
  left: 9%;
  width: 46%;
  transform: rotate(-42deg);
}

.image-card .mountain.two {
  left: 43%;
  width: 43%;
  transform: rotate(52deg);
}

.video-card {
  left: 68%;
  top: 18%;
  width: 18%;
  height: 36%;
  border: 3px solid currentColor;
  transform: rotate(-8deg);
}

.video-card span {
  left: 28%;
  top: 27%;
  width: 0;
  height: 0;
  border-top: 28px solid transparent;
  border-bottom: 28px solid transparent;
  border-left: 40px solid currentColor;
}

.paper-card {
  left: 65%;
  top: 50%;
  width: 21%;
  height: 32%;
  border-left: 3px solid currentColor;
  transform: rotate(-20deg);
}

.paper-card span,
.paper-lines span {
  left: 13%;
  width: 74%;
  height: 2px;
  background: currentColor;
  border: none;
}

.paper-card span:nth-child(1) { top: 12%; }
.paper-card span:nth-child(2) { top: 28%; }
.paper-card span:nth-child(3) { top: 44%; }
.paper-card span:nth-child(4) { top: 61%; }

.note {
  width: 38px;
  height: 56px;
  border-left: 4px solid currentColor;
  border-bottom: 4px solid currentColor;
  border-radius: 0 0 18px 18px;
}

.note.one {
  left: 49%;
  top: 68%;
  transform: rotate(4deg);
}

.note.two {
  left: 61%;
  top: 56%;
  transform: rotate(-4deg);
}

.pen {
  left: 76%;
  top: 54%;
  width: 24%;
  height: 20px;
  border: 3px solid currentColor;
  border-left: none;
  border-radius: 0 16px 16px 0;
}

.paper-lines {
  left: 86%;
  top: 63%;
  width: 18%;
  height: 26%;
}

.paper-lines span:nth-child(1) { top: 8%; }
.paper-lines span:nth-child(2) { top: 32%; }
.paper-lines span:nth-child(3) { top: 56%; }

.input-area {
  position: relative;
  z-index: 3;
  padding: 0 0 32px;
  background: transparent;
  display: flex;
  justify-content: center;
}

.input-box {
  position: relative;
  width: min(54vw, 970px);
  min-width: 560px;
  min-height: 180px;
  padding: 28px 26px 24px;
  border: 1.5px solid #8b8b8b;
  border-radius: 12px;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.add-btn {
  position: absolute;
  left: 20px;
  top: 28px;
  width: 38px;
  height: 38px;
}

textarea {
  min-height: 58px;
  padding: 4px 84px 0 54px;
  color: #282828;
  font-size: 16px;
}

textarea::placeholder {
  color: #9a9a9a;
}

.input-actions {
  margin-top: 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.quick-tools {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 32px;
  flex-wrap: wrap;
}

.quick-tool {
  height: 36px;
  min-width: 92px;
  padding: 0 14px;
  border: 1.5px solid #8b8b8b;
  border-radius: 7px;
  background: transparent;
  color: #282828;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-family: "Comic Sans MS", "Bradley Hand ITC", "Segoe Print", cursive;
  font-size: 13px;
  cursor: pointer;
}

.quick-tool:hover,
.more-tool:hover,
.voice-btn:hover,
.send-btn:hover {
  background: #f2f2ee;
  transform: none;
}

.more-tool,
.voice-btn,
.send-btn {
  width: 38px;
  height: 38px;
  border: 1.5px solid #8b8b8b;
  border-radius: 50%;
}

.right-tools {
  position: absolute;
  right: 18px;
  top: 28px;
  display: flex;
  gap: 10px;
}

.send-btn {
  background: transparent;
  color: #282828;
}

.send-btn:disabled {
  background: transparent;
  color: #9b9b9b;
  cursor: not-allowed;
}

.message-body {
  max-width: min(720px, 82%);
}

.bubble,
.file-bubble {
  border-color: #d4d4d0;
  background: #ffffff;
  color: #282828;
  box-shadow: none;
  backdrop-filter: none;
}

.assistant .bubble,
.user .bubble,
.file-bubble {
  background: #ffffff;
  color: #282828;
}

.ai-avatar {
  background: #ffffff;
  border: 1px solid #d4d4d0;
  color: #282828;
}

.history-loading {
  color: #555;
}

@media (max-width: 980px) {
  .chat-page {
    padding: 18px;
  }

  .chat-page::after {
    inset: 18px;
  }

  .sketch-topbar {
    padding: 14px 24px 0;
  }

  .chat-content {
    padding: 58px 28px 22px;
  }

  .learning-doodle {
    width: 82vw;
    min-width: 300px;
  }

  .input-box {
    width: calc(100vw - 72px);
    min-width: 0;
  }

  .quick-tools {
    gap: 12px;
  }
}

@media (max-width: 640px) {
  .topbar-left {
    gap: 18px;
  }

  .round-icon-btn {
    width: 48px;
    height: 48px;
  }

  .profile-btn {
    width: 58px;
    height: 58px;
  }

  .main {
    height: calc(100vh - 74px);
  }

  .chat-content {
    height: calc(100% - 230px);
    padding: 34px 18px 12px;
  }

  .empty-chat h1 {
    font-size: 28px;
  }

  .input-box {
    width: calc(100vw - 48px);
    min-height: 210px;
  }

  .quick-tool {
    min-width: 76px;
    padding: 0 10px;
  }

  .history-panel {
    left: 28px;
    width: calc(100vw - 56px);
  }
}

/* resource generation visual refresh */
.chat-page {
  padding: 28px 34px;
  background:
    radial-gradient(ellipse 72% 44% at 10% 0%, rgba(209, 244, 250, 0.46), transparent 70%),
    linear-gradient(135deg, #fafafa 0%, rgb(237, 249, 252) 52%, #fafafa 100%);
  color: #163f8f;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.chat-page::after {
  content: none;
}

.sketch-topbar {
  height: 86px;
  padding: 0;
  align-items: center;
}

.topbar-left {
  gap: 18px;
}

.round-icon-btn,
.menu-btn,
.profile-btn {
  border: 1px solid rgba(22, 63, 143, 0.16);
  background: rgba(250, 250, 250, 0.78);
  color: #163f8f;
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

.round-icon-btn,
.profile-btn {
  width: 70px;
  height: 70px;
  border-radius: 50%;
}

.menu-btn {
  width: 70px;
  height: 54px;
  border-radius: 18px;
}

.round-icon-btn:hover,
.menu-btn:hover,
.profile-btn:hover {
  background: #c9dce9;
  border-color: #5f8fc3;
  transform: translateY(-2px);
}

.history-panel {
  top: 116px;
  left: 34px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 24px;
  background: rgba(250, 250, 250, 0.9);
  color: #163f8f;
  box-shadow:
    0 18px 46px rgba(22, 63, 143, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}

.new-chat-btn,
.recent-item {
  border-color: rgba(201, 220, 233, 0.72);
  border-radius: 14px;
  color: #163f8f;
}

.new-chat-btn:hover,
.recent-item:hover,
.recent-item.active {
  background: rgba(201, 220, 233, 0.62);
}

.section-title,
.empty-history,
.recent-title,
.recent-desc,
.recent-time {
  color: #163f8f;
}

.chat-dot {
  border-color: #5f8fc3;
  background: #c9dce9;
}

.main {
  height: calc(100vh - 142px);
}

.chat-content {
  height: calc(100% - 190px);
  padding: 16px min(10vw, 130px) 24px;
  justify-content: center;
}

.empty-chat {
  min-height: 0;
  transform: none;
}

.empty-chat h1 {
  margin: 0 0 24px;
  color: #163f8f;
  font-family: inherit;
  font-size: clamp(34px, 4.2vw, 62px);
  font-weight: 900;
  line-height: 1.12;
  text-align: center;
}

.learning-doodle {
  width: min(62vw, 780px);
  min-width: 520px;
  aspect-ratio: 2.18;
  border-radius: 34px;
  background:
    linear-gradient(135deg, rgba(250, 250, 250, 0.92), rgba(237, 249, 252, 0.82)),
    #fafafa;
  border: 1px solid rgba(22, 63, 143, 0.14);
  box-shadow:
    0 24px 58px rgba(22, 63, 143, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
  overflow: hidden;
}

.learning-doodle::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 16% 18%, rgba(201, 220, 233, 0.72), transparent 22%),
    radial-gradient(circle at 86% 78%, rgba(240, 239, 221, 0.9), transparent 24%);
  opacity: 0.9;
}

.learning-doodle > div,
.learning-doodle span {
  border-color: transparent;
}

.book,
.image-card,
.video-card,
.paper-card,
.paper-lines {
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 24px;
  background: rgba(250, 250, 250, 0.88);
  box-shadow:
    0 16px 30px rgba(22, 63, 143, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.76);
}

.book {
  left: 8%;
  top: 28%;
  width: 27%;
  height: 48%;
  border-bottom: 1px solid rgba(22, 63, 143, 0.16);
  transform: rotate(-5deg);
}

.book::before,
.book::after {
  content: "";
  position: absolute;
  inset: 18px auto 18px;
  width: 42%;
  border-radius: 16px;
  border: 1px solid rgba(95, 143, 195, 0.34);
  background: linear-gradient(180deg, rgba(201, 220, 233, 0.5), rgba(250, 250, 250, 0.72));
}

.book::before {
  left: 16px;
}

.book::after {
  right: 16px;
}

.book span,
.paper-card span,
.paper-lines span {
  height: 7px;
  border-radius: 999px;
  border: 0;
  background: #c9dce9;
  transform: none;
}

.book span {
  left: 12%;
  width: 28%;
}

.book span:nth-child(1) { top: 30%; }
.book span:nth-child(2) { top: 46%; }
.book span:nth-child(3) { top: 62%; }

.image-card {
  left: 35%;
  top: 16%;
  width: 28%;
  height: 62%;
  transform: rotate(4deg);
  background:
    linear-gradient(145deg, rgba(201, 220, 233, 0.52), rgba(250, 250, 250, 0.9));
}

.image-card .sun {
  right: 18%;
  top: 18%;
  width: 46px;
  height: 46px;
  border: 0;
  border-radius: 50%;
  background: #f0efdd;
  box-shadow: inset 0 0 0 8px rgba(250, 250, 250, 0.6);
}

.image-card .mountain {
  bottom: 18%;
  height: 38%;
  border: 0;
  border-radius: 18px 18px 0 0;
  transform: none;
}

.image-card .mountain.one {
  left: 10%;
  width: 48%;
  background: #163f8f;
  clip-path: polygon(0 100%, 52% 0, 100% 100%);
}

.image-card .mountain.two {
  left: 40%;
  width: 48%;
  background: #5f8fc3;
  clip-path: polygon(0 100%, 48% 12%, 100% 100%);
}

.video-card {
  left: 66%;
  top: 18%;
  width: 23%;
  height: 34%;
  transform: rotate(-5deg);
  background: #163f8f;
}

.video-card span {
  left: 40%;
  top: 30%;
  width: 0;
  height: 0;
  border-top: 22px solid transparent;
  border-bottom: 22px solid transparent;
  border-left: 34px solid #fafafa;
}

.paper-card {
  left: 63%;
  top: 50%;
  width: 22%;
  height: 34%;
  transform: rotate(-13deg);
  background: rgba(250, 250, 250, 0.94);
}

.paper-card span {
  left: 16%;
  width: 68%;
}

.paper-card span:nth-child(1) { top: 18%; }
.paper-card span:nth-child(2) { top: 35%; }
.paper-card span:nth-child(3) { top: 52%; }
.paper-card span:nth-child(4) { top: 69%; }

.note {
  width: 58px;
  height: 58px;
  border: 0;
  border-radius: 18px;
  background: #5f8fc3;
  box-shadow: 0 12px 24px rgba(22, 63, 143, 0.12);
}

.note.one {
  left: 47%;
  top: 70%;
  transform: rotate(8deg);
}

.note.two {
  left: 56%;
  top: 63%;
  background: #f0efdd;
  transform: rotate(-8deg);
}

.pen {
  left: 78%;
  top: 63%;
  width: 16%;
  height: 18px;
  border: 0;
  border-radius: 999px;
  background: #163f8f;
  transform: rotate(-2deg);
  box-shadow: 0 10px 18px rgba(22, 63, 143, 0.14);
}

.paper-lines {
  left: 84%;
  top: 58%;
  width: 14%;
  height: 28%;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.paper-lines span {
  left: 0;
  width: 100%;
  background: rgba(95, 143, 195, 0.46);
}

.paper-lines span:nth-child(1) { top: 18%; }
.paper-lines span:nth-child(2) { top: 42%; }
.paper-lines span:nth-child(3) { top: 66%; }

.input-area {
  padding: 0;
}

.input-box {
  width: min(68vw, 1080px);
  min-width: 620px;
  min-height: 168px;
  padding: 26px 24px 22px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 24px;
  background: rgba(250, 250, 250, 0.88);
  box-shadow:
    0 18px 44px rgba(22, 63, 143, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(16px) saturate(138%);
  -webkit-backdrop-filter: blur(16px) saturate(138%);
}

.add-btn {
  left: 22px;
  top: 24px;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(201, 220, 233, 0.8);
  border-radius: 14px;
  background: #fafafa;
  color: #163f8f;
}

textarea {
  min-height: 54px;
  padding: 4px 96px 0 58px;
  color: #163f8f;
  font-size: 16px;
}

textarea::placeholder {
  color: rgba(22, 63, 143, 0.5);
}

.quick-tools {
  gap: 14px;
}

.quick-tool {
  min-width: 104px;
  height: 38px;
  border: 1px solid rgba(201, 220, 233, 0.78);
  border-radius: 12px;
  background: #fafafa;
  color: #163f8f;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.quick-tool:hover,
.more-tool:hover,
.voice-btn:hover,
.send-btn:hover,
.add-btn:hover {
  background: #c9dce9;
  border-color: #5f8fc3;
}

.right-tools {
  right: 22px;
  top: 24px;
}

.more-tool,
.voice-btn,
.send-btn {
  border: 1px solid rgba(201, 220, 233, 0.78);
  background: #fafafa;
  color: #163f8f;
}

.send-btn:not(:disabled) {
  background: #163f8f;
  border-color: #163f8f;
  color: #fafafa;
}

.send-btn:disabled {
  color: rgba(22, 63, 143, 0.36);
}

.bubble,
.file-bubble {
  border: 1px solid rgba(201, 220, 233, 0.78);
  border-radius: 18px;
  background: rgba(250, 250, 250, 0.92);
  color: #163f8f;
  box-shadow: 0 12px 28px rgba(22, 63, 143, 0.1);
}

.assistant .bubble,
.user .bubble,
.file-bubble {
  background: rgba(250, 250, 250, 0.92);
  color: #163f8f;
}

.ai-avatar {
  border-color: rgba(201, 220, 233, 0.78);
  background: #163f8f;
  color: #fafafa;
}

@media (max-width: 980px) {
  .chat-page {
    padding: 18px;
  }

  .learning-doodle {
    width: 86vw;
    min-width: 300px;
  }

  .input-box {
    width: calc(100vw - 52px);
    min-width: 0;
  }
}

@media (max-width: 640px) {
  .chat-content {
    height: calc(100% - 228px);
    padding: 20px 10px 12px;
  }

  .empty-chat h1 {
    font-size: 30px;
  }

  .learning-doodle {
    aspect-ratio: 1.45;
  }

  .input-box {
    min-height: 212px;
  }

  .quick-tools {
    gap: 8px;
  }

  .quick-tool {
    min-width: 82px;
  }
}

.empty-chat {
  gap: 4px;
}

.empty-chat h1 {
  margin-bottom: 10px;
  font-family: "Comic Sans MS", "Segoe Print", "Bradley Hand ITC", cursive;
  font-size: clamp(28px, 2.65vw, 42px);
  font-weight: 700;
  line-height: 1.22;
  color: #25344a;
  text-align: left;
  align-self: center;
  letter-spacing: 0;
}

.resource-hero-visual {
  position: relative;
  width: min(58vw, 760px);
  min-width: 520px;
  background: transparent;
  box-shadow: none;
  overflow: visible;
}

.resource-hero-visual::before {
  content: none;
}

.resource-hero-visual img {
  position: relative;
  z-index: 1;
  width: 100%;
  display: block;
  object-fit: contain;
  filter: saturate(0.98) contrast(0.98) brightness(1.03);
  mix-blend-mode: multiply;
}

@media (max-width: 980px) {
  .resource-hero-visual {
    width: min(86vw, 760px);
    min-width: 300px;
  }
}

@media (max-width: 640px) {
  .empty-chat h1 {
    font-size: 24px;
    text-align: center;
  }

  .resource-hero-visual {
    border-radius: 20px;
  }
}

/* web UI polish */
.chat-page {
  --page-pad-x: clamp(20px, 3vw, 48px);
  --page-pad-y: clamp(18px, 2.4vw, 32px);
  --panel-border: rgba(22, 63, 143, 0.14);
  --panel-bg: rgba(250, 250, 250, 0.82);
  --panel-bg-strong: rgba(255, 255, 255, 0.92);
  --primary: #163f8f;
  --primary-soft: #5f8fc3;
  --surface-soft: #c9dce9;
  --text-main: #163f8f;
  --text-muted: rgba(22, 63, 143, 0.58);
  --shadow-soft: 0 16px 40px rgba(22, 63, 143, 0.1);
  --radius-md: 8px;
  --radius-lg: 18px;
  --radius-xl: 24px;

  padding: var(--page-pad-y) var(--page-pad-x);
  min-width: 320px;
  background:
    radial-gradient(ellipse 70% 42% at 8% 0%, rgba(209, 244, 250, 0.42), transparent 68%),
    linear-gradient(135deg, #fafafa 0%, #edf9fc 54%, #fafafa 100%);
}

.sketch-topbar {
  height: 72px;
  max-width: 1480px;
  margin: 0 auto;
}

.topbar-left {
  gap: 16px;
}

.round-icon-btn,
.profile-btn,
.menu-btn {
  border-color: var(--panel-border);
  background: var(--panel-bg);
  color: var(--primary);
  box-shadow: var(--shadow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.round-icon-btn,
.profile-btn {
  width: 56px;
  height: 56px;
}

.menu-btn {
  width: 56px;
  height: 44px;
  border-radius: var(--radius-lg);
}

.round-icon-btn:hover,
.profile-btn:hover,
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
.profile-btn:focus-visible,
.menu-btn:focus-visible,
.add-btn:focus-visible,
.quick-tool:focus-visible,
.more-tool:focus-visible,
.voice-btn:focus-visible,
.send-btn:focus-visible,
.new-chat-btn:focus-visible,
.recent-item:focus-visible,
textarea:focus-visible {
  outline: 3px solid rgba(95, 143, 195, 0.28);
  outline-offset: 3px;
}

.history-panel {
  top: calc(var(--page-pad-y) + 76px);
  left: var(--page-pad-x);
  width: min(340px, calc(100vw - var(--page-pad-x) * 2));
  max-height: min(560px, calc(100vh - 128px));
  padding: 14px;
  border-radius: var(--radius-xl);
  border-color: var(--panel-border);
  background: rgba(255, 255, 255, 0.92);
}

.new-chat-btn {
  height: 44px;
  border: 1px solid rgba(201, 220, 233, 0.8);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 800;
}

.section-title {
  height: 36px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 800;
}

.recent-list {
  gap: 8px;
}

.recent-item {
  min-height: 62px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
}

.main {
  max-width: 1480px;
  height: calc(100vh - var(--page-pad-y) * 2 - 72px);
  min-height: 560px;
  margin: 0 auto;
}

.chat-content {
  height: calc(100% - 176px);
  min-height: 0;
  padding: clamp(18px, 3.2vh, 42px) clamp(20px, 6vw, 96px) 18px;
  overflow-y: auto;
}

.empty-chat {
  min-height: 100%;
  gap: clamp(6px, 1.2vh, 14px);
  justify-content: center;
}

.empty-chat h1 {
  margin: 0;
  color: #25344a;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: clamp(26px, 2.35vw, 38px);
  font-weight: 500;
  line-height: 1.38;
  text-align: center;
}

.resource-hero-visual {
  width: min(54vw, 720px);
  min-width: 420px;
  max-height: min(34vh, 310px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.resource-hero-visual img {
  max-height: min(34vh, 310px);
  object-fit: contain;
}

.input-area {
  min-height: 176px;
  align-items: flex-start;
}

.input-box {
  width: min(100%, 980px);
  min-width: 0;
  min-height: 148px;
  padding: 22px 22px 18px;
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-xl);
  background: var(--panel-bg-strong);
  box-shadow: var(--shadow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.76);
}

.add-btn,
.more-tool,
.voice-btn,
.send-btn {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  background: #ffffff;
  color: var(--primary);
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.add-btn {
  left: 20px;
  top: 20px;
  border-radius: var(--radius-md);
}

.right-tools {
  right: 20px;
  top: 20px;
}

textarea {
  min-height: 48px;
  max-height: 104px;
  padding: 2px 96px 0 58px;
  color: var(--text-main);
  font-size: 15px;
  line-height: 1.65;
}

.input-actions {
  margin-top: 22px;
  gap: 14px;
}

.quick-tools {
  gap: 10px;
}

.quick-tool {
  min-width: 96px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(201, 220, 233, 0.82);
  border-radius: var(--radius-md);
  background: #ffffff;
  color: var(--primary);
  font-size: 13px;
  font-weight: 800;
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
}

.message-row {
  width: 100%;
}

.message-body {
  max-width: min(760px, 82%);
}

.bubble,
.file-bubble {
  border-radius: var(--radius-lg);
  border-color: rgba(201, 220, 233, 0.82);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 10px 24px rgba(22, 63, 143, 0.08);
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

@media (max-width: 1024px) {
  .main {
    min-height: 520px;
  }

  .resource-hero-visual {
    width: min(76vw, 680px);
    min-width: 320px;
  }

  .quick-tool {
    min-width: 86px;
  }
}

@media (max-width: 760px) {
  .chat-page {
    --page-pad-x: 14px;
    --page-pad-y: 14px;
  }

  .sketch-topbar {
    height: 62px;
  }

  .round-icon-btn,
  .profile-btn {
    width: 46px;
    height: 46px;
  }

  .menu-btn {
    width: 48px;
    height: 40px;
  }

  .main {
    height: calc(100vh - var(--page-pad-y) * 2 - 62px);
    min-height: 0;
  }

  .chat-content {
    height: calc(100% - 218px);
    padding: 16px 4px 10px;
  }

  .empty-chat h1 {
    font-size: clamp(22px, 7vw, 28px);
  }

  .resource-hero-visual {
    width: 100%;
    min-width: 0;
    max-height: 26vh;
  }

  .resource-hero-visual img {
    max-height: 26vh;
  }

  .input-area {
    min-height: 218px;
  }

  .input-box {
    min-height: 206px;
    padding: 18px 16px 16px;
    border-radius: 20px;
  }

  .add-btn {
    left: 16px;
    top: 16px;
  }

  .right-tools {
    right: 16px;
    top: 16px;
  }

  textarea {
    padding-left: 54px;
    padding-right: 92px;
  }

  .input-actions {
    margin-top: 18px;
  }

  .quick-tools {
    gap: 8px;
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
