import request from './request'

const rawBase = request.defaults.baseURL || '/'
const API_BASE_URL = rawBase.endsWith('/') ? rawBase : rawBase + '/'

export const resolveApiUrl = path => {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path

  return new URL(String(path).replace(/^\//, ''), API_BASE_URL).toString()
}

export const normalizeAvatarUrl = avatar => {
  if (!avatar) return ''
  return resolveApiUrl(avatar)
}

export async function downloadWithToken(url, filename = 'download') {
  const href = resolveApiUrl(url)
  const token = localStorage.getItem('token')
  const response = await fetch(href, {
    headers: {
      ...(token ? { token } : {})
    }
  })

  if (!response.ok) {
    throw new Error(`下载失败：${response.status}`)
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

// 登录：后端 Login_User 接收 username/email/password
export function login(data) {
  return request({
    url: '/user/login_user',
    method: 'post',
    data
  })
}

// 注册：后端 Create_User 接收 username/password
export function register(data) {
  return request({
    url: '/user/create_user',
    method: 'post',
    data
  })
}

export function sendEmailCode(data) {
  return request({
    url: '/user/send_email_code',
    method: 'post',
    data
  })
}

export function registerByEmail(data) {
  return request({
    url: '/user/register_by_email',
    method: 'post',
    data
  })
}

// 获取用户资料：后端 Read_User 通过 token 获取 user_id
export function getUserProfile() {
  return request({
    url: '/user/read_user',
    method: 'get'
  })
}

// 更新个人信息：后端 Update_User_Information 接收 username/major/email/phonenum/profile
export function updateUserProfile(data) {
  return request({
    url: '/user/update_user/information',
    method: 'post',
    data
  })
}

export function uploadUserAvatar(file) {
  const data = new FormData()
  data.append('file', file)

  return request({
    url: '/user/avatar',
    method: 'post',
    data
  })
}

export function deleteUserAvatar() {
  return request({
    url: '/user/avatar',
    method: 'delete'
  })
}

// 注销账户：后端 Delete_User 接收 password，用户身份通过 token 获取
export function deleteUser(data) {
  return request({
    url: '/user/delete_user',
    method: 'delete',
    data
  })
}

// AI 聊天消息返回
export function sendChatMessage(data) {
  if (data.chat_group_id) {
    return request.post('/ai_chat/create_msg_into_history', {
      chat_group_id: Number(data.chat_group_id),
      user_req: data.user_req
    })
  }

  return request({
    url: '/ai_chat/create_new_history',
    method: 'post',
    data: {
      user_req: data.user_req
    }
  })
}

// 获取最近历史对话列表
export function getConversationList() {
  return request.get('/ai_chat/read_history_group')
}

// 获取某条对话的完整消息
export function getConversationMessages(chatGroupId) {
  return request.get('/ai_chat/read_messages_from_history', {
    params: {
      chat_group_id: chatGroupId
    }
  })
}

const parseStreamEvent = (eventText) => {
  return eventText
    .split('\n')
    .filter(line => line.startsWith('data:'))
    .map(line => line.replace(/^data:\s*/, '').trim())
    .filter(Boolean)
}

export async function streamChatMessage(data, { onChunk, onDone, onError, onFile } = {}) {
  const isExistingConversation = Boolean(data.chat_group_id)
  const url = `${API_BASE_URL}${isExistingConversation ? 'ai_chat/stream_msg_into_history' : 'ai_chat/stream_new_history'}`
  const token = localStorage.getItem('token')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { token } : {})
    },
    body: isExistingConversation
      ? JSON.stringify({
        chat_group_id: Number(data.chat_group_id),
        user_req: data.user_req
      })
      : JSON.stringify({
        user_req: data.user_req
      })
  })

  if (!response.ok || !response.body) {
    throw new Error(`流式请求失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()

    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split(/\r?\n\r?\n/)
    buffer = events.pop() || ''

    for (const eventText of events) {
      const payloads = parseStreamEvent(eventText)

      for (const payload of payloads) {
        if (payload === '[DONE]') {
          onDone?.({})
          continue
        }

        let eventData

        try {
          eventData = JSON.parse(payload)
        } catch (error) {
          continue
        }

        if (eventData.error) {
          await onError?.(eventData.error)
          throw new Error(eventData.error)
        }

        const isFileEvent =
          eventData.type === 'file' ||
          eventData.event === 'file' ||
          eventData.file_type ||
          eventData.fileType ||
          eventData.filename ||
          eventData.file_id ||
          eventData.fileId ||
          eventData.download_url ||
          eventData.downloadUrl ||
          eventData.preview_url ||
          eventData.previewUrl

        if (isFileEvent) {
          await onFile?.(eventData)
          continue
        }

        if (eventData.content) {
          await onChunk?.(eventData.content)
        }

        if (eventData.done || eventData.type === 'done' || eventData.event === 'done') {
          await onDone?.(eventData)
        }
      }
    }
  }
}

export function getPortrait() {
  return request.get('/ai_portrait/read_portrait')
}

export function getPortraitRadar() {
  return request.get('/ai_portrait/radar')
}

export function initPortrait(data) {
  return request({
    url: '/ai_portrait/init_portrait',
    method: 'post',
    data
  })
}

export function uploadStudyMaterial(data) {
  return request({
    url: '/knowledge_base/upload',
    method: 'post',
    data
  })
}

export function getStudyResources(params = {}) {
  return request({
    url: '/knowledge_base/list',
    method: 'get',
    params
  })
}

export function getStudyStats() {
  return request.get('/study/stats')
}

export function getStudyPathStats() {
  return request.get('/study/path-stats')
}

export function sendStudyHeartbeat(pathId = null) {
  return request({
    url: '/study/heartbeat',
    method: 'post',
    params: pathId ? { path_id: pathId } : {}
  })
}

export function markStudyResourceRead(resourceId, durationSeconds = 0) {
  return request({
    url: `/study/resource/${resourceId}/mark-read`,
    method: 'post',
    params: {
      duration_seconds: Math.max(0, Math.round(Number(durationSeconds || 0)))
    }
  })
}

export function markStudyResourceUnread(resourceId) {
  return request({
    url: `/study/resource/${resourceId}/mark-unread`,
    method: 'post'
  })
}

export function getStudyExamWeekly() {
  return request.get('/study/exam-weekly')
}

export function getLearningGuidance() {
  return request.get('/study/learning-guidance')
}

export function collectStudyResource(resourceId) {
  return request({
    url: `/study/resource/${resourceId}/collect`,
    method: 'post'
  })
}

export function uncollectStudyResource(resourceId) {
  return request({
    url: `/study/resource/${resourceId}/collect`,
    method: 'delete'
  })
}

export function getStudyCollections() {
  return request.get('/study/collections')
}

// ── 学习资源生成（流式）──

export async function streamResourceGeneration(data, { onProgress, onDone, onError, onFile } = {}) {
  const url = `${API_BASE_URL}resource/generate/stream`
  const token = localStorage.getItem('token')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { token } : {})
    },
    body: JSON.stringify({
      topic: data.topic,
      resource_types: data.resource_types,
      chat_group_id: Number(data.chat_group_id || 0)
    })
  })

  if (!response.ok || !response.body) {
    throw new Error(`资源生成请求失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split(/\r?\n\r?\n/)
    buffer = events.pop() || ''

    for (const eventText of events) {
      const payloads = parseStreamEvent(eventText)

      for (const payload of payloads) {
        if (payload === '[DONE]') {
          onDone?.({})
          continue
        }

        let eventData
        try {
          eventData = JSON.parse(payload)
        } catch {
          continue
        }

        if (eventData.error) {
          onError?.(eventData.error)
          throw new Error(eventData.error)
        }

        const isFileEvent =
          eventData.type === 'file' ||
          eventData.event === 'file' ||
          eventData.file_type ||
          eventData.fileType ||
          eventData.filename ||
          eventData.file_id ||
          eventData.fileId ||
          eventData.download_url ||
          eventData.downloadUrl ||
          eventData.preview_url ||
          eventData.previewUrl

        if (isFileEvent && !eventData.done) {
          onFile?.(eventData)
          continue
        }

        if (eventData.resources !== undefined || eventData.review_passed !== undefined) {
          // progress event: {resources: ["ppt","document"], review_passed: false}
          onProgress?.(eventData)
        }

        if (eventData.done || eventData.type === 'done' || eventData.event === 'done') {
          onDone?.(eventData)
        }
      }
    }
  }
}

// 获取已生成的资源列表
export function getGeneratedResources() {
  return request.get('/resource/list')
}

export function getGeneratedResource(resourceId) {
  return request.get(`/resource/${resourceId}`)
}

export function getResourceAnnotations(sourceId, sourceType = 'generated') {
  return request.get('/annotation', {
    params: {
      source_type: sourceType,
      source_id: sourceId
    }
  })
}

export function createResourceAnnotation(resourceId, data) {
  return request.post('/annotation', {
    source_type: data.source_type || data.sourceType || 'generated',
    source_id: data.source_id || data.sourceId || resourceId,
    selected_text: data.selected_text || data.selectedText || '',
    note_text: data.note_text || data.note || '',
    position: data.position || null
  })
}

export function updateResourceAnnotation(resourceId, annotationId, data) {
  return request.put(`/annotation/${annotationId}`, {
    note_text: data.note_text || data.note || ''
  })
}

export function deleteResourceAnnotation(resourceId, annotationId) {
  return request.delete(`/annotation/${annotationId}`)
}

export async function exportEditedPptx(resourceId, data = {}) {
  const href = resolveApiUrl(`/resource/${resourceId}/export-pptx`)
  const token = localStorage.getItem('token')
  const response = await fetch(href, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { token } : {})
    },
    body: JSON.stringify({
      title: data.title || '',
      slides: Array.isArray(data.slides) ? data.slides : []
    })
  })

  if (!response.ok) {
    throw new Error(`导出 PPTX 失败：${response.status}`)
  }

  const blob = await response.blob()
  const filename = data.filename || `${data.title || 'edited-presentation'}.pptx`
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

