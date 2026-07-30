import request from './request'
import { requestFirstAvailable } from './config'

// ── Skill 管理（原有）──
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

// ── 用户自建智能体 CRUD（新增）──
export function getMyAgents() {
  return request.get('/api/agents')
}

export function getAgent(agentId) {
  return request.get(`/api/agents/${agentId}`)
}

export function createAgent(data) {
  return request.post('/api/agents', data)
}

export function updateAgent(agentId, data) {
  return request.put(`/api/agents/${agentId}`, data)
}

export function deleteAgent(agentId) {
  return request.delete(`/api/agents/${agentId}`)
}

export function getPublicAgents() {
  return request.get('/api/agents/market/public')
}

export function copyAgent(agentId) {
  return request.post(`/api/agents/${agentId}/copy`)
}

export function getAvailableTools() {
  return request.get('/api/agents/tools')
}

export function getChatAgent(chatGroupId) {
  return request.get(`/api/agents/chat/${chatGroupId}`)
}
