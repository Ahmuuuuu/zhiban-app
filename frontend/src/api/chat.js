import request from './request'
import { API_BASE_URL, parseStreamEvent, requestFirstAvailable } from './config'

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

export function getConversationList() {
  return request.get('/ai_chat/read_history_group')
}

export function getConversationMessages(chatGroupId) {
  return request.get('/ai_chat/read_messages_from_history', {
    params: {
      chat_group_id: chatGroupId
    }
  })
}

export function deleteConversation(chatGroupId) {
  return request.delete('/ai_chat/delete_history_group', {
    params: {
      chat_group_id: chatGroupId
    }
  })
}

export function transcribeVoiceInput(audioBlob) {
  const filename = audioBlob?.type?.includes('mp4') ? 'voice.mp4' : 'voice.webm'
  const buildFormData = () => {
    const file = new File([audioBlob], filename, { type: audioBlob?.type || 'audio/webm' })
    const formData = new FormData()
    formData.append('file', file)
    formData.append('audio', file)
    return formData
  }

  return requestFirstAvailable([
    () => request.post('/ai_chat/voice_input', buildFormData()),
    () => request.post('/ai_chat/voice-input', buildFormData()),
    () => request.post('/ai_chat/transcribe', buildFormData()),
    () => request.post('/ai_chat/speech_to_text', buildFormData()),
    () => request.post('/voice/transcribe', buildFormData()),
    () => request.post('/speech/transcribe', buildFormData()),
    () => request.post('/audio/transcribe', buildFormData())
  ])
}

export async function streamChatMessage(data, { onChunk, onDone, onError, onFile, onStreamStart, onStreamSlide, onStreamSlideStart, onStreamSlideDelta, onStreamSlideDone, onStreamSectionReplace, onThinking } = {}) {
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

        if (eventData.type === 'stream_start') {
          await onStreamStart?.(eventData)
          continue
        }

        if (eventData.type === 'stream_slide') {
          await onStreamSlide?.(eventData)
          continue
        }

        if (eventData.type === 'stream_slide_start') {
          await onStreamSlideStart?.(eventData)
          continue
        }

        if (eventData.type === 'stream_slide_delta') {
          await onStreamSlideDelta?.(eventData)
          continue
        }

        if (eventData.type === 'stream_slide_done') {
          await onStreamSlideDone?.(eventData)
          continue
        }

        if (eventData.type === 'stream_section_replace') {
          await onStreamSectionReplace?.(eventData)
          continue
        }

        const thinking =
          eventData.thinking ||
          eventData.thought ||
          eventData.reasoning ||
          eventData.reasoning_content ||
          eventData.reasoningContent ||
          eventData.process ||
          eventData.thought_process ||
          eventData.thoughtProcess

        if (thinking || eventData.type === 'thinking' || eventData.event === 'thinking') {
          await onThinking?.(thinking || eventData.content || '')
          continue
        }

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
    if (done) break
  }
}
