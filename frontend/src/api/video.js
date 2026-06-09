import request from './request'

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
