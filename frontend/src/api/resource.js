import request from './request'
import { API_BASE_URL, parseStreamEvent, requestFirstAvailable, resolveApiUrl } from './config'

export async function streamResourceGeneration(data, { onProgress, onDone, onError, onFile, onStreamStart, onStreamSlide } = {}) {
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
      chat_group_id: Number(data.chat_group_id || 0),
      bind_chat_history: Boolean(data.bind_chat_history)
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

    if (value) {
      buffer += decoder.decode(value, { stream: !done })
    }
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

        if (eventData.type === 'stream_start') {
          onStreamStart?.(eventData)
          continue
        }

        if (eventData.type === 'stream_slide') {
          onStreamSlide?.(eventData)
          continue
        }

        if (eventData.type === 'stream_progress') {
          onProgress?.(eventData)
          continue
        }

        if (isFileEvent && !eventData.done) {
          onFile?.(eventData)
          continue
        }

        if (eventData.resources !== undefined || eventData.review_passed !== undefined) {
          onProgress?.(eventData)
        }

        if (eventData.done || eventData.type === 'done' || eventData.event === 'done') {
          onDone?.(eventData)
        }
      }
    }
    if (done) break
  }
}

export function getGeneratedResources(params = {}) {
  return request.get('/resource/list', { params })
}

export function getGeneratedResource(resourceId) {
  return request.get(`/resource/${resourceId}`)
}

export function deleteGeneratedResource(resourceId) {
  return request.delete(`/resource/${resourceId}`)
}

export function publishGeneratedResource(resourceId, visibility = 'public') {
  return request.post(`/resource/${resourceId}/visibility`, { visibility })
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
  const token = localStorage.getItem('token')
  const targetUrl = new URL(resolveApiUrl(`/resource/${resourceId}/export-pptx`))
  if (token && !targetUrl.searchParams.has('token')) {
    targetUrl.searchParams.set('token', token)
  }
  const href = targetUrl.toString()
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
    const message = await response.text().catch(() => '')
    throw new Error(message || `导出 PPTX 失败：${response.status}`)
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
      bind_chat_history: Boolean(data.bind_chat_history),
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
