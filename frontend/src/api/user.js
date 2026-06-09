import request from './request'

export function getUserProfile() {
  return request({
    url: '/user/read_user',
    method: 'get'
  })
}

export function updateUserProfile(data) {
  return request({
    url: '/user/update_user/information',
    method: 'post',
    data
  })
}

export function uploadUserAvatar(file) {
  const data = new FormData()
  data.append('file', file)

  return request({
    url: '/user/avatar',
    method: 'post',
    data
  })
}

export function deleteUserAvatar() {
  return request({
    url: '/user/avatar',
    method: 'delete'
  })
}

export function deleteUser(data) {
  return request({
    url: '/user/delete_user',
    method: 'delete',
    data
  })
}
