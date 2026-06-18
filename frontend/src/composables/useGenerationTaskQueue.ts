import { reactive } from 'vue'
import {
  createResourceGenerationTask,
  generatePresentation,
  getPresentationQuestions,
  getResourceGenerationTask,
  getResourceGenerationTasks,
  streamResourceGenerationTask,
} from '../api/apis'
import { executeGeneration, type ResourceToolConfig } from './useResourceGeneration'

export type GenerationTaskStatus = 'running' | 'done' | 'failed'

export interface GenerationTask {
  id: string
  backendTaskId: string
  text: string
  tool: ResourceToolConfig
  chatGroupId: number | string | null
  status: GenerationTaskStatus
  progress: string
  thinkingProcess: string
  error: string
  files: unknown[]
  images: unknown[]
  doneEvent: unknown
  createdAt: number
  updatedAt: number
}

const tasks = reactive<GenerationTask[]>([])
const pollingTaskIds = new Set<string>()
const streamingTaskIds = new Set<string>()
const GENERATION_TASKS_STORAGE_KEY = 'zhiban_generation_tasks_v2'
let hasHydratedTasks = false
let hydratePromise: Promise<GenerationTask[]> | null = null

const isViewingGenerationPage = () => {
  if (typeof window === 'undefined' || typeof document === 'undefined') return false
  const route = window.location.hash || window.location.pathname || ''
  return !document.hidden && route.includes('/chat')
}

const dispatchNotificationUpdateIfAway = () => {
  if (!isViewingGenerationPage()) {
    window.dispatchEvent(new CustomEvent('zhiban:notification-update'))
  }
}

const persistTasks = () => {
  try {
    window.localStorage.setItem(
      GENERATION_TASKS_STORAGE_KEY,
      JSON.stringify(tasks.slice(0, 30).map(task => ({
        id: task.id,
        backendTaskId: task.backendTaskId,
        text: task.text,
        tool: task.tool,
        chatGroupId: task.chatGroupId,
        status: task.status,
        progress: task.progress,
        thinkingProcess: task.thinkingProcess,
        error: task.error,
        files: task.files,
        images: task.images,
        doneEvent: task.doneEvent,
        createdAt: task.createdAt,
        updatedAt: task.updatedAt,
      }))),
    )
  } catch {
    // localStorage may be unavailable in private browsing or during SSR-like tests.
  }
}

const restorePersistedTasks = () => {
  try {
    const raw = window.localStorage.getItem(GENERATION_TASKS_STORAGE_KEY)
    const list = raw ? JSON.parse(raw) : []
    if (!Array.isArray(list)) return

    list.forEach(item => {
      if (!item?.id || tasks.some(task => task.id === item.id)) return
      const isRecent = Date.now() - Number(item.updatedAt || 0) < 60 * 60 * 1000
      if (item.status !== 'running' && !isRecent) return
      // 超过 30 分钟的 running 任务视为已失效，不再恢复轮询
      const stale = Date.now() - Number(item.createdAt || 0) > 30 * 60 * 1000
      if (item.status === 'running' && stale) return
      tasks.push(reactive({
        id: item.id,
        backendTaskId: item.backendTaskId || '',
        text: item.text || '',
        tool: item.tool || { label: 'resource', generateMode: 'resource', resourceTypes: ['document'] },
        chatGroupId: item.chatGroupId ?? null,
        status: item.status || 'running',
        progress: item.progress || '正在生成资源...',
        thinkingProcess: item.thinkingProcess || '',
        error: item.error || '',
        files: Array.isArray(item.files) ? item.files : [],
        images: Array.isArray(item.images) ? item.images : [],
        doneEvent: item.doneEvent || null,
        createdAt: Number(item.createdAt || Date.now()),
        updatedAt: Number(item.updatedAt || Date.now()),
      }) as GenerationTask)
    })
  } catch {
    // Ignore malformed cache.
  }
}

restorePersistedTasks()

const unwrapResponseData = (result: any) => result?.data?.data ?? result?.data ?? result

