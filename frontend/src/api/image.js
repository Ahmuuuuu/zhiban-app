import request from './request'

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

export function getGeneratedImages(params = {}) {
  return request.get('/image/list', { params })
}

export function getGeneratedImage(imageId) {
  return request.get(`/image/${imageId}`)
}

export function deleteGeneratedImage(imageId) {
  return request.delete(`/image/${imageId}`)
}

export function publishGeneratedImage(imageId, visibility = 'public') {
  return request.post(`/image/${imageId}/visibility`, { visibility })
}
