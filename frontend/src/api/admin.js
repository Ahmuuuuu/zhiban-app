import request from './request'
import { requestFirstAvailable } from './config'

export function getAdminUsers() {
  return request.get('/admin/users')
}

export function getAdminKnowledgeBase() {
  return request.get('/admin/knowledge_base')
}

export function getAdminPendingResources(params = {}) {
  return requestFirstAvailable([
    () => request.get('/admin/resources/pending', { params }),
    () => request.get('/admin/resource/pending', { params }),
    () => request.get('/admin/resource-applications', { params }),
    () => request.get('/admin/public-resource-applications', { params })
  ])
}

export function getAdminResources(params = {}) {
  return requestFirstAvailable([
    () => request.get('/admin/resources', { params }),
    () => request.get('/admin/resource/list', { params }),
    () => request.get('/resource/list', { params: { ...params, admin: true } })
  ])
}

export function approvePublicResourceApplication(applicationId, data = {}) {
  return requestFirstAvailable([
    () => request.post(`/admin/resources/applications/${applicationId}/approve`, data),
    () => request.post(`/admin/resource-applications/${applicationId}/approve`, data),
    () => request.post(`/admin/resources/${applicationId}/approve`, data),
    () => request.post(`/admin/resource/${applicationId}/approve`, data)
  ])
}

export function rejectPublicResourceApplication(applicationId, data = {}) {
  return requestFirstAvailable([
    () => request.post(`/admin/resources/applications/${applicationId}/reject`, data),
    () => request.post(`/admin/resource-applications/${applicationId}/reject`, data),
    () => request.post(`/admin/resources/${applicationId}/reject`, data),
    () => request.post(`/admin/resource/${applicationId}/reject`, data)
  ])
}

export function updateAdminResource(resourceId, data = {}) {
  return requestFirstAvailable([
    () => request.put(`/admin/resources/${resourceId}`, data),
    () => request.patch(`/admin/resources/${resourceId}`, data),
    () => request.put(`/admin/resource/${resourceId}`, data),
    () => request.patch(`/admin/resource/${resourceId}`, data)
  ])
}

export function deleteAdminResource(resourceId) {
  return requestFirstAvailable([
    () => request.delete(`/admin/resources/${resourceId}`),
    () => request.delete(`/admin/resource/${resourceId}`),
    () => request.delete(`/resource/${resourceId}`)
  ])
}

export function importAdminBaseResource(data) {
  const isFormData = typeof FormData !== 'undefined' && data instanceof FormData
  const config = isFormData ? {} : undefined

  return requestFirstAvailable([
    () => request.post('/admin/resources/import', data, config),
    () => request.post('/admin/resource/import', data, config),
    () => request.post('/admin/knowledge_base/import', data, config),
    () => request.post('/admin/knowledge_base', data, config)
  ])
}
