export const isAdminRole = role => {
  const value = String(role || '').trim().toLowerCase()
  return ['admin', 'administrator', 'super_admin', 'manager'].includes(value)
}

const parseJwtPayload = token => {
  try {
    const payload = String(token || '').split('.')[1]
    if (!payload) return null
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
    return JSON.parse(decodeURIComponent(escape(window.atob(padded))))
  } catch {
    return null
  }
}

export const currentUserRole = () => {
  const storedRole = localStorage.getItem('role') || localStorage.getItem('identity') || ''
  if (storedRole) return storedRole
  const tokenRole = parseJwtPayload(localStorage.getItem('token'))?.role || ''
  if (tokenRole) localStorage.setItem('role', tokenRole)
  return tokenRole
}

export const isCurrentUserAdmin = () => isAdminRole(currentUserRole())
