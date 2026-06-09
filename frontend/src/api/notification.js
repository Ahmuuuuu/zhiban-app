import request from './request'

export function getNotifications(page = 1, size = 20) {
  return request.get('/notification/list', { params: { page, size } })
}

export function getUnreadNotificationCount() {
  return request.get('/notification/unread-count')
}

export function markNotificationRead(notificationId) {
  return request.post(`/notification/${notificationId}/read`)
}

export function markAllNotificationsRead() {
  return request.post('/notification/read-all')
}
