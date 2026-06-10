export const isAdminRole = role => {
  const value = String(role || '').trim().toLowerCase()
  return ['admin', 'administrator', 'super_admin', 'manager'].includes(value)
}

export const currentUserRole = () => {
  return localStorage.getItem('role') || localStorage.getItem('identity') || ''
}

export const isCurrentUserAdmin = () => isAdminRole(currentUserRole())
