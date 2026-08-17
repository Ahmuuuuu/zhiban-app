import request from './request'

export function startMockClassroomSession(data) {
  return request({
    url: '/mock-classroom/sessions/start',
    method: 'post',
    data
  })
}

export function uploadMockClassroomFrame(sessionId, data) {
  return request({
    url: `/mock-classroom/sessions/${encodeURIComponent(sessionId)}/frame`,
    method: 'post',
    data
  })
}

export function uploadMockClassroomAudio(sessionId, data) {
  return request({
    url: `/mock-classroom/sessions/${encodeURIComponent(sessionId)}/audio`,
    method: 'post',
    data
  })
}

export function finishMockClassroomSession(sessionId, data) {
  return request({
    url: `/mock-classroom/sessions/${encodeURIComponent(sessionId)}/finish`,
    method: 'post',
    data
  })
}

export function getMockClassroomReport(sessionId) {
  return request.get(`/mock-classroom/sessions/${encodeURIComponent(sessionId)}/report`)
}

export function deleteMockClassroomMedia(sessionId) {
  return request.delete(`/mock-classroom/sessions/${encodeURIComponent(sessionId)}/media`)
}
