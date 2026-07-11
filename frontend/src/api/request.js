import axios from 'axios'

export const DEFAULT_API_BASE_URL = ''
const rawApiBaseURL = import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL
export const apiBaseURL = rawApiBaseURL.replace(/\/+$/, '')

export const isBackendUnavailableError = error => {
  const status = Number(error?.response?.status || error?.status || 0)
  return status === 502 || status === 503 || status === 504
}

const request = axios.create({
  baseURL: apiBaseURL,
  timeout: 300000
})

let authExpiredNotified = false

const clearAuthStorage = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user_id')
  localStorage.removeItem('username')
  localStorage.removeItem('role')
  localStorage.removeItem('identity')
  localStorage.removeItem('avatar')
  localStorage.removeItem('zhiban_generation_tasks_v2')
}

const notifyAuthExpired = () => {
  if (authExpiredNotified) return
  authExpiredNotified = true

  clearAuthStorage()

  window.dispatchEvent(new CustomEvent('zhiban-auth-expired', { detail: { message: '登录已过期，请重新登录。' } }))

  window.setTimeout(() => {
    authExpiredNotified = false
  }, 2000)
}

request.interceptors.request.use(
  config => {
    config.headers = config.headers || {}
    config.headers['ngrok-skip-browser-warning'] = 'true'

    const token = localStorage.getItem('token')
    const publicUrls = ['/user/create_user', '/user/login_user', '/user/send_email_code', '/user/register_by_email', '/user/login_by_email']

    if (token && !publicUrls.includes(config.url)) {
      config.headers.token = token
    }

    return config
  },
  error => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  response => {
    const data = response.data
    if (data && data.token) {
      localStorage.setItem('token', data.token)
    }
    return data
  },
  error => {
    if (error.response && error.response.status === 401) {
      notifyAuthExpired()
      console.error('登录已过期，请重新登录')
    }

    // 422 诊断日志：打印请求 URL 和参数，帮助定位参数错误
    if (error.response && error.response.status === 422) {
      console.error('[422] 请求参数校验失败\n  URL:', error.config?.url, '\n  Method:', error.config?.method, '\n  Params:', error.config?.params, '\n  Data:', error.config?.data)
    }

    return Promise.reject(error)
  }
)

export default request