export function createResourceGenerationTask(data) {
  return request({
    url: '/resource/generate/task',
    method: 'post',
    data: {
      topic: data.topic,
      resource_types: data.resource_types,
      chat_group_id: Number(data.chat_group_id || 0),
      answers: data.answers || undefined,
    }
  })
}

export function getResourceGenerationTask(taskId) {
  return request.get(`/resource/generate/task/${taskId}`)
}

export function getResourceGenerationTasks() {
  return request.get('/resource/generate/tasks')
}

export function likeResource(resourceId) {
  return requestFirstAvailable([
    () => request.post(`/resource/${resourceId}/like`),
    () => request.post(`/resource/like/${resourceId}`),
    () => request.post('/resource/like', { resource_id: Number(resourceId) })
  ])
}

export function unlikeResource(resourceId) {
  return requestFirstAvailable([
    () => request.delete(`/resource/${resourceId}/like`),
    () => request.delete(`/resource/like/${resourceId}`),
    () => request({ url: '/resource/like', method: 'delete', data: { resource_id: Number(resourceId) } })
  ])
}

export function favoriteResource(resourceId) {
  return requestFirstAvailable([
    () => request.post(`/resource/${resourceId}/favorite`),
    () => request.post(`/resource/${resourceId}/collect`),
    () => request.post(`/resource/favorite/${resourceId}`),
    () => request.post('/resource/favorite', { resource_id: Number(resourceId) })
  ])
}

