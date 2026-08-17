<template>
  <main class="study-room-page">
    <div class="classroom-bg" aria-hidden="true">
      <div class="sun-wash"></div>
      <div class="blackboard-shape">
        <span></span>
        <span></span>
      </div>
      <div class="desk-row desk-row-one"></div>
      <div class="desk-row desk-row-two"></div>
      <div class="desk-grain"></div>
    </div>

    <section class="study-room-shell" aria-label="自习室">
      <header class="room-header">
        <div>
          <p class="eyebrow">Focus Classroom</p>
          <h1>自习室</h1>
          <p>进入自动监督自习室，开启一段专注的学习</p>
        </div>
        <div class="room-state-pill" :class="sessionMode">
          <component :is="stateIcon" :size="17" stroke-width="2.2" />
          <span>{{ sessionStateText }}</span>
        </div>
      </header>

      <section v-if="sessionMode === 'setup'" class="setup-grid">
        <article class="setup-panel">
          <div class="panel-title">
            <ClipboardList :size="19" />
            <h2>开始前准备</h2>
          </div>

          <label class="form-field">
            <span>本次目标</span>
            <input v-model.trim="studyGoal" type="text" maxlength="40" placeholder="例如：完成高数习题第 3 章" />
          </label>

          <div class="form-field">
            <span>计划时长</span>
            <div class="duration-options" role="group" aria-label="计划时长">
              <button
                v-for="option in durationOptions"
                :key="option.value"
                type="button"
                :class="{ active: selectedDuration === option.value }"
                @click="selectedDuration = option.value"
              >
                {{ option.label }}
              </button>
            </div>
            <input
              v-if="selectedDuration === 'custom'"
              v-model.number="customDuration"
              class="custom-duration"
              type="number"
              min="10"
              max="240"
              step="5"
              aria-label="自定义自习分钟数"
            />
          </div>

          <label class="form-field">
            <span>摄像头</span>
            <select v-model="selectedDeviceId">
              <option value="">默认摄像头</option>
              <option v-for="(device, index) in cameraDevices" :key="device.deviceId" :value="device.deviceId">
                {{ device.label || `摄像头 ${index + 1}` }}
              </option>
            </select>
          </label>

          <div class="vlog-option" :class="{ active: vlogEnabled }">
            <label class="vlog-toggle">
              <input v-model="vlogEnabled" type="checkbox" />
              <span class="toggle-box" aria-hidden="true">
                <Video :size="16" />
              </span>
              <span>
                <strong>录制学习 Vlog</strong>
                <small>结束后由后端生成 MP4 延时摄影，可预览、下载或删除。</small>
              </span>
            </label>

            <div v-if="vlogEnabled" class="vlog-settings">
              <label>
                <span>抽帧间隔</span>
                <select v-model.number="timelapseInterval">
                  <option :value="3">每 3 秒</option>
                  <option :value="5">每 5 秒</option>
                  <option :value="8">每 8 秒</option>
                </select>
              </label>
              <label>
                <span>成片长度</span>
                <select v-model="timelapseLength">
                  <option value="auto">自动</option>
                  <option value="15">15 秒</option>
                  <option value="30">30 秒</option>
                  <option value="60">60 秒</option>
                </select>
              </label>
            </div>
          </div>

          <p v-if="cameraError" class="camera-error">{{ cameraError }}</p>

          <button class="start-button" type="button" :disabled="isPreparing" @click="startStudy">
            <Play :size="18" fill="currentColor" />
            <span>{{ isPreparing ? '正在打开摄像头' : '开启自习' }}</span>
          </button>
        </article>

        <aside class="classroom-preview" aria-label="自习室预览">
          <div class="preview-board">
            <span>今日自习</span>
            <strong>{{ normalizedGoal }}</strong>
          </div>
          <div class="preview-clock">
            <Clock3 :size="22" />
            <strong>{{ plannedMinutes }} min</strong>
          </div>
          <div class="preview-desk"></div>
        </aside>
      </section>

      <section v-else-if="sessionMode === 'summary'" class="summary-layout">
        <article class="summary-panel">
          <div class="summary-head">
            <div>
              <p class="eyebrow">Study Report</p>
              <h2>本次自习完成</h2>
            </div>
            <span>{{ summary.finishedAt }}</span>
          </div>

          <div class="summary-stats">
            <div>
              <strong>{{ formatDuration(summary.elapsedSeconds) }}</strong>
              <span>学习时长</span>
            </div>
            <div>
              <strong>{{ formatDuration(summary.focusSeconds) }}</strong>
              <span>专注时长</span>
            </div>
            <div>
              <strong>{{ summary.focusRate }}%</strong>
              <span>专注率</span>
            </div>
            <div>
              <strong>{{ summary.awayCount }}</strong>
              <span>离席次数</span>
            </div>
            <div>
              <strong>{{ summary.alertCount }}</strong>
              <span>提醒次数</span>
            </div>
          </div>

          <div class="summary-goal">
            <Target :size="18" />
            <span>{{ summary.goal }}</span>
          </div>

          <div class="summary-actions">
            <button class="secondary-button" type="button" @click="resetRoom">
              <RotateCcw :size="17" />
              <span>再来一轮</span>
            </button>
            <button class="secondary-button" type="button" :class="{ saved: savedToRecord }" @click="saveStudyRecord">
              <BookmarkCheck :size="17" />
              <span>{{ savedToRecord ? '已保存' : '保存记录' }}</span>
            </button>
          </div>
        </article>

        <article class="vlog-result">
          <div class="panel-title">
            <Clapperboard :size="19" />
            <h2>学习延时摄影</h2>
          </div>

          <div v-if="!summary.vlogEnabled" class="timelapse-empty">
            <VideoOff :size="34" />
            <strong>本次未开启 Vlog</strong>
            <span>下次开始前勾选录制，就能在这里生成回放。</span>
          </div>

          <div v-else-if="timelapseStatus === 'generating'" class="timelapse-empty">
            <LoaderCircle :size="34" class="spinning" />
            <strong>正在生成延时摄影</strong>
            <span>已捕捉 {{ timelapseFrameCount }} 帧，稍等一下就可以预览。</span>
          </div>

          <div v-else-if="timelapseStatus === 'ready'" class="timelapse-ready">
            <video :src="timelapseUrl" controls playsinline></video>
            <div class="timelapse-actions">
              <button class="primary-mini" type="button" :disabled="timelapseActionBusy" @click="downloadTimelapse">
                <Download :size="16" />
                <span>下载</span>
              </button>
              <button class="secondary-mini" type="button" :disabled="timelapseActionBusy" @click="deleteTimelapse">
                <Trash2 :size="16" />
                <span>删除</span>
              </button>
            </div>
          </div>

          <div v-else-if="timelapseStatus === 'deleted'" class="timelapse-empty">
            <VideoOff :size="34" />
            <strong>延时摄影已删除</strong>
            <span>本次自习总结仍然保留，原始抽帧和成片已从后端清理。</span>
          </div>

          <div v-else class="timelapse-empty">
            <CircleAlert :size="34" />
            <strong>暂时无法生成视频</strong>
            <span>可能是本次抽帧不足，或后端 FFmpeg 暂未配置，本次自习总结已经保留。</span>
          </div>
        </article>
      </section>

      <section v-else class="session-layout">
        <article class="camera-panel">
          <div class="camera-toolbar">
            <div>
              <span class="live-dot" :class="{ paused: sessionMode === 'paused' }"></span>
              <strong>{{ sessionMode === 'paused' ? '已暂停' : '自习进行中' }}</strong>
            </div>
            <span v-if="vlogEnabled" class="recording-chip">
              <CircleDot :size="14" fill="currentColor" />
              Vlog 录制中
            </span>
          </div>

          <div class="camera-frame">
            <video ref="videoRef" autoplay muted playsinline></video>
            <div v-if="!streamReady" class="camera-placeholder">
              <Camera :size="38" />
              <strong>正在连接摄像头</strong>
              <span>请在浏览器权限弹窗中允许访问摄像头。</span>
            </div>
            <div class="status-overlay" :class="currentStatus.tone">
              <component :is="currentStatus.icon" :size="18" />
              <span>{{ currentStatus.label }}</span>
            </div>
            <div class="time-overlay">{{ elapsedText }}</div>
          </div>

          <canvas ref="snapshotCanvasRef" class="hidden-canvas"></canvas>

          <div class="session-controls">
            <button class="control-button" type="button" @click="togglePause">
              <component :is="sessionMode === 'paused' ? Play : Pause" :size="18" />
              <span>{{ sessionMode === 'paused' ? '继续' : '暂停' }}</span>
            </button>
            <button class="control-button" type="button" @click="switchCamera">
              <RefreshCw :size="18" />
              <span>切换摄像头</span>
            </button>
            <button class="end-button" type="button" :disabled="isFinishing" @click="endStudy">
              <Square :size="17" fill="currentColor" />
              <span>{{ isFinishing ? '正在结束' : '结束自习' }}</span>
            </button>
          </div>
        </article>

        <aside class="monitor-panel">
          <div class="panel-title">
            <ScanEye :size="19" />
            <h2>监督状态</h2>
          </div>

          <div class="focus-ring" :style="{ '--progress': `${sessionProgress}%` }">
            <strong>{{ focusRate }}%</strong>
            <span>专注率</span>
          </div>

          <div class="metric-grid">
            <div>
              <strong>{{ elapsedText }}</strong>
              <span>本次时长</span>
            </div>
            <div>
              <strong>{{ focusText }}</strong>
              <span>专注时长</span>
            </div>
            <div>
              <strong>{{ awayCount }}</strong>
              <span>离席次数</span>
            </div>
            <div>
              <strong>{{ alertCount }}</strong>
              <span>提醒次数</span>
            </div>
          </div>

          <div class="goal-note">
            <Target :size="17" />
            <span>{{ normalizedGoal }}</span>
          </div>
        </aside>

        <article class="reminder-panel">
          <div class="panel-title">
            <BellRing :size="19" />
            <h2>提醒记录</h2>
          </div>
          <ol class="reminder-list">
            <li v-for="item in reminderLog" :key="item.id" :class="item.tone">
              <span>{{ item.time }}</span>
              <strong>{{ item.text }}</strong>
            </li>
          </ol>
        </article>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  BellRing,
  BookmarkCheck,
  Camera,
  CircleAlert,
  CircleDot,
  Clapperboard,
  ClipboardList,
  Clock3,
  Download,
  Eye,
  LoaderCircle,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  ScanEye,
  Square,
  Target,
  Trash2,
  Users,
  UserX,
  Video,
  VideoOff
} from 'lucide-vue-next'
import {
  deleteStudyRoomTimelapse,
  downloadWithToken,
  finishStudyRoomSession,
  getStudyRoomTimelapse,
  resolveApiUrl,
  startStudyRoomSession,
  uploadStudyRoomFrame
} from '../api/apis'

