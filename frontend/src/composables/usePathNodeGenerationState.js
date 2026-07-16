const DEFAULT_STORAGE_KEY = 'zhiban_path_node_generation_locks'
const DEFAULT_TTL_BY_KIND = {
  resources: 15 * 60 * 1000,
  quiz: 8 * 60 * 1000
}

const canUseLocalStorage = () => typeof localStorage !== 'undefined'

export function usePathNodeGenerationState(options = {}) {
  const storageKey = options.storageKey || DEFAULT_STORAGE_KEY
  const ttlByKind = {
    ...DEFAULT_TTL_BY_KIND,
    ...(options.ttlByKind || {})
  }
  const memoryLocks = new Map()

  const getKindLocks = kind => {
    const key = String(kind || 'default')
    if (!memoryLocks.has(key)) memoryLocks.set(key, new Set())
    return memoryLocks.get(key)
  }

  const getNodeKey = (pathId, node) => {
    const normalizedPathId = String(pathId || '')
    const nodeId = String(node?.id || node?.node_id || node?.nodeId || '')
    return normalizedPathId && nodeId ? `${normalizedPathId}:${nodeId}` : ''
  }

  const getLockKey = (baseKey, kind) =>
    baseKey && kind ? `${baseKey}:${kind}` : ''

  const readPersistedLocks = () => {
    if (!canUseLocalStorage()) return {}
    try {
      const raw = localStorage.getItem(storageKey)
      const locks = raw ? JSON.parse(raw) : {}
      const now = Date.now()
      let changed = false
      Object.entries(locks || {}).forEach(([key, lock]) => {
        if (!lock?.expiresAt || Number(lock.expiresAt) <= now) {
          delete locks[key]
          changed = true
        }
      })
      if (changed) localStorage.setItem(storageKey, JSON.stringify(locks))
      return locks && typeof locks === 'object' ? locks : {}
    } catch {
      return {}
    }
  }

  const writePersistedLocks = locks => {
    if (!canUseLocalStorage()) return
    try {
      localStorage.setItem(storageKey, JSON.stringify(locks || {}))
    } catch { /* ignore */ }
  }

  const rememberByKey = (baseKey, kind, ttl) => {
    const lockKey = getLockKey(baseKey, kind)
    if (!lockKey) return
    getKindLocks(kind).add(baseKey)
    const now = Date.now()
    const locks = readPersistedLocks()
    locks[lockKey] = {
      startedAt: now,
      expiresAt: now + (ttl || ttlByKind[kind] || 10 * 60 * 1000)
    }
    writePersistedLocks(locks)
  }

  const forgetByKey = (baseKey, kind) => {
    const lockKey = getLockKey(baseKey, kind)
    if (!lockKey) return
    getKindLocks(kind).delete(baseKey)
    const locks = readPersistedLocks()
    if (!locks[lockKey]) return
    delete locks[lockKey]
    writePersistedLocks(locks)
  }

  const hasMemoryByKey = (baseKey, kind) =>
    Boolean(baseKey && getKindLocks(kind).has(baseKey))

  const hasPersistedByKey = (baseKey, kind) => {
    const lockKey = getLockKey(baseKey, kind)
    if (!lockKey) return false
    const lock = readPersistedLocks()[lockKey]
    return Boolean(lock?.expiresAt && Number(lock.expiresAt) > Date.now())
  }

  const isLockedByKey = (baseKey, kind) =>
    hasMemoryByKey(baseKey, kind) || hasPersistedByKey(baseKey, kind)

  const rememberNode = (pathId, node, kind, ttl) =>
    rememberByKey(getNodeKey(pathId, node), kind, ttl)

  const forgetNode = (pathId, node, kind) =>
    forgetByKey(getNodeKey(pathId, node), kind)

  return {
    getNodeKey,
    rememberByKey,
    forgetByKey,
    hasMemoryByKey,
    hasPersistedByKey,
    isLockedByKey,
    rememberNode,
    forgetNode,
    readPersistedLocks
  }
}
