import request from './request'

const rawBase = request.defaults.baseURL || '/'
const API_BASE_URL = rawBase.endsWith('/') ? rawBase : rawBase + '/'

export const resolveApiUrl = path => {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path

  return new URL(String(path).replace(/^\//, ''), API_BASE_URL).toString()
}

// 鐧诲綍锛氬悗绔?Login_User 鎺ユ敹 username/email/password
export function login(data) {
  return request({
    url: '/user/login_user',
    method: 'post',
    data
  })
}

// 娉ㄥ唽锛氬悗绔?Create_User 鎺ユ敹 username/password
export function register(data) {
  return request({
    url: '/user/create_user',
    method: 'post',
    data
  })
}

// 鑾峰彇鐢ㄦ埛璧勬枡锛氬悗绔?Read_User 閫氳繃 token 鑾峰彇 user_id
export function getUserProfile() {
  return request({
    url: '/user/read_user',
    method: 'get'
  })
}

// 鏇存柊涓汉淇℃伅锛氬悗绔?Update_User_Information 鎺ユ敹 username/major/email/phonenum/profile
export function updateUserProfile(data) {
  return request({
    url: '/user/update_user/information',
    method: 'post',
    data
  })
}

// 娉ㄩ攢璐︽埛锛氬悗绔?Delete_User 鎺ユ敹 password锛岀敤鎴疯韩浠介€氳繃 token 鑾峰彇
export function deleteUser(data) {
  return request({
    url: '/user/delete_user',
    method: 'delete',
    data
  })
}

// AI 鑱婂ぉ淇℃伅杩斿洖
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

// 鑾峰彇鏈€杩戝巻鍙插璇濆垪琛?
export function getConversationList() {
  return request.get('/ai_chat/read_history_group')
}

// 鑾峰彇鏌愭潯瀵硅瘽鐨勫畬鏁存秷鎭?
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
    throw new Error(`娴佸紡璇锋眰澶辫触锛?{response.status}`)
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

        if (isFileEvent) {
          onFile?.(eventData)
          continue
        }

        if (eventData.content) {
          onChunk?.(eventData.content)
        }

        if (eventData.done || eventData.type === 'done' || eventData.event === 'done') {
          onDone?.(eventData)
        }
      }
    }
  }
}

export function getPortrait() {
  return request.get('/ai_portrait/read_portrait')
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

// 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
//  瀛︿範璧勬簮鐢熸垚锛堟祦寮忥級
// 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?

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
    throw new Error(`璧勬簮鐢熸垚璇锋眰澶辫触锛?{response.status}`)
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

// 鑾峰彇宸茬敓鎴愮殑璧勬簮鍒楄〃
export function getGeneratedResources() {
  return request.get('/resource/list')
}

export function getGeneratedResource(resourceId) {
  return request.get(`/resource/${resourceId}`)
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
