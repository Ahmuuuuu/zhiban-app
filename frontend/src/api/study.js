import request from './request'

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
