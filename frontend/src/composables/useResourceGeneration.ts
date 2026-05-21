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
  { label: 'quiz', generateMode: 'resource', resourceTypes: ['exercise'] },
]

export function detectGenerationIntent(text: string): ResourceToolConfig | null {
  const trimmed = String(text || '').trim()
  const hasGenerate = /(鐢熸垚|鍒朵綔|鍋殀鍒涘缓|鏉ヤ竴浠絴鍑轰竴浠絴鐢粅璁捐|瑙勫垝|鏁寸悊)/.test(trimmed)
  if (!hasGenerate) return null

  if (/(鍥剧墖|鍥惧儚|image|img|鎻掑浘|閰嶅浘|绀烘剰鍥緗鍥捐В|娴锋姤|鎻掔敾)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'image')! }
  }
  if (/(ppt|PPT|骞荤伅鐗噟婕旂ず|璇句欢|slide)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'ppt')! }
  if (/(题目|题库|练习题|习题|测试题|quiz|exercise|出题|做题|选择题|填空题|简答题)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'quiz')! }
  }
  }
  if (/(鎬濈淮瀵煎浘|mindmap|鑴戝浘|mind map)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'mindmap')! }
  }
  if (/(瑙嗛|video|璇剧▼瑙嗛|鏁欏瑙嗛|鑴氭湰|鍒嗛暅)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'video')! }
  }
  if (/(鏂囨。|word|瀛︿範璧勬簮|璧勬枡|绗旇|鏁欐|璁蹭箟|鎬荤粨)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'word')! }
  }
  if (/(闊充箰|姝屾洸|music|鑺傚|鏃嬪緥)/i.test(trimmed)) {
    return { ...resourceTools.find(t => t.label === 'music')! }
  }
  return null
}

export type GenerationCallbacks = {
  onProgress?: (msg: string) => void
  onFile?: (fileData: unknown) => void
  onImage?: (imageData: unknown) => void
  onDone?: (eventData?: unknown) => void
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
    filename: data?.filename || `鍥剧墖 ${index + 1}`,
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

    callbacks.onProgress?.('姝ｅ湪鎻愪氦鍥剧墖鐢熸垚浠诲姟...')

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
          immediateImages.forEach((image: unknown) => callbacks.onImage?.(image))
          callbacks.onProgress?.(
            immediateImages.map((r: any) => `![${r.filename || '鍥剧墖'}](${r.url || r.image_url || r.imageUrl})`).join('\n'),
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
            images.forEach((image: unknown) => callbacks.onImage?.(image))
            callbacks.onProgress?.(
              images.map((r: any) => `![${r.filename || '鍥剧墖'}](${r.url || r.image_url || r.imageUrl})`).join('\n'),
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
          if (/涓嬭浇|download/i.test(String(taskInfo.error || ''))) {
            callbacks.onError?.(taskInfo.error || '图片没有下载成功，请稍后重试。')
          } else {
            callbacks.onError?.(taskInfo.error || '鍥剧墖鐢熸垚澶辫触')
          }
          return
        }

        callbacks.onProgress?.(`姝ｅ湪鐢熸垚鍥剧墖锛?{i + 1}/30锛?..`)
      }

      callbacks.onError?.('图片生成超时，请稍后重试。')
    } catch {
      callbacks.onError?.('图片生成失败，请稍后再试。')
    }
    return
  }

  const resourceTypes = tool.resourceTypes || ['document']
  callbacks.onProgress?.(`姝ｅ湪鐢熸垚 ${resourceTypes.join(' / ')} 瀛︿範璧勬簮...`)

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
              : `姝ｅ湪鐢熸垚 ${resourceTypes.join(' / ')} 瀛︿範璧勬簮...`,
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