const durationOptions = [
  { label: '25 分钟', value: 25 },
  { label: '45 分钟', value: 45 },
  { label: '60 分钟', value: 60 },
  { label: '自定义', value: 'custom' }
]

const detectionStatuses = [
  {
    code: 'focused',
    label: '专注中',
    message: '状态很好，继续保持。',
    tone: 'good',
    icon: Eye
  },
  {
    code: 'away',
    label: '离开座位',
    message: '画面中暂时没有检测到你。',
    tone: 'warn',
    icon: UserX
  },
  {
    code: 'phone_detected',
    label: '疑似玩手机',
    message: '检测到分心动作，先把手机放到一边。',
    tone: 'danger',
    icon: CircleAlert
  },
  {
    code: 'multiple_people',
    label: '多人入镜',
    message: '检测到多人入镜，请确认自习环境。',
    tone: 'warn',
    icon: Users
  },
  {
    code: 'unknown',
    label: '分析中',
    message: '正在分析当前学习状态。',
    tone: 'warn',
    icon: ScanEye
  }
]

const detectionStatusMap = Object.fromEntries(detectionStatuses.map(status => [status.code, status]))

const normalizeBackendState = state => {
  if (state === 'phone') return 'phone_detected'
  return state || 'unknown'
}

const resolveDetectionStatus = state => {
  return detectionStatusMap[normalizeBackendState(state)] || detectionStatusMap.unknown
}

const studyGoal = ref('')
const selectedDuration = ref(45)
const customDuration = ref(60)
const selectedDeviceId = ref('')
const cameraDevices = ref([])
const vlogEnabled = ref(false)
const timelapseInterval = ref(5)
const timelapseLength = ref('auto')

