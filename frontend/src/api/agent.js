import request from './request'
import { requestFirstAvailable } from './config'

export function getAgentSkills() {
  return request.get('/resource/skill/list')
}

export function getAgentSkill(resourceType) {
  return request.get(`/resource/skill/${encodeURIComponent(resourceType)}`)
}

export function upsertAgentSkill(data) {
  return request({
    url: '/resource/skill/upsert',
    method: 'post',
    data
  })
}

export function upsertAgentActionSkill(data) {
  return requestFirstAvailable([
    () => request({ url: '/agent/skills/action', method: 'post', data }),
    () => request({ url: '/resource/skill/action/upsert', method: 'post', data }),
    () => request({ url: '/resource/skill/action', method: 'post', data }),
    () => request({ url: '/resource/skill/upsert_action', method: 'post', data })
  ])
}

export function deleteAgentSkill(resourceType) {
  return request.delete(`/resource/skill/${encodeURIComponent(resourceType)}`)
}
