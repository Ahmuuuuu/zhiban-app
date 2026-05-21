import { getGeneratedImage, getGeneratedResource, resolveApiUrl } from '../api/apis'

export const SAVED_GENERATED_RESOURCES_KEY = 'zhiban_saved_generated_resource_refs'

const readJson = key => {
  try {
    const value = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

const writeJson = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value))
}

export const readSavedResourceRefs = visibility => {
  const refs = readJson(SAVED_GENERATED_RESOURCES_KEY)
  return visibility ? refs.filter(item => item.visibility === visibility) : refs
}

export const saveGeneratedResourceRef = payload => {
  const sourceId = String(payload.sourceId || '')
  if (!sourceId) {
    throw new Error('生成资源缺少 id，暂时不能保存。')
  }

  const kind = payload.kind || 'resource'
  const id = `${kind}-${sourceId}`
  const record = {
    id,
    sourceId,
    kind,
    fileType: payload.fileType || 'file',
    category: payload.category || 'reference',
    visibility: payload.visibility || 'private',
    createdAt: new Date().toISOString()
  }

  const refs = readSavedResourceRefs()
  const next = [record, ...refs.filter(item => item.id !== id)]
  writeJson(SAVED_GENERATED_RESOURCES_KEY, next)
  window.dispatchEvent(new CustomEvent('zhiban-generated-resource-saved', { detail: record }))
  return record
}

const unwrap = result => result?.data?.data ?? result?.data ?? result

const normalizeDetail = (detail, ref) => {
  const item = unwrap(detail) || {}
  const title =
    item.title ||
    item.filename ||
    item.file_name ||
    item.name ||
    `${ref.kind === 'image' ? '生成图片' : '生成资源'}-${ref.sourceId}`
  const fileType = item.file_type || item.fileType || item.resource_type || item.resourceType || ref.fileType || 'file'
  const content = item.preview || item.content || item.text || item.preview_content || item.previewContent || ''

  return {
    doc_id: `${ref.kind}-${ref.sourceId}`,
    sourceId: ref.sourceId,
    source: 'generated',
    title,
    content,
    type: fileType,
    category: ref.category || (String(fileType).includes('exercise') ? 'exercise' : 'reference'),
    categoryLabel: '',
    visibility: ref.visibility || 'private',
    created_at: item.created_at || item.createdAt || ref.createdAt || '',
    previewUrl: resolveApiUrl(item.preview_url || item.previewUrl || item.preview || item.url || item.image_url || item.imageUrl || ''),
    downloadUrl: resolveApiUrl(
      item.download_url ||
        item.downloadUrl ||
        item.url ||
        (ref.kind === 'image' ? `/image/${ref.sourceId}/download` : `/resource/${ref.sourceId}/download`)
    )
  }
}

export const hydrateSavedResourceRefs = async visibility => {
  const refs = readSavedResourceRefs(visibility)
  const settled = await Promise.allSettled(
    refs.map(async ref => {
      const detail = ref.kind === 'image'
        ? await getGeneratedImage(ref.sourceId)
        : await getGeneratedResource(ref.sourceId)
      return normalizeDetail(detail, ref)
    })
  )

  return settled
    .filter(item => item.status === 'fulfilled')
    .map(item => item.value)
}
