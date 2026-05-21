import { generateImage, streamResourceGeneration } from '../api/apis'

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

function unwrapResponseData(result: any) {
  return result?.data?.data ?? result?.data ?? result
}

function normalizeImageRecords(result: any): any[] {
  const payload = unwrapResponseData(result)

  if (Array.isArray(payload)) return payload

  const records =
    payload?.records ||
    payload?.images ||
    payload?.image_list ||
    payload?.imageList ||
    payload?.data ||
    []

  if (Array.isArray(records)) return records

  const urls = payload?.urls || payload?.image_urls || payload?.imageUrls || payload?.url || payload?.image_url || payload?.imageUrl
  const list = Array.isArray(urls) ? urls : urls ? [urls] : []

  return list.map((url: string, index: number) => ({
    filename: payload?.filename || `图片 ${index + 1}`,
    url,
  }))
}

function getImageStatus(result: any) {
  return unwrapResponseData(result)?.status ?? result?.status
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

    callbacks.onProgress?.('正在生成图片...')

    try {
      const result: any = await generateImage({
        prompt,
        aspect_ratio: tool.aspectRatio || '1:1',
        img_count: tool.imageCount || 1,
      })
      const status = getImageStatus(result)
      const records = normalizeImageRecords(result)

      if (records.length) {
        const lines = records.map((r: any) => `![${r.filename || '图片'}](${r.url || r.image_url || r.imageUrl})`)
        callbacks.onDone?.()
        callbacks.onProgress?.(lines.join('\n'))
      } else if (status !== undefined) {
        callbacks.onProgress?.(`图片生成状态：${status}，但暂时没有返回可展示的图片地址。`)
      } else {
        callbacks.onProgress?.('图片生成完成，但没有返回可展示的图片地址。')
      }
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
