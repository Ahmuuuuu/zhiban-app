import request from './request'
import { apiFetchHeaders, parseStreamEvent } from './config'

export function getCurrentLearningPath() {
  return request.get('/learning_path/current')
}

export function completeLearningPathNode(nodeId, sessionId, answers = null) {
  const data = { session_id: sessionId }
  // 空对象也要发送：它代表本次交卷一题都没答，后端据此清除旧会话残留答案。
  if (answers && typeof answers === 'object') {
    data.answers = answers
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

export async function generateLearningPathStream(data, onEvent, onError) {
  const token = localStorage.getItem('token')
  const baseURL = request.defaults.baseURL || ''
  const url = `${baseURL}/path/generate/stream`

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: apiFetchHeaders({
        'Content-Type': 'application/json',
        ...(token ? { token } : {})
      }),
      body: JSON.stringify(data || {})
    })

    if (!response.ok) {
      const detail = await response.text().catch(() => '')
      throw new Error(detail || `HTTP ${response.status}`)
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
        if (!jsonStr || jsonStr === '[DONE]') continue
        try {
          onEvent?.(JSON.parse(jsonStr))
        } catch {
          // skip unparseable event
        }
      }
    }
  } catch (err) {
    onError?.(err)
    throw err
  }
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

export async function generatePathNodeResourcesStream(pathId, nodeId, onResource, onStatus, onDone, onError, data = {}) {
  const token = localStorage.getItem('token')
  const baseURL = request.defaults.baseURL || ''
  const url = `${baseURL}/path/${pathId}/node/${nodeId}/generate-resources/stream`

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: apiFetchHeaders({
        'Content-Type': 'application/json',
        ...(token ? { token } : {})
      }),
      body: JSON.stringify(data || {})
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

export function generatePathNodeQuiz(pathId, nodeId, forceRegenerate = false) {
  return request({
    url: `/path/${pathId}/node/${nodeId}/generate-quiz`,
    method: 'post',
    data: { force_regenerate: Boolean(forceRegenerate) }
  })
}

export function generateNodeClassroom(pathId, nodeId, data = {}, config = {}) {
  return request({
    url: `/path/${pathId}/node/${nodeId}/classroom`,
    method: 'post',
    data,
    ...config
  })
}

export function getNodeClassroom(pathId, nodeId) {
  return request.get(`/path/${pathId}/node/${nodeId}/classroom`)
}

export function getClassroomTransition(pathId, nodeId) {
  return request.get(`/path/${pathId}/node/${nodeId}/classroom-transition`)
}

export function narrateClassroomText(data = {}) {
  return request({
    url: '/path/classroom/narrate',
    method: 'post',
    data
  })
}

export async function streamClassroomChatMessage(data = {}, { onChunk, onDone, onError } = {}) {
  const token = localStorage.getItem('token')
  const baseURL = request.defaults.baseURL || ''
  const url = `${baseURL}/path/classroom/chat`
  const response = await fetch(url, {
    method: 'POST',
    headers: apiFetchHeaders({
      'Content-Type': 'application/json',
      ...(token ? { token } : {})
    }),
    body: JSON.stringify(data || {})
  })
  if (!response.ok || !response.body) {
    throw new Error(`流式请求失败：${response.status}`)
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (value) buffer += decoder.decode(value, { stream: !done })
    const events = buffer.split(/\r?\n\r?\n/)
    buffer = events.pop() || ''
    for (const eventText of events) {
      for (const payload of parseStreamEvent(eventText)) {
        if (payload === '[DONE]') { onDone?.({}); continue }
        let ev
        try { ev = JSON.parse(payload) } catch { continue }
        if (ev.error) { await onError?.(ev.error); return }
        if (ev.content) await onChunk?.(ev.content)
        if (ev.type === 'done' || ev.done) await onDone?.(ev)
      }
    }
    if (done) break
  }
}

export function getPathVideo(pathId) {
  return request.get(`/path/${pathId}/video`)
}

export function generatePathVideo(pathId) {
  return request({
    url: `/path/${pathId}/video`,
    method: 'post'
  })
}
