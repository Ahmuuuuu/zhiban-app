import request from './request'

const rawBase = request.defaults.baseURL || '/'

export const API_BASE_URL = rawBase.endsWith('/') ? rawBase : rawBase + '/'

export const resolveApiUrl = path => {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path

  return new URL(String(path).replace(/^\//, ''), API_BASE_URL).toString()
}

export const normalizeAvatarUrl = avatar => {
  if (!avatar) return ''
  return resolveApiUrl(avatar)
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
  const targetUrl = new URL(resolveApiUrl(url))
  if (token && !targetUrl.searchParams.has('token')) {
    targetUrl.searchParams.set('token', token)
  }
  const href = targetUrl.toString()
  const response = await fetch(href, {
    headers: {
      ...(token ? { token } : {})
    }
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
