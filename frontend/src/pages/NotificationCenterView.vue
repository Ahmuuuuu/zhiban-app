<template>
  <main class="notification-page">
    <header class="page-header">
      <div class="header-title-row">
        <button class="back-btn" type="button" @click="goBack">
          <ChevronLeft :size="22" />
        </button>
        <div>
          <p class="eyebrow">Messages</p>
          <h1>消息中心</h1>
          <p>查看学习提醒、资源通知与系统消息</p>
        </div>
      </div>

      <div class="header-actions">
        <button
          v-if="unreadCount > 0"
          class="mark-all-btn"
          type="button"
          :disabled="markingAll"
          @click="handleMarkAllRead"
        >
          <CheckCheck :size="16" />
          <span>全部已读</span>
        </button>
      </div>
    </header>

    <!-- 加载中 -->
    <section v-if="loading" class="msg-list">
      <article v-for="i in 5" :key="i" class="msg-card skeleton">
        <span class="skel-icon"></span>
        <div class="skel-body">
          <span class="skel-line w-60"></span>
          <span class="skel-line w-80"></span>
        </div>
      </article>
    </section>

    <!-- 空状态 -->
    <section v-else-if="!items.length" class="empty-state">
      <BellOff :size="48" stroke-width="1.2" />
      <h2>暂无消息</h2>
      <p>新的通知会出现在这里</p>
    </section>

    <!-- 消息列表 -->
    <section v-else class="msg-list">
      <article
        v-for="item in items"
        :key="item.id"
        class="msg-card"
        :class="{ unread: !item.is_read, read: item.is_read }"
        @click="handleClick(item)"
      >
        <span class="msg-dot" :class="item.type"></span>

        <div class="msg-body">
          <div class="msg-top">
            <strong>{{ item.title }}</strong>
            <div class="msg-meta">
              <span class="read-state" :class="{ unread: !item.is_read }">
                {{ item.is_read ? '已读' : '未读' }}
              </span>
              <time>{{ formatTime(item.created_at) }}</time>
            </div>
          </div>
          <p>{{ item.content }}</p>
          <span class="msg-tag">{{ typeLabel(item.type) }}</span>
        </div>
      </article>
    </section>

    <!-- 分页 -->
    <footer v-if="total > pageSize" class="pager">
      <button :disabled="page <= 1" @click="changePage(-1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="changePage(1)">下一页</button>
    </footer>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getNotifications,
  getUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
} from '../api/apis'
import { ChevronLeft, BellOff, CheckCheck } from 'lucide-vue-next'

const router = useRouter()

const items = ref([])
const total = ref(0)
const unreadCount = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(true)
const markingAll = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const typeLabel = (type) => {
  const map = { resource: '资源通知', reminder: '学习提醒', system: '系统消息', weekly_report: '学习周报' }
  return map[type] || type
}

const formatTime = (raw) => {
  if (!raw) return ''
  const d = new Date(raw)
  const now = new Date()
  const diff = now - d
  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)} 小时前`
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}-${dd}`
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

const normalizeNotificationTarget = item => {
  const rawUrl = String(item?.target_url || item?.targetUrl || '').trim()
  if (!rawUrl) return ''

  if (/^https?:\/\//i.test(rawUrl)) return rawUrl

  const [rawPath, rawQuery = ''] = rawUrl.split('?')
  const params = new URLSearchParams(rawQuery)
  const path = rawPath.replace(/\/+$/, '') || '/'

  const resourcePathMatch = path.match(/^\/resource\/([^/]+)$/)
  if (path === '/resource' || path === '/resources' || path === '/learning-resources' || resourcePathMatch) {
    const id = params.get('resource_id') || params.get('resourceId') || params.get('id') || resourcePathMatch?.[1]
    const query = new URLSearchParams()
    if (id) {
      query.set('resource_id', id)
    } else {
      query.set('open', 'latest')
    }
    return `/resources?${query.toString()}`
  }

  if (path === '/presentation') {
    const query = params.toString()
    return `/presentation-player${query ? `?${query}` : ''}`
  }

  if (path === '/study-stats') {
    return '/learning-situation'
  }

  return rawUrl
}

const loadList = async () => {
  loading.value = true
  try {
    const res = await getNotifications(page.value, pageSize)
    const data = res?.data || res || {}
    items.value = (data.items || []).map(item => ({
      ...item,
      is_read: Boolean(item.is_read ?? item.isRead ?? false)
    }))
    total.value = data.total || 0
    unreadCount.value = data.unread_count ?? 0
  } catch {
    // 后端不可用时展示空状态
    items.value = []
    total.value = 0
    unreadCount.value = 0
  } finally {
    loading.value = false
  }
}

const handleClick = async (item) => {
  if (!item.is_read) {
    try {
      await markNotificationRead(item.id)
      item.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
      window.dispatchEvent(new CustomEvent('zhiban:notification-read'))
    } catch { /* ignore */ }
  }
  const target = normalizeNotificationTarget(item)
  if (target) {
    if (/^https?:\/\//i.test(target)) {
      window.location.href = target
    } else {
      router.push(target)
    }
  }
}

const handleMarkAllRead = async () => {
  markingAll.value = true
  try {
    await markAllNotificationsRead()
    items.value.forEach(i => { i.is_read = true })
    unreadCount.value = 0
    window.dispatchEvent(new CustomEvent('zhiban:notification-read'))
  } catch { /* ignore */ }
  markingAll.value = false
}

const changePage = (delta) => {
  page.value = Math.max(1, Math.min(totalPages.value, page.value + delta))
  loadList()
}

onMounted(() => {
  loadList()
  // Also update unread count from server
  getUnreadNotificationCount()
    .then(res => {
      const data = res?.data || res || {}
      if (typeof data.unread_count === 'number') {
        unreadCount.value = data.unread_count
      }
    })
    .catch(() => {})
})
</script>

<style scoped>
.notification-page {
  min-height: 100vh;
  padding: 0 clamp(18px, 4vw, 70px) 48px;
  color: #143761;
  font-family: "Open Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* ---- header ---- */
.page-header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin: 0 calc(clamp(18px, 4vw, 70px) * -1) 24px;
  padding: 24px clamp(18px, 4vw, 70px) 18px;
  flex-wrap: wrap;
  background: rgba(245, 250, 255, 0.9);
  border-bottom: 1px solid rgba(181, 205, 220, 0.38);
  box-shadow: 0 10px 24px rgba(20, 55, 97, 0.06);
  backdrop-filter: blur(16px);
}

.header-title-row {
  display: flex;
  align-items: flex-start;
  gap: 18px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(20, 55, 97, 0.15);
  background: rgba(255, 255, 255, 0.62);
  color: #143761;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.2s ease, transform 0.2s ease;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.86);
  transform: translateX(-2px);
}

.eyebrow {
  margin: 0 0 6px;
  color: #6da3d2;
  font-size: 13px;
  font-weight: 800;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 800;
  color: #143761;
}

.page-header p {
  margin: 4px 0 0;
  color: #5d7d97;
  font-size: 14px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mark-all-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 999px;
  border: 1px solid rgba(20, 55, 97, 0.18);
  background: rgba(255, 255, 255, 0.72);
  color: #143761;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  backdrop-filter: blur(12px);
  transition: background 0.2s ease;
}

.mark-all-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.9);
}

