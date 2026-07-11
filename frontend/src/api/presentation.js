import request from './request'

export function getPresentationQuestions(data) {
  return request({
    url: '/video/questions',
    method: 'post',
    data: {
      topic: data.topic,
      chat_group_id: data.chat_group_id || 0
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
