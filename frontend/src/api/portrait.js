import request from './request'

export function getPortrait() {
  return request.get('/ai_portrait/read_portrait')
}

export function getPortraitRadar() {
  return request.get('/ai_portrait/radar')
}

export function initPortrait(data) {
  return request({
    url: '/ai_portrait/init_portrait',
    method: 'post',
    data
  })
}

export function initPortraitFromDialogue(data) {
  return request({
    url: '/ai_portrait/init_from_dialogue',
    method: 'post',
    data
  })
}
