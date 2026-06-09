import request from './request'

export function generateExamQuestions(data) {
  return request({
    url: '/exam/generate',
    method: 'post',
    data
  })
}

export function getExamQuestions(params = {}) {
  return request({
    url: '/exam/questions',
    method: 'get',
    params
  })
}

export function getExamQuestion(questionId) {
  return request({
    url: `/exam/questions/${questionId}`,
    method: 'get'
  })
}

export function submitExamAnswer(data) {
  return request({
    url: '/exam/submit',
    method: 'post',
    data
  })
}

export function getExamSession(sessionId) {
  return request.get(`/exam/session/${sessionId}`)
}

export function getExamSessions() {
  return request.get('/exam/sessions')
}