const makeLocalTaskId = (taskId = '') => taskId ? `generation-${taskId}` : `generation-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const toFrontendStatus = (status: string): GenerationTaskStatus => {
  if (status === 'success' || status === 'done') return 'done'
  if (status === 'failed') return 'failed'
  return 'running'
}

const formatTaskProgress = (taskData: any) => {
  const message = taskData?.progress_msg || taskData?.progressMsg || ''
  const progress = Number(taskData?.progress || 0)
  if (message && progress) return `${message} ${progress}%`
  if (message) return message
  if (progress) return `正在生成资源 ${progress}%...`
  return '正在生成资源...'
}

const formatTaskThinking = (value: any) => {
  const raw = Array.isArray(value)
    ? value.join('\n')
    : String(value || '')
  return raw
    .replace(/!\[[^\]]*\]\([^)]+\)/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

const getBackendThinking = (taskData: any) => formatTaskThinking(
  taskData?.progress_msg ||
  taskData?.progressMsg ||
  taskData?.message ||
  taskData?.msg
)

const normalizeTaskFiles = (taskData: any) => {
  const result = taskData?.result || taskData?.resources || []
  return (Array.isArray(result) ? result : []).map((item: any) => ({
    ...item,
    file_id: item.file_id || item.fileId || item.resource_id || item.resourceId,
    resource_id: item.resource_id || item.resourceId || item.file_id || item.fileId,
    file_type: item.file_type || item.fileType || item.resource_type || item.resourceType,
    resource_type: item.resource_type || item.resourceType || item.file_type || item.fileType,
    filename: item.filename || `${item.topic || '生成资源'}_${item.file_type || item.resource_type || 'resource'}`,
    download_url: item.download_url || item.downloadUrl || (item.resource_id ? `/resource/${item.resource_id}/download` : ''),
  }))
}

const applyBackendTaskData = (task: GenerationTask, taskData: any) => {
  const prevStatus = task.status
  task.backendTaskId = taskData?.task_id || taskData?.taskId || task.backendTaskId
  task.chatGroupId = taskData?.chat_group_id || taskData?.chatGroupId || task.chatGroupId
  task.status = toFrontendStatus(String(taskData?.status || 'running'))
  task.progress = task.status === 'failed'
    ? (taskData?.error || '资源生成失败，请稍后再试。')
    : formatTaskProgress(taskData)
  const thinking = getBackendThinking(taskData)
  if (thinking) task.thinkingProcess = thinking
  task.error = taskData?.error || ''
  // 保留已生成的课件文件和 doneEvent.presentation，
  // 避免 hydrate 时后端数据覆盖前端已完成的课件状态导致重复生成
  const existingPresentation = (task.doneEvent as any)?.presentation
  const existingVideoFiles = task.files.filter(
    f => (f as any).file_type === 'video' || (f as any).resource_type === 'video' || (f as any).resourceKind === 'presentation'
  )
  task.files.splice(0, task.files.length, ...normalizeTaskFiles(taskData))
  // 把课件文件追加回去（放在资源文件后面）
  if (existingVideoFiles.length) {
    task.files.push(...existingVideoFiles)
  }
  task.doneEvent = {
    chat_group_id: task.chatGroupId,
    resources: task.files,
  }
  if (existingPresentation) {
    (task.doneEvent as any).presentation = existingPresentation
  }
  task.updatedAt = Date.now()
  persistTasks()

  // 任务完成/失败时通知 TopNav 刷新铃铛（模块级，不受组件卸载影响）
  if (prevStatus === 'running' && task.status !== 'running') {
    console.log('[GenerationTask] 任务状态变更，发送通知刷新事件', { taskId: task.backendTaskId, prevStatus, newStatus: task.status })
    dispatchNotificationUpdateIfAway()
  }
}

const upsertBackendTask = (taskData: any, tool?: ResourceToolConfig) => {
  const backendTaskId = taskData?.task_id || taskData?.taskId || ''
  if (!backendTaskId) return null

  let task = tasks.find(item => item.backendTaskId === backendTaskId)
  if (!task) {
    task = reactive({
      id: makeLocalTaskId(backendTaskId),
      backendTaskId,
      text: taskData?.topic || '',
      tool: tool || {
        label: 'resource',
        generateMode: 'resource',
        resourceTypes: taskData?.resource_types || taskData?.resourceTypes || ['document'],
      },
      chatGroupId: taskData?.chat_group_id || taskData?.chatGroupId || null,
      status: 'running',
      progress: '正在生成资源...',
      thinkingProcess: getBackendThinking(taskData),
      error: '',
      files: [],
      images: [],
      doneEvent: null,
      createdAt: taskData?.created_at ? new Date(taskData.created_at).getTime() || Date.now() : Date.now(),
      updatedAt: Date.now(),
    }) as GenerationTask
    tasks.unshift(task)
  }

  applyBackendTaskData(task, taskData)
  return task
}

const pollBackendTask = (task: GenerationTask) => {
  if (!task.backendTaskId || pollingTaskIds.has(task.backendTaskId)) return
  pollingTaskIds.add(task.backendTaskId)

  const tick = async () => {
    try {
      const result = await getResourceGenerationTask(task.backendTaskId)
      const data = unwrapResponseData(result)
      applyBackendTaskData(task, data)
      if (task.status === 'running') {
        window.setTimeout(tick, 1800)
      } else {
        pollingTaskIds.delete(task.backendTaskId)
      }
    } catch (error: any) {
      task.status = 'failed'
      task.error = error?.response?.data?.detail || error?.message || '任务状态同步失败'
      task.progress = task.error
      task.updatedAt = Date.now()
      pollingTaskIds.delete(task.backendTaskId)
    }
  }

  window.setTimeout(tick, 800)
}

const applyTaskStreamEvent = (task: GenerationTask, eventData: any) => {
  if (!eventData || eventData.type === '__close__') return

  if (eventData.type === 'stream_start') {
    ;(task as any)._pptStream = { slides: [] }
  }

  if (eventData.type === 'stream_section_replace' && eventData.section_idx != null) {
    const stream = (task as any)._pptStream || { slides: [] }
    stream.slides = stream.slides.filter((s: any) => {
      const si = typeof s === 'object' ? s.section_idx : null
      return si !== eventData.section_idx
    })
    stream._needsRebuild = true
    ;(task as any)._pptStream = stream
  }

  if (eventData.type === 'stream_slide' && eventData.content) {
    const stream = (task as any)._pptStream || { slides: [] }
    stream.slides.push({ content: eventData.content, section_idx: eventData.section_idx })
    ;(task as any)._pptStream = stream
    console.log('[GenerationTask] stream_slide taskId=%s section_idx=%s slides=%d',
      task.backendTaskId?.slice(0, 12) || task.id, eventData.section_idx, stream.slides.length)
  }

  const thinking = getBackendThinking(eventData)
  if (thinking) task.thinkingProcess = thinking

  if (eventData.progress_msg || eventData.progressMsg || eventData.progress || eventData.status) {
    task.progress = formatTaskProgress(eventData)
    task.status = toFrontendStatus(String(eventData.status || task.status || 'running'))
  }

  if (eventData.error) {
    task.error = eventData.error
    task.status = 'failed'
    task.progress = eventData.error
  }

  if (eventData.result || eventData.resources) {
    task.files.splice(0, task.files.length, ...normalizeTaskFiles(eventData))
  }

  if (eventData.type === 'done' || eventData.done) {
    task.status = toFrontendStatus(String(eventData.status || 'done'))
    task.doneEvent = {
      chat_group_id: task.chatGroupId,
      resources: task.files,
      ...eventData,
    }
  }

  task.updatedAt = Date.now()
  persistTasks()
}

const streamBackendTask = (task: GenerationTask) => {
  if (!task.backendTaskId || streamingTaskIds.has(task.backendTaskId)) return
  streamingTaskIds.add(task.backendTaskId)

  void streamResourceGenerationTask(task.backendTaskId, {
    onEvent: eventData => {
      applyTaskStreamEvent(task, eventData)
    },
    onDone: async () => {
      try {
        const result = await getResourceGenerationTask(task.backendTaskId)
        applyBackendTaskData(task, unwrapResponseData(result))
      } finally {
        streamingTaskIds.delete(task.backendTaskId)
      }
    },
    onError: error => {
      task.error = error || task.error
      task.updatedAt = Date.now()
      persistTasks()
    }
  }).catch(() => {
    streamingTaskIds.delete(task.backendTaskId)
    pollBackendTask(task)
  })
}

const runLegacyFrontendTask = (task: GenerationTask) => {
  void executeGeneration(task.text, task.tool, task.chatGroupId, {
    onSubmitted: data => {
      const submitData: any = data || {}
      task.backendTaskId = submitData?.task_id || submitData?.taskId || submitData?.id || task.backendTaskId
      task.chatGroupId = submitData?.chat_group_id || submitData?.chatGroupId || task.chatGroupId
      const thinking = getBackendThinking(submitData)
      if (thinking) task.thinkingProcess = thinking
      task.updatedAt = Date.now()
      persistTasks()
    },
    onProgress: msg => {
      task.progress = msg
      task.thinkingProcess = formatTaskThinking(msg) || task.thinkingProcess
      task.updatedAt = Date.now()
      persistTasks()
    },
    onThinking: msg => {
      task.thinkingProcess = formatTaskThinking(msg) || task.thinkingProcess
      task.updatedAt = Date.now()
      persistTasks()
    },
    onFile: fileData => {
      task.files.push(fileData)
      task.updatedAt = Date.now()
      persistTasks()
    },
    onImage: imageData => {
      task.images.push(imageData)
      task.updatedAt = Date.now()
      persistTasks()
    },
    onStreamStart: (eventData: any) => {
      ;(task as any)._pptStream = { slides: [] }
      task.updatedAt = Date.now()
    },
    onStreamSlide: (eventData: any) => {
      const stream = (task as any)._pptStream
      if (stream && eventData?.content) {
        stream.slides.push(eventData.content)
        task.updatedAt = Date.now()
      }
    },
    onDone: eventData => {
      task.doneEvent = eventData || null
      task.chatGroupId = (eventData as any)?.chat_group_id || (eventData as any)?.chatGroupId || task.chatGroupId
      task.status = 'done'
      task.progress = task.progress || '资源已生成'
      task.updatedAt = Date.now()
      persistTasks()
      console.log('[GenerationTask] legacy 任务完成，发送通知刷新事件', { taskId: task.backendTaskId })
      dispatchNotificationUpdateIfAway()
    },
    onError: err => {
      task.error = err || '资源生成失败，请稍后再试。'
      task.status = 'failed'
      task.progress = task.error
      task.updatedAt = Date.now()
      persistTasks()
      console.log('[GenerationTask] legacy 任务失败，发送通知刷新事件', { taskId: task.backendTaskId })
      dispatchNotificationUpdateIfAway()
    },
  }).catch(error => {
    task.error = error?.message || '资源生成失败，请稍后再试。'
    task.status = 'failed'
    task.progress = task.error
    task.updatedAt = Date.now()
    persistTasks()
    console.log('[GenerationTask] legacy 任务异常，发送通知刷新事件', { taskId: task.backendTaskId })
    dispatchNotificationUpdateIfAway()
  })
}

const maybeGeneratePresentation = async (task: GenerationTask) => {
  if (task.tool.generateMode !== 'video' || task.status !== 'done') return
  if ((task.doneEvent as any)?.presentation || !task.files.length) return
  // 防止重复进入（watcher 可能在 files.push 时再次触发）
  if ((task as any)._presentationGenerating) return
  ;(task as any)._presentationGenerating = true

  try {
    // 新流程：追问前置已回答 → 直接生成课件，资源已按答案精准生成
    if ((task as any).questionsShown && (task as any)._answers) {
      task.status = 'running'
      task.progress = '正在生成动态课件...'
      task.updatedAt = Date.now()
      persistTasks()
      try {
        await _doGeneratePresentation(task)
      } catch (e: any) {
        task.status = 'failed'
        task.error = e?.response?.data?.detail || e?.message || '动态课件生成失败'
        task.progress = task.error
      } finally {
        task.updatedAt = Date.now()
        persistTasks()
      }
      return
    }

    // 旧流程兼容：等待用户作答或无追问
    if ((task as any).pendingQuestions || (task as any).questionsShown) return

    try {
      task.status = 'running'
      task.progress = '资源已生成，正在分析内容...'
      task.updatedAt = Date.now()
      persistTasks()

      const chatGroupId = task.chatGroupId || (task.doneEvent as any)?.chat_group_id || 0
      const questionsResult: any = await getPresentationQuestions({ topic: task.text, chat_group_id: chatGroupId })
      const questions = unwrapResponseData(questionsResult)?.questions || unwrapResponseData(questionsResult)

      if (questions && Array.isArray(questions) && questions.length > 0) {
        ;(task as any).pendingQuestions = questions
        task.status = 'done'
        task.progress = '请选择课件方向以继续...'
      } else {
        // 无问题则直接生成
        await _doGeneratePresentation(task)
      }
    } catch (error: any) {
      // 问题生成失败 → 降级直接生成课件
      console.warn('[GenerationTask] 追问生成失败，直接生成课件:', error)
      try {
        await _doGeneratePresentation(task)
      } catch (e: any) {
        task.status = 'failed'
        task.error = e?.response?.data?.detail || e?.message || '动态课件生成失败'
        task.progress = task.error
      }
    } finally {
      task.updatedAt = Date.now()
      persistTasks()
    }
  } finally {
    delete (task as any)._presentationGenerating
  }
}

const _doGeneratePresentation = async (task: GenerationTask) => {
  const chatGroupId = task.chatGroupId || (task.doneEvent as any)?.chat_group_id || 0
  const answers = (task as any)._answers || undefined
  const presentationResult: any = await generatePresentation({
    topic: task.text,
    answers,
    chat_group_id: chatGroupId,
    video_mode: true,
  })
  const presentation = unwrapResponseData(presentationResult)
  const sourceResource: any = task.files[0]
  const resourceId = sourceResource?.resource_id || sourceResource?.file_id || ''
  const title = sourceResource?.topic || sourceResource?.title || task.text || '学习视频'

  const presentationFile = {
    ...sourceResource,
    file_id: presentation?.id || presentation?.presentation_id || `presentation-${resourceId}`,
    presentation_id: presentation?.id || presentation?.presentation_id || '',
    source_resource_id: resourceId,
    file_type: 'video',
    resource_type: 'video',
    resourceKind: 'presentation',
    filename: `${title}.html`,
    presentation,
    preview_url: presentation?.file_url || presentation?.fileUrl || '',
    file_url: presentation?.file_url || presentation?.fileUrl || '',
    download_url: '',
    source_download_url: sourceResource?.download_url || sourceResource?.downloadUrl || `/resource/${resourceId}/download`,
  }
  // doneEvent.presentation 必须先于 files.push 设置，
  // 否则 watcher 触发 maybeGeneratePresentation 时会因 guard 缺失而重复生成课件
  task.doneEvent = { ...(task.doneEvent as object || {}), presentation, resources: [...task.files, presentationFile] }
  task.files.push(presentationFile)
  task.status = 'done'
  task.progress = '动态课件已生成，可以打开预览。'
  delete (task as any).pendingQuestions
  ;(task as any).questionsShown = true
}

export function useGenerationTaskQueue() {
  const _submitBackendTask = (task: GenerationTask) => {
    task.status = 'running'
    task.progress = '正在提交生成任务...'
    task.updatedAt = Date.now()
    persistTasks()

    void createResourceGenerationTask({
      topic: task.text,
      resource_types: task.tool.resourceTypes || ['document'],
      chat_group_id: task.chatGroupId || 0,
      // 视频模式：中间资源不写入聊天记录，最终课件卡片才是用户想看到的
      bind_chat_history: task.tool.generateMode !== 'video',
      answers: (task as any)._answers || undefined,
    }).then(result => {
      const data = unwrapResponseData(result)
      task.backendTaskId = data?.task_id || data?.taskId || ''
      // 后端创建任务时会分配 chat_group_id，前端及时同步避免后续步骤创建新对话
      if (data?.chat_group_id || data?.chatGroupId) {
        task.chatGroupId = data?.chat_group_id || data?.chatGroupId
      }
      task.progress = formatTaskProgress(data)
      const thinking = getBackendThinking(data)
      if (thinking) task.thinkingProcess = thinking
      task.updatedAt = Date.now()
      streamBackendTask(task)
      pollBackendTask(task)
    }).catch(error => {
      task.status = 'failed'
      task.error = error?.response?.data?.detail || error?.message || '创建生成任务失败'
      task.progress = task.error
      task.updatedAt = Date.now()
    })
  }

  const startTask = (text: string, tool: ResourceToolConfig, chatGroupId: number | string | null) => {
    const task: GenerationTask = reactive({
      id: makeLocalTaskId(),
      backendTaskId: '',
      text,
      tool,
      chatGroupId,
      status: 'running',
      progress: '正在提交生成任务...',
      thinkingProcess: '',
      error: '',
      files: [],
      images: [],
      doneEvent: null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    })

    tasks.unshift(task)
    persistTasks()

    if (tool.generateMode === 'image') {
      runLegacyFrontendTask(task)
      return task
    }

    // 视频模式：追问前置，根据答案按需生成 → 减体量加速
    if (tool.generateMode === 'video') {
      task.progress = '正在分析话题...'
      persistTasks()
      void getPresentationQuestions({ topic: text, chat_group_id: chatGroupId || 0 })
        .then(result => {
          const data = unwrapResponseData(result)
          const questions = data?.questions || data
          // 后端可能为追问创建 chat_group，及时同步
          if (data?.chat_group_id || data?.chatGroupId) {
            task.chatGroupId = data?.chat_group_id || data?.chatGroupId
          }
          if (questions && Array.isArray(questions) && questions.length > 0) {
            ;(task as any).pendingQuestions = questions
            task.status = 'done'
            task.progress = '请选择课件方向以继续...'
          } else {
            _submitBackendTask(task)
          }
          persistTasks()
        })
        .catch(() => {
          _submitBackendTask(task)
        })
      return task
    }

    _submitBackendTask(task)
    return task
  }

  const answerQuestionsAndGenerate = async (task: GenerationTask, answers: Record<string, any>) => {
    ;(task as any)._answers = answers
    ;(task as any).questionsShown = true
    delete (task as any).pendingQuestions

    // 新流程（追问前置）：还没有后端任务 → 先提交生成任务，答案注入 prompt 精准生成
    if (!task.backendTaskId) {
      _submitBackendTask(task)
      return
    }

    // 旧流程兼容：资源已生成 → 直接生成课件
    task.status = 'running'
    task.progress = '正在生成动态课件...'
    task.updatedAt = Date.now()
    persistTasks()

    try {
      await _doGeneratePresentation(task)
    } catch (error: any) {
      task.status = 'failed'
      task.error = error?.response?.data?.detail || error?.message || '动态课件生成失败'
      task.progress = task.error
    } finally {
      task.updatedAt = Date.now()
      persistTasks()
    }
  }

  const hydrateTasks = async () => {
    if (hydratePromise) return hydratePromise
    if (hasHydratedTasks) {
      tasks.filter(task => task.status === 'running').forEach(task => {
        streamBackendTask(task)
        pollBackendTask(task)
      })
      return tasks
    }

    hydratePromise = (async () => {
      const result = await getResourceGenerationTasks()
      const list = unwrapResponseData(result)
      const hydrated = (Array.isArray(list) ? list : [])
        .map(item => upsertBackendTask(item))
        .filter(Boolean) as GenerationTask[]

      await Promise.all(hydrated.map(async task => {
        try {
          const detail = unwrapResponseData(await getResourceGenerationTask(task.backendTaskId))
          applyBackendTaskData(task, detail)
        } catch {
          // Keep list-level task state if detail lookup is temporarily unavailable.
        }
        if (task.status === 'running') {
          streamBackendTask(task)
          pollBackendTask(task)
        }
      }))
      hasHydratedTasks = true
      return hydrated
    })().finally(() => {
      hydratePromise = null
    })

    return hydratePromise
  }

  const getTask = (taskId: string) => tasks.find(task => task.id === taskId || task.backendTaskId === taskId)

  return {
    tasks,
    startTask,
    hydrateTasks,
    maybeGeneratePresentation,
    answerQuestionsAndGenerate,
    getTask,
  }
}
