import { generateImage, generatePresentation, getImageTaskStatus, streamResourceGeneration } from '../api/apis'

export interface ResourceToolConfig {
  label: string
  generateMode: 'resource' | 'image' | 'video'
  resourceTypes?: string[]
  aspectRatio?: string
  imageCount?: number
}

export const resourceTools: ResourceToolConfig[] = [
  { label: 'image', generateMode: 'image', aspectRatio: '1:1', imageCount: 1 },
  { label: 'ppt', generateMode: 'resource', resourceTypes: ['ppt'] },
  { label: 'word', generateMode: 'resource', resourceTypes: ['document'] },
  { label: 'video', generateMode: 'video', resourceTypes: ['document'] },
  { label: 'mindmap', generateMode: 'resource', resourceTypes: ['mindmap'] },
  { label: 'quiz', generateMode: 'resource', resourceTypes: ['exercise'] },
]

export function detectGenerationIntent(text: string): ResourceToolConfig | null {
  const trimmed = String(text || '').trim()
  const hasGenerate = /(生成|制作|做|创建|来一份|出一份|出题|设计|规划|整理|测一测|测试|quiz|exercise)/i.test(trimmed)
  if (!hasGenerate) return null

  if (/(题目|题库|练习题|习题|测试题|quiz|exercise|出题|做题|选择题|填空题|简答题|测一测)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'quiz')! }
  }
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
  return null
}

export type GenerationCallbacks = {
  onSubmitted?: (data: unknown) => void
  onProgress?: (msg: string) => void
  onFile?: (fileData: unknown) => void
  onImage?: (imageData: unknown) => void
  onDone?: (eventData?: unknown) => void
  onError?: (err: string) => void
}

const unwrapResponseData = (result: any) => result?.data?.data ?? result?.data ?? result

const getGeneratedResourceId = (resource: any) => {
  const directId = resource?.resource_id || resource?.resourceId || resource?.file_id || resource?.fileId || resource?.id || ''
  if (directId) return String(directId)

  const url = String(resource?.download_url || resource?.downloadUrl || resource?.url || '')
  const match = url.match(/\/resource\/([^/?#]+)(?:\/download)?/i)
  return match?.[1] || ''
}

const isNarratableType = (resource: any) => {
  const type = String(resource?.file_type || resource?.fileType || resource?.resource_type || resource?.resourceType || '').toLowerCase()
  return /document|ppt|mindmap|mind_map|mind-map|case|reading|text|txt/.test(type)
}

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
        chat_group_id: Number(chatGroupId || 0),
      })
      const submitData = unwrapResponseData(submitRes)
      callbacks.onSubmitted?.(submitData)
      const taskId = submitData?.task_id || submitData?.taskId || submitData?.id

      if (!taskId) {
        const immediateImages = normalizeImageRecords(submitRes)
        if (immediateImages.length) {
          immediateImages.forEach((image: unknown) => callbacks.onImage?.(image))
          callbacks.onProgress?.(
            immediateImages.map((r: any) => `![${r.filename || '图片'}](${r.url || r.image_url || r.imageUrl})`).join('\n'),
          )
          callbacks.onDone?.({ chat_group_id: submitData?.chat_group_id || submitData?.chatGroupId })
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
            images.forEach((image: unknown) => callbacks.onImage?.(image))
            callbacks.onProgress?.(
              images.map((r: any) => `![${r.filename || '图片'}](${r.url || r.image_url || r.imageUrl})`).join('\n'),
            )
            callbacks.onDone?.({ chat_group_id: taskInfo.chat_group_id || taskInfo.chatGroupId || submitData?.chat_group_id })
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

        callbacks.onProgress?.(`正在生成图片 ${Math.round(((i + 1) / 30) * 100)}%...`)
      }

      callbacks.onError?.('图片生成超时，请稍后重试。')
    } catch {
      callbacks.onError?.('图片生成失败，请稍后再试。')
    }
    return
  }

  if (tool.generateMode === 'video') {
    const resourceTypes = tool.resourceTypes || ['document']
    const generatedResources: any[] = []

    callbacks.onProgress?.('正在生成视频脚本...')

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
              finished.length ? '视频脚本已生成，正在整理内容...' : '正在生成视频脚本...',
            )
          },
          onFile: (fileData: any) => {
            generatedResources.push(fileData)
          },
          onDone: (eventData: any) => {
            if (Array.isArray(eventData?.resources)) {
              generatedResources.push(...eventData.resources)
            }
          },
          onError: (err: string) => {
            callbacks.onError?.(err)
          },
        },
      )

      const sourceResource = generatedResources.find(item => getGeneratedResourceId(item) && isNarratableType(item)) ||
        generatedResources.find(item => getGeneratedResourceId(item))
      const resourceId = getGeneratedResourceId(sourceResource)

      if (!resourceId) {
        callbacks.onError?.('视频脚本已生成，但没有拿到可生成视频的资源 ID。')
        return
      }

      callbacks.onProgress?.('视频脚本已生成，正在生成动态课件...')
      const presentationResult: any = await generatePresentation({ topic: text })
      const presentation = unwrapResponseData(presentationResult)
      const title = sourceResource?.topic || sourceResource?.title || text || '学习视频'

      callbacks.onFile?.({
        ...sourceResource,
        file_id: presentation?.id || presentation?.presentation_id || `presentation-${resourceId}`,
        presentation_id: presentation?.id || presentation?.presentation_id || '',
        source_resource_id: resourceId,
        file_type: 'video',
        resource_type: 'video',
        resourceKind: 'presentation',
        filename: `${title}.html`,
        content: sourceResource?.content || sourceResource?.text || sourceResource?.preview_content || '',
        presentation,
        preview_url: presentation?.file_url || presentation?.fileUrl || '',
        file_url: presentation?.file_url || presentation?.fileUrl || '',
        download_url: '',
        source_download_url: sourceResource?.download_url || sourceResource?.downloadUrl || `/resource/${resourceId}/download`,
      })
      callbacks.onProgress?.('动态课件已生成，可以打开预览。')
      callbacks.onDone?.({
        chat_group_id: presentation?.chat_group_id || presentation?.chatGroupId,
        resources: [],
        presentation,
      })
    } catch (error: any) {
      callbacks.onError?.(error?.response?.data?.detail || error?.message || '视频生成失败，请稍后再试。')
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
              ? `正在生成学习资源，已完成：${finished.map((item: any) => typeof item === 'string' ? item : item?.file_type || item?.resource_type || 'resource').join(' / ')}`
              : `正在生成 ${resourceTypes.join(' / ')} 学习资源...`,
          )
        },
        onFile: (fileData: unknown) => {
          callbacks.onFile?.(fileData)
        },
        onDone: (eventData: unknown) => {
          callbacks.onDone?.(eventData)
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
