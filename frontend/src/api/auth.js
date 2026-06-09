import request from './request'

export function login(data) {
  return request({
    url: '/user/login_user',
    method: 'post',
    data
  })
}

export function register(data) {
  return request({
    url: '/user/create_user',
    method: 'post',
    data
  })
}

export function sendEmailCode(data) {
  return request({
    url: '/user/send_email_code',
    method: 'post',
    data
  })
}

export function registerByEmail(data) {
  return request({
    url: '/user/register_by_email',
    method: 'post',
    data
  })
}
