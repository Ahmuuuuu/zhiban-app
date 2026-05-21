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
  const hasGenerate = /(生成|制作|做|创建|来一份|出一份|画|设计|规划|整理)/.test(trimmed)
  if (!hasGenerate) return null

  if (/(图片|图像|image|img|插图|配图|示意图|图解|海报|插画)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'image')! }
  }
  if (/(ppt|PPT|幻灯片|演示|课件|slide)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'ppt')! }
  }
  if (/(思维导图|mindmap|脑图|mind map)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'mindmap')! }
  }
  if (/(视频|video|课程视频|教学视频|脚本|分镜)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'video')! }
  }
  if (/(文档|word|学习资源|资料|笔记|教案|讲义|总结)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'word')! }
  }
  if (/(音乐|歌曲|music|节奏|旋律)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'music')! }
  }
  return null
}

export type GenerationCallbacks = {
  onProgress?: (msg: string) => void
  onFile?: (fileData: unknown) => void
  onDone?: () => void
  onError?: (err: string) => void
}

const unwrapResponseData = (result: any) => result?.data?.data ?? result?.data ?? result

const normalizeImageRecords = (payload: any): any[] => {
  const data = unwrapResponseData(payload)

  if (Array.isArray(data)) return data

  const records =
    data?.images ||
    data?.records ||
    data?.image_list ||
    data?.imageList ||
    data?.data ||
    []

  if (Array.isArray(records)) return records

  const urls = data?.urls || data?.image_urls || data?.imageUrls || data?.url || data?.image_url || data?.imageUrl
  const list = Array.isArray(urls) ? urls : urls ? [urls] : []

  return list.map((url: string, index: number) => ({
    filename: data?.filename || `图片 ${index + 1}`,
    url,
  }))
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
      const submitData = unwrapResponseData(submitRes)
      const taskId = submitData?.task_id || submitData?.taskId || submitData?.id

      if (!taskId) {
        const immediateImages = normalizeImageRecords(submitRes)
        if (immediateImages.length) {
          callbacks.onProgress?.(
            immediateImages.map((r: any) => `![${r.filename || '图片'}](${r.url || r.image_url || r.imageUrl})`).join('\n'),
          )
          callbacks.onDone?.()
          return
        }

        callbacks.onError?.('图片生成任务提交失败，请稍后重试。')
        return
      }

      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000))
        const statusRes: any = await getImageTaskStatus(taskId)
        const taskInfo = unwrapResponseData(statusRes)
        if (!taskInfo) continue

        if (taskInfo.status === 'done') {
          const images = normalizeImageRecords(taskInfo)
          if (images.length) {
            callbacks.onProgress?.(
              images.map((r: any) => `![${r.filename || '图片'}](${r.url || r.image_url || r.imageUrl})`).join('\n'),
            )
            callbacks.onDone?.()
          } else {
            callbacks.onError?.('图片没有下载成功，请稍后重试。')
          }
          return
        }

        if (['download_failed', 'download_error'].includes(String(taskInfo.status))) {
          callbacks.onError?.(taskInfo.error || '图片没有下载成功，请稍后重试。')
          return
        }

        if (taskInfo.status === 'failed') {
          if (/下载|download/i.test(String(taskInfo.error || ''))) {
            callbacks.onError?.(taskInfo.error || '图片没有下载成功，请稍后重试。')
          } else {
            callbacks.onError?.(taskInfo.error || '图片生成失败')
          }
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