const sessionMode = ref('setup')
const isPreparing = ref(false)
const isFinishing = ref(false)
const streamReady = ref(false)
const cameraError = ref('')
const videoRef = ref(null)
const snapshotCanvasRef = ref(null)
const activeStream = ref(null)
const activeSessionId = ref('')
const frameUploadIntervalSeconds = ref(2)

const elapsedSeconds = ref(0)
const focusSeconds = ref(0)
const awayCount = ref(0)
const alertCount = ref(0)
const reminderLog = ref([])
const currentStatus = ref(resolveDetectionStatus('focused'))
const savedToRecord = ref(false)

const timelapseFrameCount = ref(0)
const timelapseStatus = ref('idle')
const timelapseUrl = ref('')
const timelapseActionBusy = ref(false)
const summary = ref({
  goal: '',
  elapsedSeconds: 0,
  focusSeconds: 0,
  focusRate: 0,
  awayCount: 0,
  alertCount: 0,
  vlogEnabled: false,
  finishedAt: ''
})

let clockTimer = null
let detectionTimer = null
let timelapsePollTimer = null
let reminderSeed = 0
let uploadInFlight = false
let uploadErrorNotified = false
let lastVlogCaptureSecond = Number.NEGATIVE_INFINITY

const normalizedGoal = computed(() => studyGoal.value || '完成一次专注自习')

const plannedMinutes = computed(() => {
  if (selectedDuration.value === 'custom') {
    return Math.max(10, Math.min(240, Number(customDuration.value) || 60))
  }
  return Number(selectedDuration.value)
})

const targetSeconds = computed(() => plannedMinutes.value * 60)

const elapsedText = computed(() => formatDuration(elapsedSeconds.value))
const focusText = computed(() => formatDuration(focusSeconds.value))

const focusRate = computed(() => {
  if (!elapsedSeconds.value) return 100
  return Math.round((focusSeconds.value / elapsedSeconds.value) * 100)
})

const sessionProgress = computed(() => {
  if (!targetSeconds.value) return 0
  return Math.min(100, Math.round((elapsedSeconds.value / targetSeconds.value) * 100))
})

const sessionStateText = computed(() => {
  if (sessionMode.value === 'setup') return '准备中'
  if (sessionMode.value === 'running') return '监督中'
  if (sessionMode.value === 'paused') return '已暂停'
  return '已完成'
})

const stateIcon = computed(() => {
  if (sessionMode.value === 'running') return ScanEye
  if (sessionMode.value === 'paused') return Pause
  if (sessionMode.value === 'summary') return BookmarkCheck
  return Clock3
})

