import { API_BASE_URL, apiFetchHeaders, parseStreamEvent } from './config'
import request from './request'

export function getPresentationQuestions(data) {
  return request({
    url: '/video/questions',
    method: 'post',
    data: {
      topic: data.topic,
      chat_group_id: data.chat_group_id || 0,
      voice: data.voice || 'zh-CN-XiaoxiaoNeural'
    }
  })
}

export function generatePresentation(data) {
  return request({
    url: '/video/generate',
    method: 'post',
    data: {
      topic: data.topic,
      voice: data.voice || 'zh-CN-XiaoxiaoNeural',
      chapters: data.chapters || undefined,
      answers: data.answers || undefined,
      chat_group_id: data.chat_group_id || 0,
      video_mode: false
    }
  })
}

export function previewPresentation(data) {
  return request({
    url: '/video/preview',
    method: 'post',
    data: {
      topic: data.topic
    }
  })
}

export function getPresentations() {
  return request.get('/video/list')
}

export function getPresentation(presentationId) {
  return request.get(`/video/${presentationId}`)
}

export async function streamPresentationProgress(presentationId, { onEvent, onDone, onError, signal, doneOnAudio = false } = {}) {
  const url = `${API_BASE_URL}video/${encodeURIComponent(presentationId)}/sse`
  const token = localStorage.getItem('token')
  const response = await fetch(url, {
    signal,
    headers: apiFetchHeaders({
      ...(token ? { token } : {})
    })
  })

  if (!response.ok || !response.body) {
    const error = new Error(`视频进度订阅失败：${response.status}`)
    error.status = response.status
    error.response = { status: response.status }
    throw error
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let doneNotified = false

  const notifyDone = eventData => {
    if (doneNotified) return
    doneNotified = true
    onDone?.(eventData || {})
  }

  while (true) {
    const { done, value } = await reader.read()
    if (value) {
      buffer += decoder.decode(value, { stream: !done })
    }

    const events = buffer.split(/\r?\n\r?\n/)
    buffer = events.pop() || ''

    for (const eventText of events) {
      const payloads = parseStreamEvent(eventText)
      for (const payload of payloads) {
        if (payload === '[DONE]') {
          notifyDone({})
          continue
        }

        let eventData
        try {
          eventData = JSON.parse(payload)
        } catch {
          continue
        }

        if (eventData.error && eventData.status !== 'failed') {
          onError?.(eventData.error)
          continue
        }

        onEvent?.(eventData)

        const isAgentDone = eventData.type === 'agent_event' &&
          eventData.phase === 'complete' &&
          ['done', 'failed'].includes(String(eventData.status || '').toLowerCase())
        const isAudioDone = eventData.type === 'audio_progress' && eventData.status === 'all_ready'
        const isReadyWithAudio = eventData.status === 'ready' &&
          Array.isArray(eventData.chapters) &&
          eventData.chapters.length > 0 &&
          eventData.chapters.every(ch => ch?.is_audio_ready)
        const isFailed = eventData.status === 'failed'
        if (isFailed) {
          onError?.(eventData.error || eventData.message || '视频生成失败')
          notifyDone(eventData)
        } else if (isAudioDone || isReadyWithAudio || (isAgentDone && !doneOnAudio)) {
          notifyDone(eventData)
        }
      }
    }

    if (done) break
  }
}
