<template>
  <main class="mock-classroom-page">
    <div class="classroom-scene" aria-hidden="true">
      <div class="wall-light"></div>
      <div class="chalk-board-bg">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <div class="floor-lines"></div>
      <div class="teacher-desk-bg"></div>
    </div>

    <section class="mock-classroom-shell" aria-label="模拟课堂">
      <header class="classroom-header">
        <div>
          <p class="eyebrow">Teaching Studio</p>
          <h1>模拟课堂</h1>
          <p>把一个知识点讲给“学生”听，用主动输出检验自己是不是真的掌握。</p>
        </div>
        <div class="lesson-state" :class="lessonMode">
          <component :is="lessonStateIcon" :size="18" />
          <span>{{ lessonStateText }}</span>
        </div>
      </header>

      <section v-if="lessonMode === 'setup'" class="classroom-grid">
        <article class="setup-panel">
          <div class="panel-title">
            <BookOpenCheck :size="19" />
            <h2>本次试讲</h2>
          </div>

          <label class="form-field">
            <span>讲解主题</span>
            <input v-model.trim="topic" type="text" maxlength="60" placeholder="例如：二次函数的顶点式" />
          </label>

          <div class="form-field">
            <span>讲解时长</span>
            <div class="duration-options" role="group" aria-label="讲解时长">
              <button
                v-for="option in durationOptions"
                :key="option"
                type="button"
                :class="{ active: plannedMinutes === option }"
                @click="plannedMinutes = option"
              >
                {{ option }} 分钟
              </button>
            </div>
          </div>

          <label class="form-field">
            <span>参考要点</span>
            <textarea
              v-model.trim="referenceText"
              maxlength="600"
              placeholder="写下本节课必须讲清楚的概念、公式、例子或易错点"
            ></textarea>
          </label>

          <div class="device-grid">
            <label class="form-field">
              <span>摄像头</span>
              <select v-model="selectedCameraId" @change="handleDeviceChange">
                <option value="">默认摄像头</option>
                <option v-for="(device, index) in cameraDevices" :key="device.deviceId" :value="device.deviceId">
                  {{ device.label || `摄像头 ${index + 1}` }}
                </option>
              </select>
            </label>

            <label class="form-field">
              <span>麦克风</span>
              <select v-model="selectedMicId" @change="handleDeviceChange">
                <option value="">默认麦克风</option>
                <option v-for="(device, index) in micDevices" :key="device.deviceId" :value="device.deviceId">
                  {{ device.label || `麦克风 ${index + 1}` }}
                </option>
              </select>
            </label>
          </div>

          <p v-if="deviceError" class="device-error">{{ deviceError }}</p>

          <div class="setup-actions">
            <button class="secondary-button" type="button" :disabled="isPreparingDevices" @click="prepareDevices">
              <RefreshCw :size="17" />
              <span>{{ isPreparingDevices ? '检查中' : '检查设备' }}</span>
            </button>
            <button class="start-button" type="button" :disabled="!devicesReady || isStartingLesson" @click="startTeaching">
              <Play :size="18" fill="currentColor" />
              <span>{{ isStartingLesson ? '准备上课' : '开始讲课' }}</span>
            </button>
          </div>
        </article>

        <article class="stage-panel">
          <div class="board">
            <div class="board-topline">
              <span>Today's Topic</span>
              <Timer :size="18" />
            </div>
            <strong>{{ normalizedTopic }}</strong>
            <p>{{ boardHint }}</p>
            <div class="chalk-lines">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>

          <div class="device-preview" :class="{ ready: devicesReady }">
            <div class="preview-video">
              <video ref="deviceVideoRef" autoplay muted playsinline></video>
              <div v-if="!cameraReady" class="preview-placeholder">
                <VideoOff :size="30" />
                <strong>镜头待检查</strong>
              </div>
              <span class="preview-chip">
                <CheckCircle2 v-if="devicesReady" :size="15" />
                <Camera v-else :size="15" />
                {{ deviceStateText }}
              </span>
            </div>

            <div class="mic-meter">
              <div>
                <AudioLines :size="18" />
                <span>{{ micReady ? '麦克风已连接' : '麦克风待检查' }}</span>
              </div>
              <div class="meter-track">
                <span :style="{ width: `${micLevel}%` }"></span>
              </div>
            </div>
          </div>

          <div class="lectern">
            <div class="book-stack"></div>
            <div class="chalk-box">
              <Mic :size="18" />
              <span>收音席</span>
            </div>
            <div class="camera-stand">
              <Camera :size="18" />
              <span>镜头席</span>
            </div>
          </div>
        </article>

        <aside class="rubric-panel">
          <div class="panel-title">
            <ClipboardCheck :size="19" />
            <h2>评分维度</h2>
          </div>

          <div class="score-ring" :style="{ '--score': '60%' }">
            <strong>60%</strong>
            <span>知识理解</span>
          </div>

          <div class="rubric-list">
            <div v-for="item in rubricItems" :key="item.name">
              <component :is="item.icon" :size="17" />
              <span>{{ item.name }}</span>
              <strong>{{ item.weight }}</strong>
            </div>
          </div>

          <div class="report-preview">
            <LineChart :size="18" />
            <span>课堂报告会汇总综合分、文字稿、知识漏洞和练习建议。</span>
          </div>
        </aside>
      </section>

      <section v-else class="teaching-layout">
        <article class="teaching-camera-panel">
          <div class="teaching-toolbar">
            <div>
              <span class="record-dot" :class="{ paused: lessonMode === 'finished' }"></span>
              <strong>{{ lessonMode === 'finished' ? '讲课已结束' : '讲课进行中' }}</strong>
            </div>
            <span class="recording-chip">
              <CircleDot :size="14" fill="currentColor" />
              {{ recorderStateText }}
            </span>
          </div>

          <div class="teaching-video-frame">
            <video ref="teachingVideoRef" autoplay muted playsinline></video>
            <div class="teaching-overlay">
              <span>{{ elapsedText }}</span>
              <strong>{{ normalizedTopic }}</strong>
            </div>
          </div>

          <canvas ref="snapshotCanvasRef" class="hidden-canvas"></canvas>

          <div class="teaching-controls">
            <button class="secondary-button" type="button" @click="lessonMode === 'finished' ? resetLesson() : captureLessonFrame()">
              <component :is="lessonMode === 'finished' ? RotateCcw : Camera" :size="17" />
              <span>{{ lessonMode === 'finished' ? '重新备课' : '截取一帧' }}</span>
            </button>
            <button class="end-button" type="button" :disabled="lessonMode === 'finished' || isFinishingLesson" @click="finishTeaching">
              <Square :size="17" fill="currentColor" />
              <span>{{ isFinishingLesson ? '正在结束' : '结束讲课' }}</span>
            </button>
          </div>
        </article>

        <aside class="teaching-status-panel">
          <div class="panel-title">
            <ClipboardCheck :size="19" />
            <h2>课堂状态</h2>
          </div>

          <div class="lesson-timer" :style="{ '--lesson-progress': `${lessonProgress}%` }">
            <strong>{{ remainingText }}</strong>
            <span>剩余时间</span>
          </div>

          <div class="teaching-metrics">
            <div>
              <strong>{{ elapsedText }}</strong>
              <span>已讲时间</span>
            </div>
            <div>
              <strong>{{ uploadedFrameCount }}/{{ capturedFrameCount }}</strong>
              <span>课堂帧</span>
            </div>
            <div>
              <strong>{{ pendingFrameCount }}</strong>
              <span>待上传</span>
            </div>
            <div>
              <strong>{{ recordedAudioSizeText }}</strong>
              <span>录音</span>
            </div>
          </div>

          <div class="backend-status" :class="{ warn: uploadError || finishError }">
            <CheckCircle2 :size="16" />
            <span>{{ backendStatusText }}</span>
          </div>

          <div class="mic-meter live-meter">
            <div>
              <AudioLines :size="18" />
              <span>{{ micReady ? '麦克风收音中' : '麦克风未连接' }}</span>
            </div>
            <div class="meter-track">
              <span :style="{ width: `${micLevel}%` }"></span>
            </div>
          </div>

          <div class="report-preview">
            <LineChart :size="18" />
            <span>{{ lessonMode === 'finished' ? reportSuggestionText : '讲课结束后，录音会用于语音转文字和知识理解评分。' }}</span>
          </div>

          <div v-if="lessonMode === 'finished'" class="report-result">
            <div>
              <span>报告状态</span>
              <strong>{{ reportStatusText }}</strong>
            </div>
            <div>
              <span>综合分</span>
              <strong>{{ finalScoreText }}</strong>
            </div>
            <div v-for="item in scoreBreakdown" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <button class="secondary-button" type="button" :disabled="reportStatus === 'loading'" @click="refreshReport">
              <RefreshCw :size="16" />
              <span>{{ reportStatus === 'loading' ? '刷新中' : '刷新报告' }}</span>
            </button>
          </div>

          <div v-if="lessonMode === 'finished'" class="report-details">
            <section class="report-section">
              <div class="report-section-title">
                <BookOpenCheck :size="16" />
                <strong>讲课文字稿</strong>
                <span>{{ asrStatusText }}</span>
              </div>
              <p class="transcript-text">{{ transcriptPreview }}</p>
            </section>

            <section v-for="section in reportSections" :key="section.title" class="report-section">
              <div class="report-section-title">
                <component :is="section.icon" :size="16" />
                <strong>{{ section.title }}</strong>
              </div>
              <ul>
                <li v-for="item in section.items" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="report-section">
              <div class="report-section-title">
                <Camera :size="16" />
                <strong>镜头状态</strong>
              </div>
              <p>{{ cameraSummaryText }}</p>
            </section>
          </div>
        </aside>

        <article class="teaching-board-panel">
          <div class="board compact-board">
            <div class="board-topline">
              <span>Lesson Notes</span>
              <Timer :size="18" />
            </div>
            <strong>{{ normalizedTopic }}</strong>
            <p>{{ boardHint }}</p>
          </div>
        </article>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  AudioLines,
  BookOpenCheck,
  Brain,
  Camera,
  CheckCircle2,
  CircleDot,
  ClipboardCheck,
  GraduationCap,
  LineChart,
  Mic,
  MessageSquareText,
  Play,
  RefreshCw,
  RotateCcw,
  Square,
  Timer,
  UserRoundCheck,
  VideoOff
} from 'lucide-vue-next'
import {
  finishMockClassroomSession,
  getMockClassroomReport,
  startMockClassroomSession,
  uploadMockClassroomAudio,
  uploadMockClassroomFrame
} from '../api/apis'

