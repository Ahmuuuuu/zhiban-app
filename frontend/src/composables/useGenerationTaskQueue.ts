import { reactive } from 'vue'
import { executeGeneration, type ResourceToolConfig } from './useResourceGeneration'

export type GenerationTaskStatus = 'running' | 'done' | 'failed'

export interface GenerationTask {
  id: string
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

const makeTaskId = () => `generation-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

export function useGenerationTaskQueue() {
  const startTask = (text: string, tool: ResourceToolConfig, chatGroupId: number | string | null) => {
    const task: GenerationTask = reactive({
      id: makeTaskId(),
      text,
      tool,
      chatGroupId,
      status: 'running',
      progress: '正在准备生成资源...',
      error: '',
      files: [],
      images: [],
      doneEvent: null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    })

    tasks.unshift(task)

    void executeGeneration(text, tool, chatGroupId, {
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
      },
      onError: err => {
        task.error = err || '资源生成失败，请稍后再试。'
        task.status = 'failed'
        task.progress = task.error
        task.updatedAt = Date.now()
      },
    }).catch(error => {
      task.error = error?.message || '资源生成失败，请稍后再试。'
      task.status = 'failed'
      task.progress = task.error
      task.updatedAt = Date.now()
    })

    return task
  }

  const getTask = (taskId: string) => tasks.find(task => task.id === taskId)

  return {
    tasks,
    startTask,
    getTask,
  }
}
