import request from './request'

export function startStudyRoomSession(data) {
  return request({
    url: '/study-room/sessions/start',
    method: 'post',
    data
  })
}

export function uploadStudyRoomFrame(sessionId, data) {
  return request({
    url: `/study-room/sessions/${encodeURIComponent(sessionId)}/frame`,
    method: 'post',
    data
  })
}

export function getStudyRoomSession(sessionId) {
  return request.get(`/study-room/sessions/${encodeURIComponent(sessionId)}`)
}

export function finishStudyRoomSession(sessionId, data) {
  return request({
    url: `/study-room/sessions/${encodeURIComponent(sessionId)}/finish`,
    method: 'post',
    data
  })
}

export function getStudyRoomTimelapse(sessionId) {
  return request.get(`/study-room/sessions/${encodeURIComponent(sessionId)}/timelapse`)
}

export function deleteStudyRoomTimelapse(sessionId) {
  return request.delete(`/study-room/sessions/${encodeURIComponent(sessionId)}/timelapse`)
}
