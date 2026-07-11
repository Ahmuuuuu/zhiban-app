import request from './request'

const rawBase = request.defaults.baseURL || '/'

export const API_BASE_URL = rawBase.endsWith('/') ? rawBase : rawBase + '/'

const isNgrokApi = /^https?:\/\/[^/]+\.ngrok-free\.(app|dev)(\/|$)/i.test(API_BASE_URL)

export const apiFetchHeaders = (headers = {}) => ({
  ...headers,
  ...(isNgrokApi ? { 'ngrok-skip-browser-warning': 'true' } : {})
})

export const resolveApiUrl = path => {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path

  // /static/ 路径保持相对，走 Vite proxy（开发）或同源访问（生产），避免局域网跨端口拦截
  // baseURL 为空时走相对路径，由 nginx/Vite proxy 转发
  if (!/^https?:\/\//i.test(API_BASE_URL)) return path.startsWith('/') ? path : `/${path}`

  return new URL(String(path).replace(/^\//, ''), API_BASE_URL).toString()
}

export const normalizeAvatarUrl = avatar => {
  const raw = String(avatar || '').trim()
  if (!raw) return ''
  if (/^(data:|blob:)/i.test(raw)) return raw

  try {
    const url = /^https?:\/\//i.test(raw)
      ? new URL(raw)
      : new URL(raw.replace(/^\//, ''), API_BASE_URL)

    if (/\/static\/avatars\//.test(url.pathname) && !url.searchParams.has('v')) {
      const version = localStorage.getItem('zhiban_avatar_version')
      if (version) url.searchParams.set('v', version)
    }

    return url.toString()
  } catch {
    return resolveApiUrl(raw)
  }
}

export const parseStreamEvent = eventText => {
  return eventText
    .split('\n')
    .filter(line => line.startsWith('data:'))
    .map(line => line.replace(/^data:\s*/, '').trim())
    .filter(Boolean)
}

export async function downloadWithToken(url, filename = 'download') {
  const token = localStorage.getItem('token')
  const targetUrl = new URL(resolveApiUrl(url), window.location.origin)
  if (token && !targetUrl.searchParams.has('token')) {
    targetUrl.searchParams.set('token', token)
  }
  const href = targetUrl.toString()
  const response = await fetch(href, {
    headers: apiFetchHeaders({
      ...(token ? { token } : {})
    })
  })

  if (!response.ok) {
    const message = await response.text().catch(() => '')
    throw new Error(message || `下载失败：${response.status}`)
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

export const requestFirstAvailable = async requests => {
  let lastError = null

  for (const makeRequest of requests) {
    try {
      return await makeRequest()
    } catch (error) {
      lastError = error
      const status = error?.response?.status
      if (status && ![404, 405].includes(status)) {
        throw error
      }
    }
  }

  throw lastError
}