const durationOptions = [3, 5, 8, 10]
const FRAME_CAPTURE_INTERVAL_SECONDS = 2
const MAX_PENDING_FRAMES = 180

const topic = ref('')
const plannedMinutes = ref(5)
const referenceText = ref('')
const lessonMode = ref('setup')
const isStartingLesson = ref(false)
const isFinishingLesson = ref(false)
const selectedCameraId = ref('')
const selectedMicId = ref('')
const cameraDevices = ref([])
const micDevices = ref([])
const deviceVideoRef = ref(null)
const teachingVideoRef = ref(null)
const snapshotCanvasRef = ref(null)
const deviceStream = ref(null)
const isPreparingDevices = ref(false)
const cameraReady = ref(false)
const micReady = ref(false)
const deviceError = ref('')
const micLevel = ref(0)
const elapsedSeconds = ref(0)
const capturedFrameCount = ref(0)
const pendingFrames = ref([])
const uploadedFrameCount = ref(0)
const recordedAudioBlob = ref(null)
const recordingState = ref('idle')
const activeSessionId = ref('')
const frameUploadIntervalSeconds = ref(FRAME_CAPTURE_INTERVAL_SECONDS)
const isUploadingFrame = ref(false)
const uploadError = ref('')
const finishError = ref('')
const audioUploadStatus = ref('idle')
const reportStatus = ref('idle')
const reportData = ref(null)

let audioContext = null
let micAnalyser = null
let micSource = null
let micAnimationFrame = 0
let lessonClockTimer = null
let frameCaptureTimer = null
let reportPollTimer = null
let mediaRecorder = null
let recorderMimeType = ''
let recorderStopPromise = null
let resolveRecorderStop = null
let audioChunks = []

const normalizedTopic = computed(() => topic.value || '选择一个知识点，站上讲台讲清楚它')
const boardHint = computed(() => {
  return referenceText.value || '核心概念、推导步骤、例子和易错点都会成为讲解评分的参考。'
})
const devicesReady = computed(() => cameraReady.value && micReady.value)
const targetSeconds = computed(() => plannedMinutes.value * 60)
const remainingSeconds = computed(() => Math.max(0, targetSeconds.value - elapsedSeconds.value))
const elapsedText = computed(() => formatDuration(elapsedSeconds.value))
const remainingText = computed(() => formatDuration(remainingSeconds.value))
const lessonProgress = computed(() => {
  if (!targetSeconds.value) return 0
  return Math.min(100, Math.round((elapsedSeconds.value / targetSeconds.value) * 100))
})
const pendingFrameCount = computed(() => pendingFrames.value.length)
const sessionShortId = computed(() => {
  if (!activeSessionId.value) return '--'
  return activeSessionId.value.slice(-8)
})
const lessonStateText = computed(() => {
  if (lessonMode.value === 'teaching') return '讲课中'
  if (lessonMode.value === 'finished') return '已结束'
  return '备课中'
})
const lessonStateIcon = computed(() => {
  if (lessonMode.value === 'teaching') return CircleDot
  if (lessonMode.value === 'finished') return ClipboardCheck
  return GraduationCap
})
const deviceStateText = computed(() => {
  if (isPreparingDevices.value) return '检查中'
  if (devicesReady.value) return '设备就绪'
  return '等待授权'
})
const recorderStateText = computed(() => {
  if (audioUploadStatus.value === 'uploading') return '音频上传中'
  if (audioUploadStatus.value === 'stored') return '音频已上传'
  if (audioUploadStatus.value === 'error') return '音频上传失败'
  if (recordingState.value === 'recording') return '录音中'
  if (recordingState.value === 'ready') return '录音已保存'
  if (recordingState.value === 'error') return '录音异常'
  return '等待录音'
})
const recordedAudioSizeText = computed(() => {
  if (!recordedAudioBlob.value?.size) {
    return recordingState.value === 'recording' ? '录制中' : '--'
  }
  const kb = recordedAudioBlob.value.size / 1024
  if (kb < 1024) return `${Math.max(1, Math.round(kb))} KB`
  return `${(kb / 1024).toFixed(1)} MB`
})

