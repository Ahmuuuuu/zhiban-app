import { generateImage, getImageTaskStatus, streamResourceGeneration } from '../api/apis'

export interface ResourceToolConfig {
  label: string
  generateMode: 'resource' | 'image'
  resourceTypes?: string[]
  aspectRatio?: string
  imageCount?: number
}

export const resourceTools: ResourceToolConfig[] = [
  { label: 'music', generateMode: 'resource', resourceTypes: ['document'] },
  { label: 'image', generateMode: 'image', aspectRatio: '1:1', imageCount: 1 },
  { label: 'ppt', generateMode: 'resource', resourceTypes: ['ppt'] },
  { label: 'word', generateMode: 'resource', resourceTypes: ['document'] },
  { label: 'video', generateMode: 'resource', resourceTypes: ['document'] },
  { label: 'mindmap', generateMode: 'resource', resourceTypes: ['mindmap'] },
]

export function detectGenerationIntent(text: string): ResourceToolConfig | null {
  const trimmed = String(text || '').trim()
  const hasGenerate = /(生成|制作|做|创建|来一份|出一份|画|画一张|设计)/.test(trimmed)
  if (!hasGenerate) return null

  if (/(图片|图|image|img|插图|配图|示意图|图解)/i.test(trimmed))
    return { ...resourceTools.find(t => t.label === 'image')! }
  if (/(ppt|PPT|幻灯片|演示文稿|slide)/i.test(trimmed))
    return { ...resourceTools.find(t => t.label === 'ppt')! }
  if (/(思维导图|mindmap|脑图|mind map)/i.test(trimmed))
    return { ...resourceTools.find(t => t.label === 'mindmap')! }
  if (/(视频|video|课程视频|教学视频)/i.test(trimmed))
    return { ...resourceTools.find(t => t.label === 'video')! }
  if (/(文档|word|学习资源|资料|笔记|教案)/i.test(trimmed))
    return { ...resourceTools.find(t => t.label === 'word')! }
  if (/(音乐|歌曲|music|节奏|旋律)/i.test(trimmed))
    return { ...resourceTools.find(t => t.label === 'music')! }
  return null
}

export type GenerationCallbacks = {
  onProgress?: (msg: string) => void
  onFile?: (fileData: unknown) => void
  onDone?: () => void
  onError?: (err: string) => void
}

export async function executeGeneration(
  text: string,
  tool: ResourceToolConfig,
  chatGroupId: number | string | null,
  callbacks: GenerationCallbacks,
) {
  if (tool.generateMode === 'image') {
    const prompt = text
    if (!prompt) {
      callbacks.onError?.('请告诉我你想生成什么图片')
      return
    }
    callbacks.onProgress?.('正在提交图片生成任务...')
    try {
      const submitRes: any = await generateImage({
        prompt,
        aspect_ratio: tool.aspectRatio || '1:1',
        img_count: tool.imageCount || 1,
      })
      const taskId = submitRes?.data?.task_id
      if (!taskId) {
        callbacks.onError?.('图片生成任务提交失败，请稍后重试。')
        return
      }

      for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const statusRes: any = await getImageTaskStatus(taskId)
        const taskInfo = statusRes?.data
        if (!taskInfo) continue
        if (taskInfo.status === 'done') {
          const images = taskInfo.images || []
          if (images.length) {
            const lines = images.map((r: any) => `![${r.filename || '图片'}](${r.url})`)
            callbacks.onProgress?.(lines.join('\n'))
          } else {
            callbacks.onProgress?.('图片生成完成，但没有返回可展示的图片地址。')
          }
          callbacks.onDone?.()
          return
        }
        if (taskInfo.status === 'failed') {
          callbacks.onError?.(taskInfo.error || '图片生成失败')
          return
        }
        callbacks.onProgress?.(`正在生成图片（${i + 1}/30）...`)
      }
      callbacks.onError?.('图片生成超时，请稍后重试。')
    } catch {
      callbacks.onError?.('图片生成失败，请稍后再试。')
    }
    return
  }

  const resourceTypes = tool.resourceTypes || ['document']
  callbacks.onProgress?.(`正在生成 ${resourceTypes.join(' / ')} 学习资源...`)

  try {
    await streamResourceGeneration(
      {
        topic: text,
        resource_types: resourceTypes,
        chat_group_id: Number(chatGroupId || 0),
      },
      {
        onProgress: (eventData: any) => {
          const finished = Array.isArray(eventData?.resources) ? eventData.resources : []
          callbacks.onProgress?.(
            finished.length
              ? `正在生成学习资源，已完成：${finished.join(' / ')}`
              : `正在生成 ${resourceTypes.join(' / ')} 学习资源...`,
          )
        },
        onFile: (fileData: unknown) => {
          callbacks.onFile?.(fileData)
        },
        onDone: () => {
          callbacks.onDone?.()
        },
        onError: (err: string) => {
          callbacks.onError?.(err)
        },
      },
    )
  } catch {
    callbacks.onError?.('资源生成失败，请稍后再试。')
  }
}