.mark-all-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

/* ---- list ---- */
.msg-list {
  display: grid;
  gap: 12px;
}

.msg-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 14px;
  border: 1px solid rgba(181, 205, 220, 0.5);
  background: rgba(255, 255, 255, 0.58);
  backdrop-filter: blur(12px);
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
}

.msg-card:hover {
  background: rgba(255, 255, 255, 0.82);
  border-color: rgba(20, 55, 97, 0.16);
  transform: translateY(-1px);
}

.msg-card.unread {
  border-color: rgba(69, 133, 255, 0.38);
  background: rgba(246, 250, 255, 0.94);
  box-shadow: 0 10px 24px rgba(69, 133, 255, 0.1);
}

.msg-card.read {
  background: rgba(255, 255, 255, 0.46);
  border-color: rgba(181, 205, 220, 0.36);
}

.msg-card.read .msg-top strong,
.msg-card.read .msg-body p {
  color: #7690a7;
}

.msg-card.read .msg-dot {
  background: #cfdce8;
  opacity: 0.75;
}

.msg-card.unread::before {
  content: "";
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 4px;
  border-radius: 0 999px 999px 0;
  background: #4f8cff;
}

.msg-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: #c9dce9;
}

.msg-dot.resource { background: #4f8cff; }
.msg-dot.reminder { background: #f0a73a; }
.msg-dot.system { background: #6da3d2; }
.msg-dot.weekly_report { background: #34d399; }

.unread .msg-dot {
  box-shadow: 0 0 0 4px rgba(20, 55, 97, 0.1);
}

.msg-body {
  flex: 1;
  min-width: 0;
}

.msg-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.msg-top strong {
  font-size: 15px;
  font-weight: 700;
  color: #143761;
}

.msg-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.read-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(139, 164, 188, 0.13);
  color: #8ba4bc;
  font-size: 11px;
  font-weight: 800;
}

.read-state.unread {
  background: rgba(79, 140, 255, 0.14);
  color: #2f6fe4;
}

.msg-top time {
  font-size: 12px;
  color: #8ba4bc;
}

.msg-body p {
  margin: 0 0 10px;
  font-size: 14px;
  color: #5d7d97;
  line-height: 1.55;
}

.msg-tag {
  font-size: 11px;
  font-weight: 700;
  color: #8ba4bc;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(181, 205, 220, 0.32);
}

/* ---- skeleton ---- */
.msg-card.skeleton {
  pointer-events: none;
}

.skel-icon {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e9eff3;
  margin-top: 6px;
  flex-shrink: 0;
}

.skel-body {
  flex: 1;
  display: grid;
  gap: 8px;
}

.skel-line {
  height: 14px;
  border-radius: 4px;
  background: #e9eff3;
}

.skel-line.w-60 { width: 60%; }
.skel-line.w-80 { width: 80%; }

/* ---- empty ---- */
.empty-state {
  display: grid;
  place-items: center;
  gap: 12px;
  padding: 80px 20px;
  color: #8ba4bc;
  text-align: center;
}

.empty-state h2 {
  margin: 0;
  font-size: 18px;
  color: #5d7d97;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

/* ---- pager ---- */
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
}

.pager button {
  padding: 8px 20px;
  border-radius: 999px;
  border: 1px solid rgba(20, 55, 97, 0.18);
  background: rgba(255, 255, 255, 0.62);
  color: #143761;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease;
}

.pager button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.86);
}

.pager button:disabled {
  opacity: 0.4;
  cursor: default;
}

.pager span {
  font-size: 13px;
  color: #5d7d97;
}

@media (max-width: 640px) {
  .notification-page {
    padding: 0 16px 40px;
  }

  .page-header {
    flex-direction: column;
    gap: 14px;
    margin: 0 -16px 18px;
    padding: 18px 16px 14px;
  }

  .page-header h1 {
    font-size: 22px;
  }

  .msg-top {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }
}
</style>
