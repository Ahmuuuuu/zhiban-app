import { reactive } from 'vue'
import {
  createResourceGenerationTask,
  generatePresentation,
  getResourceGenerationTask,
  getResourceGenerationTasks,
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
  error: string
  files: unknown[]
  images: unknown[]
  doneEvent: unknown
  createdAt: number
  updatedAt: number
}

const tasks = reactive<GenerationTask[]>([])
const pollingTaskIds = new Set<string>()

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
  task.error = taskData?.error || ''
  task.files.splice(0, task.files.length, ...normalizeTaskFiles(taskData))
  task.doneEvent = {
    chat_group_id: task.chatGroupId,
    resources: task.files,
  }
  task.updatedAt = Date.now()

  // 任务完成/失败时通知 TopNav 刷新铃铛（模块级，不受组件卸载影响）
  if (prevStatus === 'running' && task.status !== 'running') {
    console.log('[GenerationTask] 任务状态变更，发送通知刷新事件', { taskId: task.backendTaskId, prevStatus, newStatus: task.status })
    window.dispatchEvent(new CustomEvent('zhiban:notification-update'))
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

const runLegacyFrontendTask = (task: GenerationTask) => {
  void executeGeneration(task.text, task.tool, task.chatGroupId, {
    onProgress: msg => {
      task.progress = msg
      task.updatedAt = Date.now()
    },
    onFile: fileData => {
      task.files.push(fileData)
      task.updatedAt = Date.now()
    },
    onImage: imageData => {
      task.images.push(imageData)
      task.updatedAt = Date.now()
    },
    onDone: eventData => {
      task.doneEvent = eventData || null
      task.status = 'done'
      task.progress = task.progress || '资源已生成'
      task.updatedAt = Date.now()
      console.log('[GenerationTask] legacy 任务完成，发送通知刷新事件', { taskId: task.backendTaskId })
      window.dispatchEvent(new CustomEvent('zhiban:notification-update'))
    },
    onError: err => {
      task.error = err || '资源生成失败，请稍后再试。'
      task.status = 'failed'
      task.progress = task.error
      task.updatedAt = Date.now()
      console.log('[GenerationTask] legacy 任务失败，发送通知刷新事件', { taskId: task.backendTaskId })
      window.dispatchEvent(new CustomEvent('zhiban:notification-update'))
    },
  }).catch(error => {
    task.error = error?.message || '资源生成失败，请稍后再试。'
    task.status = 'failed'
    task.progress = task.error
    task.updatedAt = Date.now()
    console.log('[GenerationTask] legacy 任务异常，发送通知刷新事件', { taskId: task.backendTaskId })
    window.dispatchEvent(new CustomEvent('zhiban:notification-update'))
  })
}

const maybeGeneratePresentation = async (task: GenerationTask) => {
  if (task.tool.generateMode !== 'video' || task.status !== 'done') return
  if ((task.doneEvent as any)?.presentation || !task.files.length) return

  try {
    task.status = 'running'
    task.progress = '资源已生成，正在生成动态课件...'
    const presentationResult: any = await generatePresentation({ topic: task.text })
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
    task.files.splice(0, task.files.length, presentationFile)
    task.doneEvent = { ...(task.doneEvent as object || {}), presentation }
    task.status = 'done'
    task.progress = '动态课件已生成，可以打开预览。'
  } catch (error: any) {
    task.status = 'failed'
    task.error = error?.response?.data?.detail || error?.message || '动态课件生成失败'
    task.progress = task.error
  } finally {
    task.updatedAt = Date.now()
  }
}

export function useGenerationTaskQueue() {
  const startTask = (text: string, tool: ResourceToolConfig, chatGroupId: number | string | null) => {
    const task: GenerationTask = reactive({
      id: makeLocalTaskId(),
      backendTaskId: '',
      text,
      tool,
      chatGroupId,
      status: 'running',
      progress: '正在提交生成任务...',
      error: '',
      files: [],
      images: [],
      doneEvent: null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    })

    tasks.unshift(task)

    if (tool.generateMode === 'image') {
      runLegacyFrontendTask(task)
      return task
    }

    void createResourceGenerationTask({
      topic: text,
      resource_types: tool.resourceTypes || ['document'],
      chat_group_id: chatGroupId || 0,
    }).then(result => {
      const data = unwrapResponseData(result)
      task.backendTaskId = data?.task_id || data?.taskId || ''
      task.progress = formatTaskProgress(data)
      task.updatedAt = Date.now()
      pollBackendTask(task)
    }).catch(error => {
      task.status = 'failed'
      task.error = error?.response?.data?.detail || error?.message || '创建生成任务失败'
      task.progress = task.error
      task.updatedAt = Date.now()
    })

    return task
  }

  const hydrateTasks = async () => {
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
      if (task.status === 'running') pollBackendTask(task)
    }))
    return hydrated
  }

  const getTask = (taskId: string) => tasks.find(task => task.id === taskId || task.backendTaskId === taskId)

  return {
    tasks,
    startTask,
    hydrateTasks,
    maybeGeneratePresentation,
    getTask,
  }
}