const backendStatusText = computed(() => {
  if (finishError.value) return finishError.value
  if (uploadError.value) return uploadError.value
  if (isUploadingFrame.value) return '课堂画面上传中'
  if (activeSessionId.value) return `后端课堂记录已连接：${sessionShortId.value}`
  return '等待创建课堂记录'
})
const reportStatusText = computed(() => {
  const status = reportData.value?.status || reportStatus.value
  if (status === 'ready') return '报告已生成'
  if (status === 'generating') return '报告生成中'
  if (status === 'failed') return '报告生成失败'
  if (status === 'loading') return '查询中'
  if (status === 'pending') return '等待评分'
  return '未开始'
})
const finalScoreText = computed(() => {
  const score = Number(reportData.value?.overall_score || 0)
  return score > 0 ? String(score) : '--'
})
const reportSuggestionText = computed(() => {
  const suggestions = Array.isArray(reportData.value?.suggestions) ? reportData.value.suggestions : []
  return suggestions[0] || '讲课数据已经保存，报告生成后会在这里返回反馈。'
})
const scoreBreakdown = computed(() => [
  {
    label: '知识理解',
    value: Number(reportData.value?.knowledge_score || 0) || '--'
  },
  {
    label: '讲解熟练度',
    value: Number(reportData.value?.fluency_score || 0) || '--'
  },
  {
    label: '表达状态',
    value: Number(reportData.value?.presentation_score || 0) || '--'
  }
])
const transcriptPreview = computed(() => {
  const transcript = String(reportData.value?.transcript || '').trim()
  if (transcript) return transcript
  const status = reportData.value?.rubric?.asr?.status
  if (status === 'unconfigured') return '当前未配置 ASR，系统已经先根据讲课时长、参考要点和镜头状态生成降级报告。'
  if (status === 'failed') return reportData.value?.rubric?.asr?.message || '音频转写失败，暂时没有可展示的文字稿。'
  if (reportStatus.value === 'ready') return '这次报告没有拿到有效文字稿，可以检查麦克风、音频上传和 ASR 配置。'
  return '报告生成中，文字稿完成后会显示在这里。'
})
const asrStatusText = computed(() => {
  const status = reportData.value?.rubric?.asr?.status
  if (status === 'ready') return '已转写'
  if (status === 'unconfigured') return '未配置 ASR'
  if (status === 'failed') return '转写失败'
  if (status === 'missing_audio') return '缺少音频'
  if (reportStatus.value === 'ready') return '无文字稿'
  return '等待转写'
})
const cameraSummaryText = computed(() => {
  return reportData.value?.rubric?.vision_summary?.summary || '报告生成后会根据课堂帧汇总人像稳定、离开画面和多人入镜情况。'
})
const reportSections = computed(() => [
  {
    title: '讲得好的地方',
    icon: CheckCircle2,
    items: normalizeReportList(reportData.value?.strengths, '报告生成后会列出本次讲解中值得保留的做法。')
  },
  {
    title: '知识漏洞',
    icon: ClipboardCheck,
    items: normalizeReportList(reportData.value?.gaps, '暂时没有发现明确知识漏洞，建议结合文字稿再复盘一次。')
  },
  {
    title: '下次建议',
    icon: MessageSquareText,
    items: normalizeReportList(reportData.value?.suggestions, '下一次可以按“定义-推导-例子-易错点-总结”的顺序讲。')
  }
])

const normalizeReportList = (value, fallback) => {
  if (!Array.isArray(value)) return [fallback]
  const items = value.map(item => String(item || '').trim()).filter(Boolean)
  return items.length ? items : [fallback]
}

const rubricItems = [
  {
    name: '知识理解',
    weight: '60%',
    icon: Brain
  },
  {
    name: '讲解熟练度',
    weight: '25%',
    icon: MessageSquareText
  },
  {
    name: '表达状态',
    weight: '15%',
    icon: UserRoundCheck
  }
]