export function unfavoriteResource(resourceId) {
  return requestFirstAvailable([
    () => request.delete(`/resource/${resourceId}/favorite`),
    () => request.delete(`/resource/${resourceId}/collect`),
    () => request.delete(`/resource/favorite/${resourceId}`),
    () => request({ url: '/resource/favorite', method: 'delete', data: { resource_id: Number(resourceId) } })
  ])
}

export function narrateResource(resourceId, options = {}) {
  return request({
    url: '/video/narrate',
    method: 'post',
    data: {
      resource_id: Number(resourceId),
      voice: options.voice || 'zh-CN-XiaoxiaoNeural',
      force_regenerate: Boolean(options.force_regenerate)
    }
  })
}

export function getNarration(narrationId) {
  return request.get(`/video/narrations/${narrationId}`)
}

export function getNarrationVoices() {
  return request.get('/video/voices')
}

export function getPresentationQuestions(data) {
  return request({
    url: '/presentation/questions',
    method: 'post',
    data: {
      topic: data.topic,
      chat_group_id: data.chat_group_id || 0
    }
  })
}

export function generatePresentation(data) {
  return request({
    url: '/presentation/generate',
    method: 'post',
    data: {
      topic: data.topic,
      voice: data.voice || 'zh-CN-XiaoxiaoNeural',
      chapters: data.chapters || undefined,
      answers: data.answers || undefined,
      chat_group_id: data.chat_group_id || 0
    }
  })
}

export function previewPresentation(data) {
  return request({
    url: '/presentation/preview',
    method: 'post',
    data: {
      topic: data.topic
    }
  })
}

export function getPresentations() {
  return request.get('/presentation/list')
}

export function getPresentation(presentationId) {
  return request.get(`/presentation/${presentationId}`)
}

// ── 个人智能体 Skill API ──

export function getAgentSkills() {
  return request.get('/resource/skill/list')
}

export function getAgentSkill(resourceType) {
  return request.get(`/resource/skill/${encodeURIComponent(resourceType)}`)
}

export function upsertAgentSkill(data) {
  return request({
    url: '/resource/skill/upsert',
    method: 'post',
    data
  })
}

const requestFirstAvailable = async requests => {
  let lastError = null

  for (const makeRequest of requests) {
    try {
      return await makeRequest()
    } catch (error) {
      lastError = error
      const status = error?.response?.status
      if (status && ![404, 405].includes(status)) {
        throw error
      }
    }
  }

  throw lastError
}

export function upsertAgentActionSkill(data) {
  return requestFirstAvailable([
    () => request({ url: '/agent/skills/action', method: 'post', data }),
    () => request({ url: '/resource/skill/action/upsert', method: 'post', data }),
    () => request({ url: '/resource/skill/action', method: 'post', data }),
    () => request({ url: '/resource/skill/upsert_action', method: 'post', data })
  ])
}