const formatDuration = seconds => {
  const safeSeconds = Math.max(0, Math.floor(Number(seconds) || 0))
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const restSeconds = safeSeconds % 60

  if (hours > 0) {
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(restSeconds).padStart(2, '0')}`
  }

  return `${String(minutes).padStart(2, '0')}:${String(restSeconds).padStart(2, '0')}`
}

const readableFinishedAt = () => {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date())
}

const unwrapApiData = result => result?.data?.data ?? result?.data ?? result ?? {}

const errorMessage = (error, fallback) => {
  return error?.response?.data?.detail || error?.response?.data?.msg || error?.message || fallback
}

const timelapseTargetSeconds = () => {
  if (timelapseLength.value === 'auto') return null
  const value = Number(timelapseLength.value)
  return Number.isFinite(value) ? value : null
}

const toneFromReminder = reminder => {
  if (reminder?.level === 'danger') return 'danger'
  if (reminder?.level === 'warning') return 'warn'
  return resolveDetectionStatus(reminder?.type).tone || 'warn'
}

const refreshCameraDevices = async () => {
  if (!navigator.mediaDevices?.enumerateDevices) return
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameraDevices.value = devices.filter(device => device.kind === 'videoinput')
  } catch (error) {
    console.warn('[StudyRoom] enumerate devices failed:', error)
  }
}

const startStudy = async () => {
  if (isPreparing.value) return
  cameraError.value = ''
  isPreparing.value = true
  clearTimelapseUrl()
  stopRuntimeLoops()

  resetSessionStats()
  sessionMode.value = 'running'
  await nextTick()

  try {
    await openCamera()
    const sessionData = unwrapApiData(await startStudyRoomSession({
      goal: normalizedGoal.value,
      planned_minutes: plannedMinutes.value,
      vlog_enabled: vlogEnabled.value,
      timelapse_interval_seconds: timelapseInterval.value,
      timelapse_target_seconds: timelapseTargetSeconds()
    }))

    activeSessionId.value = sessionData.session_id || ''
    if (!activeSessionId.value) {
      throw new Error('后端没有返回自习室会话 ID')
    }

    frameUploadIntervalSeconds.value = Math.max(1, Number(sessionData.frame_upload_interval_seconds || 2))
    timelapseStatus.value = vlogEnabled.value ? 'capturing' : 'disabled'
    startClock()
    startFrameUploadLoop()
    await uploadCurrentFrame({ force: true, saveForVlog: vlogEnabled.value })
  } catch (error) {
    console.warn('[StudyRoom] start failed:', error)
    cameraError.value = errorMessage(error, '自习室启动失败，请确认摄像头权限、登录状态和后端服务。')
    sessionMode.value = 'setup'
    stopRuntimeLoops()
    stopCamera()
    activeSessionId.value = ''
  } finally {
    isPreparing.value = false
  }
}

const openCamera = async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('getUserMedia unsupported')
  }

  stopCamera()

  const videoConstraints = {
    width: { ideal: 1280 },
    height: { ideal: 720 },
    facingMode: 'user'
  }

  if (selectedDeviceId.value) {
    videoConstraints.deviceId = { exact: selectedDeviceId.value }
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    video: videoConstraints,
    audio: false
  })

  activeStream.value = stream
  streamReady.value = true

  if (videoRef.value) {
    videoRef.value.srcObject = stream
    await videoRef.value.play()
  }

  await refreshCameraDevices()
}

const stopCamera = () => {
  if (activeStream.value) {
    activeStream.value.getTracks().forEach(track => track.stop())
  }
  activeStream.value = null
  streamReady.value = false

  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
}

const resetSessionStats = () => {
  activeSessionId.value = ''
  frameUploadIntervalSeconds.value = 2
  elapsedSeconds.value = 0
  focusSeconds.value = 0
  awayCount.value = 0
  alertCount.value = 0
  reminderLog.value = []
  currentStatus.value = resolveDetectionStatus('focused')
  savedToRecord.value = false
  timelapseFrameCount.value = 0
  timelapseStatus.value = 'idle'
  timelapseActionBusy.value = false
  uploadErrorNotified = false
  lastVlogCaptureSecond = Number.NEGATIVE_INFINITY
}

const startClock = () => {
  window.clearInterval(clockTimer)
  clockTimer = window.setInterval(() => {
    if (sessionMode.value !== 'running') return

    elapsedSeconds.value += 1
    if (currentStatus.value.code === 'focused') {
      focusSeconds.value += 1
    }

    if (elapsedSeconds.value === targetSeconds.value) {
      addReminder('计划时长已完成，可以结束或继续保持。', 'good')
    }
  }, 1000)
}

const startFrameUploadLoop = () => {
  window.clearInterval(detectionTimer)
  currentStatus.value = resolveDetectionStatus('focused')
  detectionTimer = window.setInterval(() => {
    uploadCurrentFrame()
  }, frameUploadIntervalSeconds.value * 1000)
}

const uploadCurrentFrame = async ({ force = false, saveForVlog = null } = {}) => {
  if (!activeSessionId.value || uploadInFlight) return false
  if (!force && sessionMode.value !== 'running') return false

  uploadInFlight = true
  try {
    const frameBlob = await captureStudyFrameBlob()
    if (!frameBlob) return false

    const shouldSaveForVlog = Boolean(vlogEnabled.value && (saveForVlog ?? shouldSaveVlogFrame()))
    const currentElapsed = Math.max(0, Math.floor(elapsedSeconds.value))
    const formData = new FormData()
    formData.append('frame', frameBlob, `study-room-${Date.now()}.jpg`)
    formData.append('client_elapsed_seconds', String(currentElapsed))
    formData.append('save_for_vlog', shouldSaveForVlog ? 'true' : 'false')

    const payload = unwrapApiData(await uploadStudyRoomFrame(activeSessionId.value, formData))
    applyFramePayload(payload)
    uploadErrorNotified = false

    if (shouldSaveForVlog) {
      lastVlogCaptureSecond = currentElapsed
      timelapseFrameCount.value += 1
    }

    return true
  } catch (error) {
    console.warn('[StudyRoom] frame upload failed:', error)
    if (!uploadErrorNotified) {
      addReminder(errorMessage(error, '画面上传失败，正在保留本地计时。'), 'danger')
      uploadErrorNotified = true
    }
    return false
  } finally {
    uploadInFlight = false
  }
}

const shouldSaveVlogFrame = () => {
  if (!vlogEnabled.value) return false
  if (!Number.isFinite(lastVlogCaptureSecond)) return true
  return elapsedSeconds.value - lastVlogCaptureSecond >= timelapseInterval.value
}

const captureStudyFrameBlob = async () => {
  if (!videoRef.value || !snapshotCanvasRef.value) return null
  if (!videoRef.value.videoWidth || !videoRef.value.videoHeight) return null

  const sourceWidth = videoRef.value.videoWidth
  const sourceHeight = videoRef.value.videoHeight
  const canvasWidth = 960
  const canvasHeight = Math.round((sourceHeight / sourceWidth) * canvasWidth)
  const canvas = snapshotCanvasRef.value
  const context = canvas.getContext('2d')
  if (!context) return null

  canvas.width = canvasWidth
  canvas.height = canvasHeight
  context.drawImage(videoRef.value, 0, 0, canvasWidth, canvasHeight)
  context.fillStyle = 'rgba(42, 33, 20, 0.58)'
  context.fillRect(0, canvasHeight - 54, canvasWidth, 54)
  context.fillStyle = '#fff6df'
  context.font = '600 24px "Microsoft YaHei", sans-serif'
  context.fillText(`${normalizedGoal.value} · ${formatDuration(elapsedSeconds.value)}`, 24, canvasHeight - 20)

  return canvasToBlob(canvas)
}

const canvasToBlob = canvas => new Promise(resolve => {
  canvas.toBlob(blob => resolve(blob), 'image/jpeg', 0.78)
})

const applyFramePayload = payload => {
  const nextStatus = resolveDetectionStatus(payload?.state)
  currentStatus.value = payload?.message
    ? { ...nextStatus, message: payload.message }
    : nextStatus

  applyMetrics(payload?.metrics)

  if (payload?.reminder?.message) {
    addReminder(payload.reminder.message, toneFromReminder(payload.reminder))
  }
}

const applyMetrics = (metrics = {}, { authoritative = false } = {}) => {
  const nextElapsed = Number(metrics.elapsed_seconds ?? elapsedSeconds.value)
  const nextFocus = Number(metrics.focus_seconds ?? focusSeconds.value)

  elapsedSeconds.value = authoritative ? Math.max(0, nextElapsed) : Math.max(elapsedSeconds.value, nextElapsed)
  focusSeconds.value = authoritative ? Math.max(0, nextFocus) : Math.max(focusSeconds.value, nextFocus)

  if (metrics.away_count !== undefined) {
    awayCount.value = Math.max(0, Number(metrics.away_count) || 0)
  }
  if (metrics.alert_count !== undefined) {
    alertCount.value = Math.max(0, Number(metrics.alert_count) || 0)
  }
}

const addReminder = (text, tone = 'warn') => {
  reminderSeed += 1
  reminderLog.value = [
    {
      id: `${Date.now()}-${reminderSeed}`,
      text,
      tone,
      time: formatDuration(elapsedSeconds.value)
    },
    ...reminderLog.value
  ].slice(0, 8)
}

const togglePause = () => {
  if (sessionMode.value === 'running') {
    sessionMode.value = 'paused'
    addReminder('自习已暂停，计时和检测暂时停止。', 'muted')
    return
  }

  if (sessionMode.value === 'paused') {
    sessionMode.value = 'running'
    addReminder('自习已继续，保持现在的节奏。', 'good')
  }
}

const switchCamera = async () => {
  if (!cameraDevices.value.length) {
    await refreshCameraDevices()
  }

  if (cameraDevices.value.length > 1) {
    const currentIndex = cameraDevices.value.findIndex(device => device.deviceId === selectedDeviceId.value)
    const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % cameraDevices.value.length : 0
    selectedDeviceId.value = cameraDevices.value[nextIndex].deviceId
  }

  try {
    await openCamera()
    addReminder('摄像头已切换。', 'good')
  } catch (error) {
    console.warn('[StudyRoom] switch camera failed:', error)
    addReminder('摄像头切换失败，请检查设备状态。', 'danger')
  }
}

const endStudy = async () => {
  if (isFinishing.value || (sessionMode.value !== 'running' && sessionMode.value !== 'paused')) return
  if (!activeSessionId.value) return

  isFinishing.value = true
  try {
    if (vlogEnabled.value) {
      await uploadCurrentFrame({ force: true, saveForVlog: true })
    }

    const payload = unwrapApiData(await finishStudyRoomSession(activeSessionId.value, {
      client_elapsed_seconds: Math.max(0, Math.floor(elapsedSeconds.value))
    }))

    stopRuntimeLoops()
    applyFinishPayload(payload)
    applyTimelapsePayload(payload.timelapse)
    sessionMode.value = 'summary'
    stopCamera()

    if (timelapseStatus.value === 'generating') {
      startTimelapsePolling()
    }
  } catch (error) {
    console.warn('[StudyRoom] finish failed:', error)
    addReminder(errorMessage(error, '结束自习失败，请稍后再试。'), 'danger')
  } finally {
    isFinishing.value = false
  }
}

const applyFinishPayload = payload => {
  const report = payload?.summary || {}
  const metrics = {
    elapsed_seconds: report.elapsed_seconds ?? elapsedSeconds.value,
    focus_seconds: report.focus_seconds ?? focusSeconds.value,
    away_count: report.away_count ?? awayCount.value,
    alert_count: report.alert_count ?? alertCount.value
  }
  applyMetrics(metrics, { authoritative: true })

  summary.value = {
    goal: report.goal || normalizedGoal.value,
    elapsedSeconds: elapsedSeconds.value,
    focusSeconds: focusSeconds.value,
    focusRate: Number(report.focus_rate ?? focusRate.value) || 0,
    awayCount: awayCount.value,
    alertCount: alertCount.value,
    vlogEnabled: Boolean(payload?.timelapse?.enabled ?? vlogEnabled.value),
    finishedAt: readableFinishedAt()
  }
}

const applyTimelapsePayload = (payload = {}) => {
  const status = payload.status || (summary.value.vlogEnabled ? 'failed' : 'disabled')
  const nextUrl = payload.url ? resolveApiUrl(payload.url) : ''

  timelapseStatus.value = status
  timelapseFrameCount.value = Math.max(0, Number(payload.frame_count ?? timelapseFrameCount.value) || 0)

  if (nextUrl !== timelapseUrl.value) {
    clearTimelapseUrl()
    timelapseUrl.value = nextUrl
  }
}

const startTimelapsePolling = () => {
  stopTimelapsePolling()
  timelapsePollTimer = window.setInterval(refreshTimelapseStatus, 3000)
  refreshTimelapseStatus()
}

const refreshTimelapseStatus = async () => {
  if (!activeSessionId.value) return

  try {
    const payload = unwrapApiData(await getStudyRoomTimelapse(activeSessionId.value))
    applyTimelapsePayload(payload)
    if (isTimelapseTerminal(timelapseStatus.value)) {
      stopTimelapsePolling()
    }
  } catch (error) {
    console.warn('[StudyRoom] timelapse poll failed:', error)
  }
}

const stopTimelapsePolling = () => {
  window.clearInterval(timelapsePollTimer)
  timelapsePollTimer = null
}

const stopRuntimeLoops = () => {
  window.clearInterval(clockTimer)
  window.clearInterval(detectionTimer)
  stopTimelapsePolling()
  clockTimer = null
  detectionTimer = null
}

const isTimelapseTerminal = status => {
  return ['disabled', 'ready', 'failed', 'deleted'].includes(status)
}

const clearTimelapseUrl = () => {
  if (timelapseUrl.value?.startsWith('blob:')) {
    URL.revokeObjectURL(timelapseUrl.value)
  }
  timelapseUrl.value = ''
}

const downloadTimelapse = async () => {
  if (!timelapseUrl.value || timelapseActionBusy.value) return

  timelapseActionBusy.value = true
  try {
    await downloadWithToken(timelapseUrl.value, `自习延时摄影-${Date.now()}.mp4`)
  } catch (error) {
    console.warn('[StudyRoom] download timelapse failed:', error)
  } finally {
    timelapseActionBusy.value = false
  }
}

const deleteTimelapse = async () => {
  if (timelapseActionBusy.value) return

  timelapseActionBusy.value = true
  try {
    if (activeSessionId.value) {
      await deleteStudyRoomTimelapse(activeSessionId.value)
    }
    clearTimelapseUrl()
    timelapseFrameCount.value = 0
    timelapseStatus.value = 'deleted'
  } catch (error) {
    console.warn('[StudyRoom] delete timelapse failed:', error)
  } finally {
    timelapseActionBusy.value = false
  }
}

const saveStudyRecord = () => {
  savedToRecord.value = true
}

const resetRoom = () => {
  stopRuntimeLoops()
  stopCamera()
  clearTimelapseUrl()
  resetSessionStats()
  sessionMode.value = 'setup'
}

onMounted(() => {
  refreshCameraDevices()
})

onBeforeUnmount(() => {
  stopRuntimeLoops()
  stopCamera()
  clearTimelapseUrl()
})
</script>

<style scoped>
.study-room-page {
  position: relative;
  min-height: 100vh;
  padding: 28px clamp(18px, 3.5vw, 48px) 34px;
  color: #3b2a16;
  overflow: hidden;
  isolation: isolate;
  font-family:
    Inter,
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
}

.classroom-bg {
  position: absolute;
  inset: 0;
  z-index: -2;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 244, 196, 0.94) 0%, rgba(247, 202, 104, 0.72) 58%, rgba(174, 103, 43, 0.42) 100%),
    repeating-linear-gradient(90deg, rgba(128, 76, 31, 0.08) 0 2px, transparent 2px 34px),
    #f3c45d;
}

.classroom-bg::before {
  content: "";
  position: absolute;
  inset: 0;
  opacity: 0.25;
  background-image:
    linear-gradient(90deg, rgba(255, 255, 255, 0.24) 1px, transparent 1px),
    linear-gradient(180deg, rgba(96, 59, 26, 0.16) 1px, transparent 1px);
  background-size: 86px 100%, 100% 76px;
}

.sun-wash {
  position: absolute;
  left: 9vw;
  top: 6vh;
  width: min(42vw, 540px);
  aspect-ratio: 1.2;
  background: radial-gradient(circle, rgba(255, 248, 207, 0.78), rgba(255, 236, 148, 0) 68%);
}

.blackboard-shape {
  position: absolute;
  left: clamp(24px, 6vw, 92px);
  right: clamp(24px, 6vw, 92px);
  top: 70px;
  height: clamp(148px, 22vh, 230px);
  border: 12px solid rgba(103, 66, 34, 0.88);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.08), transparent 32%),
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.035) 0 1px, transparent 1px 5px),
    #315f49;
  box-shadow:
    0 24px 48px rgba(103, 66, 34, 0.22),
    inset 0 0 36px rgba(11, 45, 32, 0.32);
}

.blackboard-shape span {
  position: absolute;
  left: 26px;
  height: 2px;
  border-radius: 999px;
  background: rgba(245, 239, 209, 0.72);
}

.blackboard-shape span:first-child {
  top: 38%;
  width: 26%;
}

.blackboard-shape span:last-child {
  top: 56%;
  width: 18%;
}

.desk-row {
  position: absolute;
  left: -5vw;
  right: -5vw;
  height: 56px;
  transform: skewY(-3deg);
  background:
    repeating-linear-gradient(90deg, transparent 0 80px, rgba(63, 36, 18, 0.2) 80px 84px),
    linear-gradient(180deg, rgba(174, 103, 43, 0.48), rgba(125, 70, 32, 0.34));
  border-top: 2px solid rgba(91, 53, 27, 0.24);
  border-bottom: 1px solid rgba(255, 240, 177, 0.3);
}

.desk-row-one {
  bottom: 28vh;
}

.desk-row-two {
  bottom: 18vh;
  opacity: 0.82;
}

.desk-grain {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: min(26vh, 230px);
  background:
    repeating-linear-gradient(100deg, rgba(255, 223, 147, 0.18) 0 2px, transparent 2px 16px),
    repeating-linear-gradient(0deg, rgba(78, 43, 20, 0.18) 0 1px, transparent 1px 24px),
    linear-gradient(180deg, #b66c35, #8e4f29 58%, #6d391f);
  box-shadow: inset 0 12px 24px rgba(255, 234, 173, 0.22);
}

.study-room-shell {
  position: relative;
  width: min(1360px, 100%);
  min-height: calc(100vh - 126px);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.room-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.eyebrow {
  margin: 0 0 7px;
  color: #9a4f21;
  font-size: 12px;
  font-weight: 900;
}

.room-header h1,
.summary-head h2 {
  margin: 0;
  color: #2d1d10;
  font-size: clamp(28px, 3.4vw, 46px);
  font-weight: 950;
  line-height: 1.08;
}

.room-header p:last-child {
  max-width: 620px;
  margin: 9px 0 0;
  color: #76502e;
  font-size: 14px;
  line-height: 1.7;
  font-weight: 700;
}

.room-state-pill {
  min-height: 42px;
  padding: 0 15px;
  border: 1px solid rgba(67, 43, 23, 0.18);
  border-radius: 999px;
  background: rgba(255, 247, 220, 0.78);
  color: #5f3c20;
  box-shadow: 0 12px 28px rgba(89, 49, 20, 0.12);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 900;
  white-space: nowrap;
}

.room-state-pill.running {
  background: rgba(45, 95, 73, 0.92);
  color: #fff8df;
}

.room-state-pill.paused {
  background: rgba(143, 75, 32, 0.92);
  color: #fff8df;
}

.room-state-pill.summary {
  background: rgba(22, 63, 143, 0.92);
  color: #ffffff;
}

.setup-grid,
.summary-layout,
.session-layout {
  min-height: 0;
  flex: 1;
  display: grid;
  gap: 18px;
}

.setup-grid {
  grid-template-columns: minmax(340px, 0.48fr) minmax(520px, 1fr);
  align-items: stretch;
}

.setup-panel,
.classroom-preview,
.summary-panel,
.vlog-result,
.camera-panel,
.monitor-panel,
.reminder-panel {
  border: 1px solid rgba(92, 57, 28, 0.22);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(255, 249, 226, 0.94), rgba(255, 238, 185, 0.84)),
    rgba(255, 246, 215, 0.9);
  box-shadow:
    0 18px 42px rgba(95, 55, 22, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(130%);
  -webkit-backdrop-filter: blur(14px) saturate(130%);
}

.setup-panel {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 17px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #2d1d10;
}

.panel-title h2 {
  margin: 0;
  font-size: 17px;
  line-height: 1.25;
}

.form-field {
  display: grid;
  gap: 8px;
  color: #5f3c20;
  font-size: 13px;
  font-weight: 900;
}

.form-field input,
.form-field select,
.vlog-settings select {
  width: 100%;
  height: 42px;
  border: 1px solid rgba(92, 57, 28, 0.22);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.84);
  color: #3b2a16;
  padding: 0 12px;
  font: inherit;
  outline: none;
}

.form-field input:focus,
.form-field select:focus,
.vlog-settings select:focus {
  border-color: #315f49;
  box-shadow: 0 0 0 3px rgba(49, 95, 73, 0.14);
}

.duration-options {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.duration-options button {
  min-height: 40px;
  border: 1px solid rgba(92, 57, 28, 0.2);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.72);
  color: #6f4725;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.duration-options button:hover,
.duration-options button.active {
  border-color: #315f49;
  background: #315f49;
  color: #fff8df;
  transform: translateY(-1px);
}

.custom-duration {
  max-width: 160px;
}

.vlog-option {
  padding: 14px;
  border: 1px solid rgba(92, 57, 28, 0.2);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.58);
}

.vlog-option.active {
  border-color: rgba(49, 95, 73, 0.48);
  background: rgba(245, 250, 225, 0.78);
}

.vlog-toggle {
  display: grid;
  grid-template-columns: 0 38px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.vlog-toggle input {
  opacity: 0;
}

.toggle-box {
  width: 38px;
  height: 38px;
  border: 1px solid rgba(92, 57, 28, 0.24);
  border-radius: 8px;
  background: #fff8df;
  color: #9a4f21;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

.vlog-toggle input:checked + .toggle-box {
  border-color: #315f49;
  background: #315f49;
  color: #fff8df;
}

.vlog-toggle strong,
.vlog-toggle small {
  display: block;
}

.vlog-toggle strong {
  color: #2d1d10;
  font-size: 14px;
}

.vlog-toggle small {
  margin-top: 3px;
  color: #76502e;
  font-size: 12px;
  line-height: 1.5;
}

.vlog-settings {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(92, 57, 28, 0.16);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.vlog-settings label {
  display: grid;
  gap: 7px;
  color: #5f3c20;
  font-size: 12px;
  font-weight: 900;
}

.camera-error {
  margin: 0;
  padding: 11px 12px;
  border: 1px solid rgba(165, 56, 38, 0.3);
  border-radius: 8px;
  background: rgba(255, 231, 219, 0.8);
  color: #8f2f23;
  font-size: 13px;
  line-height: 1.5;
}

.start-button,
.end-button,
.control-button,
.secondary-button,
.primary-mini,
.secondary-mini {
  border: 0;
  border-radius: 8px;
  font: inherit;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.start-button {
  min-height: 48px;
  margin-top: auto;
  background: #315f49;
  color: #fff8df;
  box-shadow: 0 12px 24px rgba(49, 95, 73, 0.22);
}

.start-button:hover:not(:disabled),
.end-button:hover:not(:disabled),
.control-button:hover:not(:disabled),
.secondary-button:hover:not(:disabled),
.primary-mini:hover:not(:disabled),
.secondary-mini:hover:not(:disabled) {
  transform: translateY(-2px);
}

.start-button:disabled,
.end-button:disabled,
.control-button:disabled,
.secondary-button:disabled,
.primary-mini:disabled,
.secondary-mini:disabled {
  opacity: 0.72;
  cursor: wait;
}

.classroom-preview {
  position: relative;
  overflow: hidden;
  min-height: 520px;
  padding: 26px;
  background:
    linear-gradient(180deg, rgba(255, 245, 203, 0.82), rgba(247, 203, 111, 0.52)),
    #f2c861;
}

.classroom-preview::before {
  content: "";
  position: absolute;
  left: 8%;
  right: 8%;
  top: 34px;
  height: 45%;
  border: 12px solid #6b4227;
  border-radius: 8px;
  background:
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.045) 0 1px, transparent 1px 6px),
    #315f49;
  box-shadow: 0 24px 36px rgba(80, 46, 22, 0.2);
}

.preview-board {
  position: relative;
  z-index: 2;
  width: min(430px, 78%);
  margin: 60px auto 0;
  color: #fff8df;
  text-align: center;
  display: grid;
  gap: 12px;
}

.preview-board span {
  font-size: 13px;
  font-weight: 900;
  opacity: 0.86;
}

.preview-board strong {
  font-size: clamp(24px, 3vw, 38px);
  line-height: 1.2;
}

.preview-clock {
  position: absolute;
  right: 38px;
  top: 38px;
  z-index: 3;
  width: 112px;
  aspect-ratio: 1;
  border: 8px solid #fff6df;
  border-radius: 50%;
  background: #f7e2a3;
  color: #5f3c20;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 5px;
  box-shadow: 0 12px 26px rgba(80, 46, 22, 0.18);
}

.preview-clock strong {
  font-size: 18px;
}

.preview-desk {
  position: absolute;
  left: 7%;
  right: 7%;
  bottom: 0;
  height: 34%;
  border-radius: 8px 8px 0 0;
  background:
    repeating-linear-gradient(100deg, rgba(255, 226, 158, 0.25) 0 2px, transparent 2px 18px),
    linear-gradient(180deg, #bd7238, #8d4e29);
  box-shadow: inset 0 14px 24px rgba(255, 241, 190, 0.2);
}

.session-layout {
  grid-template-columns: minmax(520px, 1fr) minmax(300px, 0.34fr);
  grid-template-rows: minmax(360px, 1fr) minmax(170px, 0.38fr);
  grid-template-areas:
    "camera monitor"
    "camera reminders";
}

.camera-panel {
  grid-area: camera;
  min-height: 0;
  padding: 16px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 12px;
}

.camera-toolbar {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.camera-toolbar > div,
.recording-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #2d1d10;
  font-size: 13px;
  font-weight: 900;
}

.live-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #2f8f59;
  box-shadow: 0 0 0 6px rgba(47, 143, 89, 0.16);
}

.live-dot.paused {
  background: #a8632e;
  box-shadow: 0 0 0 6px rgba(168, 99, 46, 0.16);
}

.recording-chip {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(159, 42, 34, 0.1);
  color: #9f2a22;
}

.camera-frame {
  position: relative;
  min-height: 360px;
  border: 10px solid #6b4227;
  border-radius: 8px;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(39, 26, 14, 0.42), transparent),
    #24180f;
}

.camera-frame video {
  width: 100%;
  height: 100%;
  min-height: 100%;
  object-fit: cover;
  display: block;
  background: #20160e;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  color: #fff6df;
  background:
    linear-gradient(135deg, rgba(49, 95, 73, 0.72), rgba(43, 28, 15, 0.7)),
    #315f49;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
}

.camera-placeholder strong {
  font-size: 18px;
}

.camera-placeholder span {
  color: rgba(255, 246, 223, 0.78);
  font-size: 13px;
}

.status-overlay,
.time-overlay {
  position: absolute;
  z-index: 2;
  border-radius: 999px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.status-overlay {
  left: 16px;
  top: 16px;
  min-height: 38px;
  padding: 0 13px;
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 900;
}

.status-overlay.good {
  background: rgba(49, 95, 73, 0.86);
}

.status-overlay.warn {
  background: rgba(163, 91, 34, 0.9);
}

.status-overlay.danger {
  background: rgba(159, 42, 34, 0.9);
}

.time-overlay {
  right: 16px;
  bottom: 16px;
  min-height: 40px;
  padding: 0 14px;
  background: rgba(42, 28, 14, 0.72);
  color: #fff8df;
  display: inline-flex;
  align-items: center;
  font-size: 22px;
  font-weight: 900;
}

.hidden-canvas {
  display: none;
}

.session-controls {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.control-button,
.end-button {
  min-height: 44px;
}

.control-button {
  border: 1px solid rgba(92, 57, 28, 0.22);
  background: rgba(255, 253, 242, 0.78);
  color: #5f3c20;
}

.end-button {
  background: #9f2a22;
  color: #fff6df;
  box-shadow: 0 12px 22px rgba(159, 42, 34, 0.18);
}

.monitor-panel {
  grid-area: monitor;
  padding: 18px;
  display: grid;
  gap: 16px;
  align-content: start;
}

.focus-ring {
  --progress: 0%;
  width: min(190px, 100%);
  aspect-ratio: 1;
  margin: 0 auto;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, rgba(255, 248, 226, 0.98) 0 56%, transparent 57%),
    conic-gradient(#315f49 var(--progress), rgba(95, 60, 32, 0.16) 0);
  display: grid;
  place-items: center;
  align-content: center;
  gap: 4px;
}

.focus-ring strong {
  color: #315f49;
  font-size: 42px;
  line-height: 1;
}

.focus-ring span {
  color: #76502e;
  font-size: 13px;
  font-weight: 900;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metric-grid div {
  min-height: 72px;
  padding: 10px;
  border: 1px solid rgba(92, 57, 28, 0.16);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.58);
  display: grid;
  place-items: center;
  text-align: center;
}

.metric-grid strong {
  color: #2d1d10;
  font-size: 20px;
}

.metric-grid span {
  color: #76502e;
  font-size: 12px;
  font-weight: 900;
}

.goal-note,
.summary-goal {
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid rgba(49, 95, 73, 0.2);
  border-radius: 8px;
  background: rgba(245, 250, 225, 0.72);
  color: #315f49;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 900;
}

.reminder-panel {
  grid-area: reminders;
  min-height: 0;
  padding: 18px;
  overflow: hidden;
}

.reminder-list {
  height: calc(100% - 34px);
  min-height: 110px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 8px;
}

.reminder-list li {
  min-height: 44px;
  padding: 9px 10px;
  border: 1px solid rgba(92, 57, 28, 0.16);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.58);
  display: grid;
  gap: 2px;
}

.reminder-list li.good {
  border-color: rgba(49, 95, 73, 0.24);
  background: rgba(245, 250, 225, 0.72);
}

.reminder-list li.danger {
  border-color: rgba(159, 42, 34, 0.22);
  background: rgba(255, 234, 222, 0.68);
}

.reminder-list li.muted {
  opacity: 0.8;
}

.reminder-list span {
  color: #9a4f21;
  font-size: 11px;
  font-weight: 900;
}

.reminder-list strong {
  color: #3b2a16;
  font-size: 13px;
  line-height: 1.45;
}

.summary-layout {
  grid-template-columns: minmax(480px, 0.92fr) minmax(380px, 0.72fr);
  align-items: stretch;
}

.summary-panel,
.vlog-result {
  padding: 22px;
}

.summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.summary-head span {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(49, 95, 73, 0.12);
  color: #315f49;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.summary-stats {
  margin-top: 24px;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.summary-stats div {
  min-height: 96px;
  border: 1px solid rgba(92, 57, 28, 0.16);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.6);
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  text-align: center;
}

.summary-stats strong {
  color: #315f49;
  font-size: clamp(21px, 2.5vw, 32px);
  line-height: 1;
}

.summary-stats span {
  color: #76502e;
  font-size: 12px;
  font-weight: 900;
}

.summary-goal {
  margin-top: 18px;
}

.summary-actions,
.timelapse-actions {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.secondary-button {
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid rgba(92, 57, 28, 0.2);
  background: rgba(255, 253, 242, 0.76);
  color: #5f3c20;
}

.secondary-button.saved {
  border-color: rgba(49, 95, 73, 0.42);
  background: rgba(49, 95, 73, 0.12);
  color: #315f49;
}

.vlog-result {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
}

.timelapse-empty {
  min-height: 320px;
  border: 1px dashed rgba(92, 57, 28, 0.26);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.52);
  color: #76502e;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
}

.timelapse-empty strong {
  color: #2d1d10;
  font-size: 17px;
}

.timelapse-empty span {
  max-width: 340px;
  font-size: 13px;
  line-height: 1.6;
}

.spinning {
  animation: spin 1s linear infinite;
}

.timelapse-ready video {
  width: 100%;
  aspect-ratio: 16 / 10;
  border: 8px solid #6b4227;
  border-radius: 8px;
  background: #20160e;
  display: block;
}

.primary-mini,
.secondary-mini {
  min-height: 38px;
  padding: 0 13px;
}

.primary-mini {
  background: #315f49;
  color: #fff8df;
}

.secondary-mini {
  border: 1px solid rgba(92, 57, 28, 0.2);
  background: rgba(255, 253, 242, 0.76);
  color: #5f3c20;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1120px) {
  .setup-grid,
  .summary-layout,
  .session-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    grid-template-areas: none;
  }

  .camera-panel,
  .monitor-panel,
  .reminder-panel {
    grid-area: auto;
  }

  .classroom-preview {
    min-height: 420px;
  }
}

@media (max-width: 720px) {
  .study-room-page {
    min-height: 100vh;
    padding: 20px 14px 26px;
    overflow-y: auto;
  }

  .study-room-shell {
    min-height: 0;
  }

  .room-header,
  .summary-head {
    flex-direction: column;
  }

  .room-state-pill {
    align-self: flex-start;
  }

  .duration-options,
  .vlog-settings,
  .session-controls,
  .metric-grid,
  .summary-stats {
    grid-template-columns: 1fr;
  }

  .classroom-preview {
    min-height: 360px;
  }

  .preview-clock {
    width: 92px;
    right: 20px;
    top: 20px;
  }

  .camera-frame {
    min-height: 260px;
    border-width: 7px;
  }

  .time-overlay {
    font-size: 18px;
  }
}
</style>