const formatDuration = seconds => {
  const safeSeconds = Math.max(0, Math.floor(Number(seconds) || 0))
  const minutes = Math.floor(safeSeconds / 60)
  const restSeconds = safeSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(restSeconds).padStart(2, '0')}`
}

const unwrapApiData = result => result?.data?.data ?? result?.data ?? result ?? {}

const errorMessage = (error, fallback) => {
  return error?.response?.data?.detail || error?.response?.data?.msg || error?.message || fallback
}

const getPreferredRecorderMimeType = () => {
  if (typeof MediaRecorder === 'undefined') return ''

  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus'
  ]
  return candidates.find(type => MediaRecorder.isTypeSupported(type)) || ''
}

const refreshMediaDevices = async () => {
  if (!navigator.mediaDevices?.enumerateDevices) return

  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameraDevices.value = devices.filter(device => device.kind === 'videoinput')
    micDevices.value = devices.filter(device => device.kind === 'audioinput')
  } catch (error) {
    console.warn('[MockClassroom] enumerate devices failed:', error)
  }
}

const prepareDevices = async () => {
  if (isPreparingDevices.value) return

  deviceError.value = ''
  isPreparingDevices.value = true
  stopDevicePreview()

  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('当前浏览器不支持摄像头或麦克风访问')
    }

    const videoConstraints = selectedCameraId.value
      ? {
          deviceId: { exact: selectedCameraId.value },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      : {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }

    const audioConstraints = selectedMicId.value
      ? { deviceId: { exact: selectedMicId.value } }
      : true

    const stream = await navigator.mediaDevices.getUserMedia({
      video: videoConstraints,
      audio: audioConstraints
    })

    deviceStream.value = stream
    cameraReady.value = stream.getVideoTracks().some(track => track.readyState === 'live')
    micReady.value = stream.getAudioTracks().some(track => track.readyState === 'live')

    await nextTick()
    if (deviceVideoRef.value) {
      deviceVideoRef.value.srcObject = stream
      await deviceVideoRef.value.play()
    }

    await refreshMediaDevices()
    startMicMeter(stream)
    attachStreamToVideos()
  } catch (error) {
    console.warn('[MockClassroom] prepare devices failed:', error)
    deviceError.value = error?.message || '设备检查失败，请确认浏览器权限和设备占用情况。'
    stopDevicePreview()
  } finally {
    isPreparingDevices.value = false
  }
}

const handleDeviceChange = () => {
  if (deviceStream.value) {
    prepareDevices()
  }
}

const attachStreamToVideos = async () => {
  await nextTick()
  const targets = [deviceVideoRef.value, teachingVideoRef.value].filter(Boolean)

  for (const video of targets) {
    if (video.srcObject !== deviceStream.value) {
      video.srcObject = deviceStream.value
    }
    if (deviceStream.value) {
      await video.play().catch(() => {})
    }
  }
}

const startTeaching = async () => {
  if (isStartingLesson.value) return

  deviceError.value = ''
  isStartingLesson.value = true

  try {
    if (!devicesReady.value) {
      await prepareDevices()
    }
    if (!devicesReady.value || !deviceStream.value) {
      throw new Error('请先完成摄像头和麦克风检查')
    }
    if (typeof MediaRecorder === 'undefined') {
      throw new Error('当前浏览器不支持录音')
    }

    resetLessonRuntime()
    const sessionData = unwrapApiData(await startMockClassroomSession({
      topic: normalizedTopic.value,
      reference_text: referenceText.value || null,
      planned_minutes: plannedMinutes.value
    }))
    activeSessionId.value = sessionData.session_id || ''
    if (!activeSessionId.value) {
      throw new Error('后端没有返回模拟课堂会话 ID')
    }
    frameUploadIntervalSeconds.value = Math.max(1, Number(sessionData.frame_upload_interval_seconds || FRAME_CAPTURE_INTERVAL_SECONDS))
    reportStatus.value = 'pending'

    lessonMode.value = 'teaching'
    await attachStreamToVideos()
    startLessonClock()
    startAudioRecording()
    startFrameCaptureLoop()
    await captureLessonFrame()
  } catch (error) {
    console.warn('[MockClassroom] start teaching failed:', error)
    deviceError.value = error?.message || '开始讲课失败，请检查设备权限。'
    lessonMode.value = 'setup'
    stopLessonRuntime()
  } finally {
    isStartingLesson.value = false
  }
}

const resetLessonRuntime = () => {
  stopLessonRuntime()
  stopReportPolling()
  elapsedSeconds.value = 0
  capturedFrameCount.value = 0
  pendingFrames.value = []
  uploadedFrameCount.value = 0
  recordedAudioBlob.value = null
  activeSessionId.value = ''
  frameUploadIntervalSeconds.value = FRAME_CAPTURE_INTERVAL_SECONDS
  isUploadingFrame.value = false
  uploadError.value = ''
  finishError.value = ''
  audioUploadStatus.value = 'idle'
  reportStatus.value = 'idle'
  reportData.value = null
  audioChunks = []
  recordingState.value = 'idle'
  isFinishingLesson.value = false
}

const startLessonClock = () => {
  window.clearInterval(lessonClockTimer)
  lessonClockTimer = window.setInterval(() => {
    if (lessonMode.value !== 'teaching') return

    elapsedSeconds.value += 1
    if (elapsedSeconds.value >= targetSeconds.value) {
      finishTeaching()
    }
  }, 1000)
}

const startAudioRecording = () => {
  const audioTracks = deviceStream.value?.getAudioTracks() || []
  if (!audioTracks.length) {
    throw new Error('没有可用的麦克风音轨')
  }

  const audioStream = new MediaStream(audioTracks)
  const mimeType = getPreferredRecorderMimeType()
  recorderMimeType = mimeType || 'audio/webm'
  mediaRecorder = new MediaRecorder(audioStream, mimeType ? { mimeType } : undefined)
  audioChunks = []
  recorderStopPromise = new Promise(resolve => {
    resolveRecorderStop = resolve
  })

  mediaRecorder.ondataavailable = event => {
    if (event.data?.size) {
      audioChunks.push(event.data)
    }
  }

  mediaRecorder.onstop = () => {
    recordedAudioBlob.value = new Blob(audioChunks, { type: recorderMimeType })
    recordingState.value = recordedAudioBlob.value.size ? 'ready' : 'error'
    resolveRecorderStop?.(recordedAudioBlob.value.size ? recordedAudioBlob.value : null)
    resolveRecorderStop = null
  }

  mediaRecorder.onerror = error => {
    console.warn('[MockClassroom] recorder error:', error)
    recordingState.value = 'error'
    resolveRecorderStop?.(null)
    resolveRecorderStop = null
  }

  mediaRecorder.start(1000)
  recordingState.value = 'recording'
}

const startFrameCaptureLoop = () => {
  window.clearInterval(frameCaptureTimer)
  frameCaptureTimer = window.setInterval(() => {
    captureLessonFrame()
  }, frameUploadIntervalSeconds.value * 1000)
}

const captureLessonFrame = async () => {
  if (lessonMode.value !== 'teaching') return false

  const video = teachingVideoRef.value || deviceVideoRef.value
  if (!video || !snapshotCanvasRef.value) return false
  if (!video.videoWidth || !video.videoHeight) return false

  const sourceWidth = video.videoWidth
  const sourceHeight = video.videoHeight
  const canvasWidth = 960
  const canvasHeight = Math.round((sourceHeight / sourceWidth) * canvasWidth)
  const canvas = snapshotCanvasRef.value
  const context = canvas.getContext('2d')
  if (!context) return false

  canvas.width = canvasWidth
  canvas.height = canvasHeight
  context.drawImage(video, 0, 0, canvasWidth, canvasHeight)
  context.fillStyle = 'rgba(42, 33, 20, 0.58)'
  context.fillRect(0, canvasHeight - 54, canvasWidth, 54)
  context.fillStyle = '#fff6df'
  context.font = '600 24px "Microsoft YaHei", sans-serif'
  context.fillText(`${normalizedTopic.value} · ${formatDuration(elapsedSeconds.value)}`, 24, canvasHeight - 20)

  const blob = await canvasToBlob(canvas)
  if (!blob) return false

  capturedFrameCount.value += 1
  queueFrameForUpload(blob)
  flushFrameQueue()
  return true
}

const canvasToBlob = canvas => new Promise(resolve => {
  canvas.toBlob(blob => resolve(blob), 'image/jpeg', 0.78)
})

const queueFrameForUpload = blob => {
  pendingFrames.value = [
    ...pendingFrames.value,
    {
      id: `${Date.now()}-${capturedFrameCount.value}`,
      blob,
      elapsed_seconds: Math.max(0, Math.floor(elapsedSeconds.value)),
      state: 'queued'
    }
  ].slice(-MAX_PENDING_FRAMES)
}

const flushFrameQueue = async ({ force = false } = {}) => {
  if (!activeSessionId.value || isUploadingFrame.value) return false
  if (!force && lessonMode.value !== 'teaching') return false

  isUploadingFrame.value = true
  try {
    while (activeSessionId.value && pendingFrames.value.length) {
      if (!force && lessonMode.value !== 'teaching') break

      const item = pendingFrames.value[0]
      const formData = new FormData()
      formData.append('frame', item.blob, `mock-classroom-${item.id}.jpg`)
      formData.append('client_elapsed_seconds', String(item.elapsed_seconds))

      const payload = unwrapApiData(await uploadMockClassroomFrame(activeSessionId.value, formData))
      const backendFrameCount = Number(payload?.metrics?.frame_count || 0)
      uploadedFrameCount.value = Math.max(uploadedFrameCount.value + 1, backendFrameCount)
      pendingFrames.value = pendingFrames.value.filter(frame => frame.id !== item.id)
      uploadError.value = ''
    }

    return true
  } catch (error) {
    console.warn('[MockClassroom] frame upload failed:', error)
    uploadError.value = errorMessage(error, '课堂画面上传失败，已保留待上传队列。')
    return false
  } finally {
    isUploadingFrame.value = false
  }
}

const waitForFrameQueueIdle = async () => {
  while (isUploadingFrame.value) {
    await new Promise(resolve => window.setTimeout(resolve, 100))
  }
}

const uploadLessonAudio = async audioBlob => {
  if (!activeSessionId.value || !audioBlob?.size) return null

  audioUploadStatus.value = 'uploading'
  const formData = new FormData()
  formData.append('audio', audioBlob, `mock-classroom-${Date.now()}${audioFileSuffix()}`)
  formData.append('client_elapsed_seconds', String(Math.max(0, Math.floor(elapsedSeconds.value))))

  try {
    const payload = unwrapApiData(await uploadMockClassroomAudio(activeSessionId.value, formData))
    audioUploadStatus.value = 'stored'
    return payload
  } catch (error) {
    console.warn('[MockClassroom] audio upload failed:', error)
    audioUploadStatus.value = 'error'
    finishError.value = errorMessage(error, '讲课音频上传失败，本次报告会暂时缺少语音数据。')
    return null
  }
}

const audioFileSuffix = () => {
  if (recorderMimeType.includes('mp4')) return '.mp4'
  if (recorderMimeType.includes('ogg')) return '.ogg'
  if (recorderMimeType.includes('wav')) return '.wav'
  return '.webm'
}

const applyFinishPayload = payload => {
  reportStatus.value = payload?.report_status || reportStatus.value || 'pending'
  const summary = payload?.summary || {}
  if (summary.frame_count !== undefined) {
    uploadedFrameCount.value = Math.max(uploadedFrameCount.value, Number(summary.frame_count) || 0)
  }
}

const refreshReport = async () => {
  if (!activeSessionId.value) return null

  reportStatus.value = 'loading'
  try {
    const payload = unwrapApiData(await getMockClassroomReport(activeSessionId.value))
    reportData.value = payload
    reportStatus.value = payload?.status || 'pending'
    if (isReportTerminal(reportStatus.value)) {
      stopReportPolling()
    }
    return payload
  } catch (error) {
    console.warn('[MockClassroom] report refresh failed:', error)
    reportStatus.value = 'failed'
    finishError.value = errorMessage(error, '报告查询失败，请稍后刷新。')
    stopReportPolling()
    return null
  }
}

const startReportPolling = () => {
  stopReportPolling()
  reportPollTimer = window.setInterval(() => {
    if (!activeSessionId.value || isReportTerminal(reportStatus.value)) {
      stopReportPolling()
      return
    }
    refreshReport()
  }, 3000)
}

const stopReportPolling = () => {
  window.clearInterval(reportPollTimer)
  reportPollTimer = null
}

const isReportTerminal = status => ['ready', 'failed'].includes(status)

const finishTeaching = async () => {
  if (isFinishingLesson.value || lessonMode.value !== 'teaching') return
  if (!activeSessionId.value) {
    finishError.value = '没有可结束的后端课堂记录，请重新开始。'
    return
  }

  isFinishingLesson.value = true
  try {
    await captureLessonFrame()
    stopLessonTimers()
    const audioBlob = await stopAudioRecording()
    await waitForFrameQueueIdle()
    await flushFrameQueue({ force: true })
    await uploadLessonAudio(audioBlob)
    const payload = unwrapApiData(await finishMockClassroomSession(activeSessionId.value, {
      client_elapsed_seconds: Math.max(0, Math.floor(elapsedSeconds.value))
    }))
    applyFinishPayload(payload)
    await refreshReport()
    if (!isReportTerminal(reportStatus.value)) {
      startReportPolling()
    }
    lessonMode.value = 'finished'
    stopDevicePreview()
  } catch (error) {
    console.warn('[MockClassroom] finish teaching failed:', error)
    finishError.value = errorMessage(error, '结束讲课失败，请稍后再试。')
  } finally {
    isFinishingLesson.value = false
  }
}

const stopLessonTimers = () => {
  window.clearInterval(lessonClockTimer)
  window.clearInterval(frameCaptureTimer)
  lessonClockTimer = null
  frameCaptureTimer = null
}

const stopAudioRecording = async () => {
  if (!mediaRecorder) return recordedAudioBlob.value

  const recorder = mediaRecorder
  if (recorder.state !== 'inactive') {
    recorder.stop()
  }

  const blob = recorderStopPromise ? await recorderStopPromise : recordedAudioBlob.value
  mediaRecorder = null
  recorderStopPromise = null
  resolveRecorderStop = null
  return blob
}

const stopLessonRuntime = () => {
  stopLessonTimers()
  stopAudioRecording().catch(error => {
    console.warn('[MockClassroom] stop audio failed:', error)
  })
}

const resetLesson = async () => {
  resetLessonRuntime()
  lessonMode.value = 'setup'
  await attachStreamToVideos()
}

const startMicMeter = stream => {
  stopMicMeter()

  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  const audioTracks = stream.getAudioTracks()
  if (!AudioContextClass || !audioTracks.length) return

  audioContext = new AudioContextClass()
  micAnalyser = audioContext.createAnalyser()
  micAnalyser.fftSize = 256
  micSource = audioContext.createMediaStreamSource(new MediaStream(audioTracks))
  micSource.connect(micAnalyser)

  const buffer = new Uint8Array(micAnalyser.frequencyBinCount)
  const tick = () => {
    if (!micAnalyser) return

    micAnalyser.getByteTimeDomainData(buffer)
    const sum = buffer.reduce((total, value) => {
      const normalized = (value - 128) / 128
      return total + normalized * normalized
    }, 0)
    const rms = Math.sqrt(sum / buffer.length)
    micLevel.value = Math.min(100, Math.round(rms * 260))
    micAnimationFrame = window.requestAnimationFrame(tick)
  }

  tick()
}

const stopMicMeter = () => {
  window.cancelAnimationFrame(micAnimationFrame)
  micAnimationFrame = 0
  micLevel.value = 0

  if (micSource) {
    try {
      micSource.disconnect()
    } catch {
      // Some browsers disconnect an already-closed audio graph automatically.
    }
  }

  micSource = null
  micAnalyser = null

  if (audioContext) {
    audioContext.close().catch(() => {})
    audioContext = null
  }
}

const stopDevicePreview = () => {
  stopMicMeter()

  if (deviceStream.value) {
    deviceStream.value.getTracks().forEach(track => track.stop())
  }
  deviceStream.value = null
  cameraReady.value = false
  micReady.value = false

  if (deviceVideoRef.value) {
    deviceVideoRef.value.srcObject = null
  }
  if (teachingVideoRef.value) {
    teachingVideoRef.value.srcObject = null
  }
}

onMounted(() => {
  refreshMediaDevices()
  navigator.mediaDevices?.addEventListener?.('devicechange', refreshMediaDevices)
})

onBeforeUnmount(() => {
  stopLessonRuntime()
  stopReportPolling()
  stopDevicePreview()
  navigator.mediaDevices?.removeEventListener?.('devicechange', refreshMediaDevices)
})
</script>

<style scoped>
.mock-classroom-page {
  position: relative;
  min-height: 100vh;
  padding: 28px clamp(18px, 3.5vw, 48px) 34px;
  color: #2e2418;
  overflow: hidden;
  isolation: isolate;
  font-family:
    Inter,
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
}

.classroom-scene {
  position: absolute;
  inset: 0;
  z-index: -2;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 244, 205, 0.94) 0%, rgba(240, 205, 130, 0.82) 56%, rgba(157, 93, 47, 0.62) 100%),
    #f4cf77;
}

.wall-light {
  position: absolute;
  left: 8vw;
  top: 2vh;
  width: min(48vw, 620px);
  height: min(44vh, 430px);
  background: radial-gradient(circle, rgba(255, 252, 226, 0.88), rgba(255, 238, 164, 0) 70%);
}

.chalk-board-bg {
  position: absolute;
  left: clamp(28px, 6vw, 92px);
  right: clamp(28px, 6vw, 92px);
  top: 78px;
  height: clamp(180px, 27vh, 270px);
  border: 13px solid rgba(96, 59, 30, 0.92);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.08), transparent 30%),
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.035) 0 1px, transparent 1px 6px),
    #284f42;
  box-shadow:
    0 26px 46px rgba(77, 47, 24, 0.22),
    inset 0 0 36px rgba(8, 42, 33, 0.32);
}

.chalk-board-bg span {
  position: absolute;
  left: 32px;
  height: 2px;
  border-radius: 999px;
  background: rgba(249, 244, 218, 0.58);
}

.chalk-board-bg span:nth-child(1) {
  top: 34%;
  width: 24%;
}

.chalk-board-bg span:nth-child(2) {
  top: 50%;
  width: 18%;
}

.chalk-board-bg span:nth-child(3) {
  top: 66%;
  width: 30%;
}

.floor-lines {
  position: absolute;
  left: -8vw;
  right: -8vw;
  bottom: 0;
  height: min(32vh, 270px);
  transform: skewY(-2deg);
  background:
    repeating-linear-gradient(92deg, rgba(255, 226, 156, 0.2) 0 2px, transparent 2px 22px),
    repeating-linear-gradient(0deg, rgba(75, 43, 23, 0.18) 0 1px, transparent 1px 30px),
    linear-gradient(180deg, #b96f3a, #8a4e2a 64%, #6e3b22);
}

.teacher-desk-bg {
  position: absolute;
  left: 12vw;
  right: 12vw;
  bottom: 9vh;
  height: 62px;
  border-radius: 8px 8px 0 0;
  background:
    repeating-linear-gradient(90deg, rgba(86, 48, 24, 0.18) 0 3px, transparent 3px 88px),
    linear-gradient(180deg, #c27b3e, #8c4d28);
  box-shadow: 0 20px 42px rgba(75, 43, 23, 0.2);
}

.mock-classroom-shell {
  position: relative;
  width: min(1360px, 100%);
  min-height: calc(100vh - 126px);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.classroom-header {
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

.classroom-header h1 {
  margin: 0;
  color: #2d1d10;
  font-size: clamp(28px, 3.4vw, 46px);
  font-weight: 950;
  line-height: 1.08;
}

.classroom-header p:last-child {
  max-width: 620px;
  margin: 9px 0 0;
  color: #76502e;
  font-size: 14px;
  line-height: 1.7;
  font-weight: 750;
}

.lesson-state {
  min-height: 42px;
  padding: 0 15px;
  border: 1px solid rgba(67, 43, 23, 0.18);
  border-radius: 999px;
  background: rgba(255, 247, 220, 0.8);
  color: #315f49;
  box-shadow: 0 12px 28px rgba(89, 49, 20, 0.12);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 900;
  white-space: nowrap;
}

.lesson-state.teaching {
  background: rgba(49, 95, 73, 0.92);
  color: #fff8df;
}

.lesson-state.finished {
  background: rgba(20, 55, 97, 0.92);
  color: #ffffff;
}

.classroom-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(340px, 0.42fr) minmax(480px, 1fr) minmax(300px, 0.36fr);
  gap: 18px;
}

.setup-panel,
.stage-panel,
.rubric-panel {
  border: 1px solid rgba(92, 57, 28, 0.22);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(255, 249, 226, 0.95), rgba(255, 238, 185, 0.86)),
    rgba(255, 246, 215, 0.92);
  box-shadow:
    0 18px 42px rgba(95, 55, 22, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(130%);
  -webkit-backdrop-filter: blur(14px) saturate(130%);
}

.setup-panel,
.rubric-panel {
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
.form-field textarea {
  width: 100%;
  border: 1px solid rgba(92, 57, 28, 0.22);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.86);
  color: #3b2a16;
  padding: 0 12px;
  font: inherit;
  outline: none;
}

.form-field input {
  height: 42px;
}

.form-field select {
  height: 42px;
}

.form-field textarea {
  min-height: 150px;
  padding-top: 12px;
  resize: vertical;
  line-height: 1.6;
}

.form-field input:focus,
.form-field select:focus,
.form-field textarea:focus {
  border-color: #315f49;
  box-shadow: 0 0 0 3px rgba(49, 95, 73, 0.14);
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.device-error {
  margin: 0;
  padding: 11px 12px;
  border: 1px solid rgba(165, 56, 38, 0.3);
  border-radius: 8px;
  background: rgba(255, 231, 219, 0.8);
  color: #8f2f23;
  font-size: 13px;
  line-height: 1.5;
}

.setup-actions {
  margin-top: auto;
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr);
  gap: 10px;
}

.duration-options {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.duration-options button,
.secondary-button,
.end-button,
.start-button {
  border: 0;
  border-radius: 8px;
  font: inherit;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.duration-options button {
  min-height: 40px;
  border: 1px solid rgba(92, 57, 28, 0.2);
  background: rgba(255, 253, 242, 0.72);
  color: #6f4725;
  font-size: 13px;
}

.duration-options button:hover,
.duration-options button.active {
  border-color: #315f49;
  background: #315f49;
  color: #fff8df;
  transform: translateY(-1px);
}

.secondary-button {
  min-height: 48px;
  border: 1px solid rgba(92, 57, 28, 0.2);
  background: rgba(255, 253, 242, 0.76);
  color: #5f3c20;
  box-shadow: none;
}

.start-button {
  min-height: 48px;
  background: #9a4f21;
  color: #fff8df;
  box-shadow: 0 12px 24px rgba(154, 79, 33, 0.22);
}

.start-button:hover:not(:disabled),
.secondary-button:hover:not(:disabled),
.end-button:hover:not(:disabled) {
  transform: translateY(-2px);
}

.start-button:disabled,
.secondary-button:disabled,
.end-button:disabled {
  opacity: 0.7;
  cursor: wait;
}

.end-button {
  min-height: 48px;
  background: #9f2a22;
  color: #fff6df;
  box-shadow: 0 12px 22px rgba(159, 42, 34, 0.18);
}

.stage-panel {
  position: relative;
  overflow: hidden;
  min-height: 560px;
  padding: 24px;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto auto;
  gap: 18px;
  background:
    linear-gradient(180deg, rgba(255, 245, 203, 0.8), rgba(247, 203, 111, 0.48)),
    #f1c861;
}

.device-preview {
  display: grid;
  grid-template-columns: minmax(240px, 0.8fr) minmax(200px, 0.55fr);
  gap: 12px;
}

.preview-video,
.mic-meter {
  border: 1px solid rgba(70, 39, 20, 0.18);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.7);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

.preview-video {
  position: relative;
  min-height: 150px;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(49, 95, 73, 0.55), rgba(43, 28, 15, 0.6)),
    #315f49;
}

.preview-video video {
  width: 100%;
  height: 100%;
  min-height: 150px;
  object-fit: cover;
  display: block;
  background: #20160e;
}

.preview-placeholder {
  position: absolute;
  inset: 0;
  color: #fff8df;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  background:
    linear-gradient(135deg, rgba(49, 95, 73, 0.78), rgba(43, 28, 15, 0.68)),
    #315f49;
}

.preview-placeholder strong {
  font-size: 14px;
}

.preview-chip {
  position: absolute;
  left: 10px;
  top: 10px;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(42, 28, 14, 0.72);
  color: #fff8df;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 900;
}

.device-preview.ready .preview-chip {
  background: rgba(49, 95, 73, 0.86);
}

.mic-meter {
  min-height: 150px;
  padding: 16px;
  color: #5f3c20;
  display: grid;
  align-content: center;
  gap: 16px;
}

.mic-meter > div:first-child {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 900;
}

.meter-track {
  height: 14px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(95, 60, 32, 0.16);
  box-shadow: inset 0 1px 2px rgba(70, 39, 20, 0.15);
}

.meter-track span {
  height: 100%;
  min-width: 3px;
  border-radius: inherit;
  background: linear-gradient(90deg, #315f49, #e4b747);
  display: block;
  transition: width 0.08s linear;
}

.board {
  min-height: 360px;
  border: 12px solid #6b4227;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.08), transparent 32%),
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.042) 0 1px, transparent 1px 6px),
    #315f49;
  color: #fff8df;
  padding: clamp(18px, 3vw, 34px);
  display: grid;
  align-content: start;
  gap: 18px;
  box-shadow:
    0 24px 38px rgba(80, 46, 22, 0.2),
    inset 0 0 40px rgba(11, 45, 32, 0.28);
}

.board-topline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: rgba(255, 248, 223, 0.76);
  font-size: 13px;
  font-weight: 900;
}

.board strong {
  max-width: 760px;
  color: #fff8df;
  font-size: clamp(28px, 4vw, 56px);
  line-height: 1.14;
  font-weight: 950;
}

.board p {
  max-width: 680px;
  margin: 0;
  color: rgba(255, 248, 223, 0.78);
  font-size: 15px;
  line-height: 1.75;
  font-weight: 700;
}

.chalk-lines {
  margin-top: 8px;
  display: grid;
  gap: 12px;
}

.chalk-lines span {
  height: 3px;
  border-radius: 999px;
  background: rgba(255, 248, 223, 0.58);
}

.chalk-lines span:nth-child(1) {
  width: 70%;
}

.chalk-lines span:nth-child(2) {
  width: 48%;
}

.chalk-lines span:nth-child(3) {
  width: 58%;
}

.lectern {
  min-height: 116px;
  border-radius: 8px;
  background:
    repeating-linear-gradient(100deg, rgba(255, 226, 158, 0.2) 0 2px, transparent 2px 18px),
    linear-gradient(180deg, #bd7238, #8d4e29);
  box-shadow: inset 0 14px 24px rgba(255, 241, 190, 0.2);
  display: grid;
  grid-template-columns: minmax(150px, 1fr) repeat(2, minmax(110px, 0.45fr));
  gap: 12px;
  align-items: end;
  padding: 18px;
}

.book-stack,
.chalk-box,
.camera-stand {
  border-radius: 8px;
  border: 1px solid rgba(70, 39, 20, 0.18);
}

.book-stack {
  height: 58px;
  background:
    linear-gradient(180deg, transparent 0 12px, #f7e2a3 12px 22px, transparent 22px),
    linear-gradient(180deg, transparent 24px, #315f49 24px 38px, transparent 38px),
    linear-gradient(180deg, transparent 40px, #9a4f21 40px 54px, transparent 54px);
}

.chalk-box,
.camera-stand {
  min-height: 62px;
  background: rgba(255, 253, 242, 0.72);
  color: #5f3c20;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 900;
}

.score-ring {
  --score: 60%;
  width: min(180px, 100%);
  aspect-ratio: 1;
  margin: 0 auto;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, rgba(255, 248, 226, 0.98) 0 56%, transparent 57%),
    conic-gradient(#315f49 var(--score), rgba(95, 60, 32, 0.16) 0);
  display: grid;
  place-items: center;
  align-content: center;
  gap: 4px;
}

.score-ring strong {
  color: #315f49;
  font-size: 42px;
  line-height: 1;
}

.score-ring span {
  color: #76502e;
  font-size: 13px;
  font-weight: 900;
}

.rubric-list {
  display: grid;
  gap: 10px;
}

.rubric-list div,
.report-preview {
  min-height: 48px;
  padding: 10px 12px;
  border: 1px solid rgba(92, 57, 28, 0.16);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.6);
  color: #5f3c20;
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13px;
  font-weight: 900;
}

.rubric-list span {
  flex: 1;
  min-width: 0;
}

.rubric-list strong {
  color: #315f49;
}

.report-preview {
  align-items: flex-start;
  margin-top: auto;
  color: #315f49;
  background: rgba(245, 250, 225, 0.74);
  line-height: 1.55;
}

.report-preview svg {
  flex-shrink: 0;
  margin-top: 1px;
}

.teaching-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(520px, 1fr) minmax(310px, 0.35fr);
  grid-template-rows: minmax(430px, 1fr) minmax(190px, 0.42fr);
  grid-template-areas:
    "camera status"
    "camera board";
  gap: 18px;
}

.teaching-camera-panel,
.teaching-status-panel,
.teaching-board-panel {
  border: 1px solid rgba(92, 57, 28, 0.22);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(255, 249, 226, 0.95), rgba(255, 238, 185, 0.86)),
    rgba(255, 246, 215, 0.92);
  box-shadow:
    0 18px 42px rgba(95, 55, 22, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(130%);
  -webkit-backdrop-filter: blur(14px) saturate(130%);
}

.teaching-camera-panel {
  grid-area: camera;
  min-height: 0;
  padding: 16px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 12px;
}

.teaching-toolbar {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.teaching-toolbar > div,
.recording-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #2d1d10;
  font-size: 13px;
  font-weight: 900;
}

.record-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #2f8f59;
  box-shadow: 0 0 0 6px rgba(47, 143, 89, 0.16);
}

.record-dot.paused {
  background: #143761;
  box-shadow: 0 0 0 6px rgba(20, 55, 97, 0.14);
}

.recording-chip {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(159, 42, 34, 0.1);
  color: #9f2a22;
}

.teaching-video-frame {
  position: relative;
  min-height: 360px;
  border: 10px solid #6b4227;
  border-radius: 8px;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(39, 26, 14, 0.42), transparent),
    #24180f;
}

.teaching-video-frame video {
  width: 100%;
  height: 100%;
  min-height: 100%;
  object-fit: cover;
  display: block;
  background: #20160e;
}

.teaching-overlay {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 16px;
  min-height: 52px;
  padding: 9px 13px;
  border-radius: 8px;
  background: rgba(42, 28, 14, 0.72);
  color: #fff8df;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  display: flex;
  align-items: center;
  gap: 12px;
}

.teaching-overlay span {
  font-size: 22px;
  font-weight: 950;
  white-space: nowrap;
}

.teaching-overlay strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 900;
}

.hidden-canvas {
  display: none;
}

.teaching-controls {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr);
  gap: 10px;
}

.teaching-status-panel {
  grid-area: status;
  padding: 18px;
  display: grid;
  align-content: start;
  gap: 16px;
  overflow: auto;
}

.lesson-timer {
  --lesson-progress: 0%;
  width: min(190px, 100%);
  aspect-ratio: 1;
  margin: 0 auto;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, rgba(255, 248, 226, 0.98) 0 56%, transparent 57%),
    conic-gradient(#9a4f21 var(--lesson-progress), rgba(95, 60, 32, 0.16) 0);
  display: grid;
  place-items: center;
  align-content: center;
  gap: 5px;
}

.lesson-timer strong {
  color: #9a4f21;
  font-size: 40px;
  line-height: 1;
}

.lesson-timer span {
  color: #76502e;
  font-size: 13px;
  font-weight: 900;
}

.teaching-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.teaching-metrics div {
  min-height: 72px;
  padding: 10px;
  border: 1px solid rgba(92, 57, 28, 0.16);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.58);
  display: grid;
  place-items: center;
  text-align: center;
}

.teaching-metrics strong {
  color: #2d1d10;
  font-size: 20px;
}

.teaching-metrics span {
  color: #76502e;
  font-size: 12px;
  font-weight: 900;
}

.backend-status {
  min-height: 44px;
  padding: 9px 12px;
  border: 1px solid rgba(49, 95, 73, 0.18);
  border-radius: 8px;
  background: rgba(245, 250, 225, 0.74);
  color: #315f49;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 900;
  line-height: 1.45;
}

.backend-status.warn {
  border-color: rgba(159, 42, 34, 0.22);
  background: rgba(255, 235, 219, 0.72);
  color: #9f2a22;
}

.backend-status svg {
  flex-shrink: 0;
}

.live-meter {
  min-height: 102px;
}

.report-result {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.report-result > div {
  min-height: 68px;
  padding: 10px;
  border: 1px solid rgba(92, 57, 28, 0.16);
  border-radius: 8px;
  background: rgba(255, 253, 242, 0.6);
  display: grid;
  place-items: center;
  text-align: center;
}

.report-result span {
  color: #76502e;
  font-size: 12px;
  font-weight: 900;
}

.report-result strong {
  color: #315f49;
  font-size: 19px;
}

.report-result button {
  grid-column: 1 / -1;
  min-height: 42px;
}

.report-details {
  display: grid;
  gap: 12px;
}

.report-section {
  padding-top: 12px;
  border-top: 1px solid rgba(92, 57, 28, 0.16);
  color: #4e321d;
}

.report-section-title {
  min-height: 24px;
  display: flex;
  align-items: center;
  gap: 7px;
  color: #315f49;
  font-size: 13px;
  font-weight: 950;
}

.report-section-title span {
  margin-left: auto;
  color: #9a4f21;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.report-section p,
.report-section ul {
  margin: 8px 0 0;
  color: #76502e;
  font-size: 13px;
  line-height: 1.65;
  font-weight: 760;
}

.report-section ul {
  padding-left: 17px;
}

.report-section li + li {
  margin-top: 5px;
}

.transcript-text {
  max-height: 138px;
  overflow: auto;
}

.teaching-board-panel {
  grid-area: board;
  min-height: 0;
  padding: 14px;
}

.compact-board {
  min-height: 100%;
  border-width: 8px;
  padding: 18px;
  gap: 11px;
}

.compact-board strong {
  font-size: clamp(20px, 2.4vw, 30px);
}

.compact-board p {
  font-size: 13px;
}

@media (max-width: 1180px) {
  .classroom-grid {
    grid-template-columns: minmax(340px, 0.5fr) minmax(520px, 1fr);
  }

  .rubric-panel {
    grid-column: 1 / -1;
  }

  .teaching-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    grid-template-areas: none;
  }

  .teaching-camera-panel,
  .teaching-status-panel,
  .teaching-board-panel {
    grid-area: auto;
  }
}

@media (max-width: 820px) {
  .mock-classroom-page {
    min-height: 100vh;
    padding: 20px 14px 26px;
    overflow-y: auto;
  }

  .mock-classroom-shell {
    min-height: 0;
  }

  .classroom-header {
    flex-direction: column;
  }

  .lesson-state {
    align-self: flex-start;
  }

  .classroom-grid {
    grid-template-columns: 1fr;
  }

  .stage-panel {
    min-height: 460px;
  }

  .board {
    min-height: 300px;
    border-width: 8px;
  }

  .duration-options,
  .device-grid,
  .setup-actions,
  .device-preview,
  .teaching-controls,
  .teaching-metrics,
  .lectern {
    grid-template-columns: 1fr;
  }

  .teaching-video-frame {
    min-height: 260px;
    border-width: 7px;
  }

  .teaching-overlay {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