export function deleteAgentSkill(resourceType) {
  return request.delete(`/resource/skill/${encodeURIComponent(resourceType)}`)
}

export function generateImage(data) {
  return request({
    url: '/image/generate',
    method: 'post',
    data: {
      prompt: data.prompt,
      aspect_ratio: data.aspect_ratio || '1:1',
      img_count: data.img_count || 1,
      chat_group_id: Number(data.chat_group_id || 0)
    }
  })
}

export function getImageTaskStatus(taskId) {
  return request.get(`/image/status/${taskId}`)
}

export function getGeneratedImages() {
  return request.get('/image/list')
}

export function getGeneratedImage(imageId) {
  return request.get(`/image/${imageId}`)
}

export function deleteGeneratedImage(imageId) {
  return request.delete(`/image/${imageId}`)
}

export function deleteGeneratedResource(resourceId) {
  return request.delete(`/resource/${resourceId}`)
}

// ── 题库 Exam API ──

export function generateExamQuestions(data) {
  return request({
    url: '/exam/generate',
    method: 'post',
    data
  })
}

export function getExamQuestions(params = {}) {
  return request({
    url: '/exam/questions',
    method: 'get',
    params
  })
}

export function getExamQuestion(questionId) {
  return request({
    url: `/exam/questions/${questionId}`,
    method: 'get'
  })
}

export function submitExamAnswer(data) {
  return request({
    url: '/exam/submit',
    method: 'post',
    data
  })
}

export function getExamSession(sessionId) {
  return request.get(`/exam/session/${sessionId}`)
}

export function getExamSessions() {
  return request.get('/exam/sessions')
}

// ── 学习路径 API ──

export function getCurrentLearningPath() {
  return request.get('/learning_path/current')
}

export function completeLearningPathNode(nodeId, sessionId, answers = null, correctAnswers = null) {
  const data = { session_id: sessionId }
  if (answers && typeof answers === 'object' && Object.keys(answers).length > 0) {
    data.answers = answers
  }
  if (correctAnswers && typeof correctAnswers === 'object' && Object.keys(correctAnswers).length > 0) {
    data.correct_answers = correctAnswers
  }
  return request({
    url: `/learning_path/nodes/${nodeId}/complete`,
    method: 'post',
    data
  })
}

export function generateLearningPath(data) {
  return request({
    url: '/path/generate',
    method: 'post',
    data
  })
}

export function generateLearningPathsFromProfile(data = {}) {
  return request({
    url: '/path/generate-from-profile',
    method: 'post',
    data
  })
}

export function getLearningPaths() {
  return request.get('/path/list')
}

export function getLearningPathDetail(pathId) {
  return request.get(`/path/${pathId}`)
}

export function getLearningPathProgress(pathId) {
  return request.get(`/path/${pathId}/progress`)
}

export function enrollLearningPath(pathId) {
  return request({
    url: '/path/enroll',
    method: 'post',
    data: {
      path_id: pathId
    }
  })
}

export function generatePathNodeResources(pathId, nodeId) {
  return request({
    url: `/path/${pathId}/node/${nodeId}/generate-resources`,
    method: 'post'
  })
}

export async function generatePathNodeResourcesStream(pathId, nodeId, onResource, onStatus, onDone, onError) {
  const token = localStorage.getItem('token')
  const baseURL = request.defaults.baseURL || ''
  const url = `${baseURL}/path/${pathId}/node/${nodeId}/generate-resources/stream`

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { token } : {})
      }
    })

    if (!response.ok) {
      const detail = await response.text().catch(() => '')
      onError(new Error(detail || `HTTP ${response.status}`))
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const jsonStr = line.slice(6).trim()
        if (jsonStr === '[DONE]') continue
        try {
          const data = JSON.parse(jsonStr)
          if (data.type === 'resource') {
            onResource(data)
          } else if (data.type === 'done') {
            onDone(data)
          } else if (data.type === 'status') {
            onStatus(data)
          } else if (data.type === 'error') {
            onError(new Error(data.detail || '生成失败'))
          }
        } catch {
          // skip unparseable lines
        }
      }
    }
  } catch (err) {
    onError(err)
  }
}

export function generatePathNodeQuiz(pathId, nodeId) {
  return request({
    url: `/path/${pathId}/node/${nodeId}/generate-quiz`,
    method: 'post'
  })
}

// ── 消息通知 API ──

export function getNotifications(page = 1, size = 20) {
  return request.get('/notification/list', { params: { page, size } })
}

export function getUnreadNotificationCount() {
  return request.get('/notification/unread-count')
}

export function markNotificationRead(notificationId) {
  return request.post(`/notification/${notificationId}/read`)
}

export function markAllNotificationsRead() {
  return request.post('/notification/read-all')
}
