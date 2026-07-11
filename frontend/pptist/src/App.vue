<template>
  <template v-if="slides.length">
    <Screen v-if="screening" />
    <Editor v-else-if="_isPC" />
    <Mobile v-else />
  </template>
  <FullscreenSpin tip="数据初始化中，请稍等 ..." v-else  loading :mask="false" />
</template>

<script lang="ts" setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { nanoid } from 'nanoid'
import { useScreenStore, useMainStore, useSnapshotStore, useSlidesStore } from '@/store'
import { LOCALSTORAGE_KEY_DISCARDED_DB } from '@/configs/storage'
import { deleteDiscardedDB } from '@/utils/database'
import { isPC } from '@/utils/common'
import api from '@/services'

import Editor from './views/Editor/index.vue'
import Screen from './views/Screen/index.vue'
import Mobile from './views/Mobile/index.vue'
import FullscreenSpin from '@/components/FullscreenSpin.vue'

const _isPC = isPC()

const mainStore = useMainStore()
const slidesStore = useSlidesStore()
const snapshotStore = useSnapshotStore()
const screenStore = useScreenStore()
const { databaseId } = storeToRefs(mainStore)
const { slides } = storeToRefs(slidesStore)
const { screening } = storeToRefs(screenStore)

const isAudienceMode = new URLSearchParams(window.location.search).get('mode') === 'audience'
const zhibanPayloadKey = new URLSearchParams(window.location.search).get('source')
const ZHIBAN_PAYLOAD_PREFIX = 'zhiban:pptist:payload:'

if (import.meta.env.MODE !== 'development') {
  window.onbeforeunload = () => false
}

const createFallbackSlides = (title = 'Zhiban PPT') => [{
  id: nanoid(10),
  background: { type: 'solid', color: '#ffffff' },
  elements: [{
    type: 'text',
    id: nanoid(10),
    left: 90,
    top: 190,
    width: 820,
    height: 120,
    rotate: 0,
    content: `<p style="text-align:center;"><strong><span style="font-size:44px;color:#163f8f;">${title}</span></strong></p>`,
    defaultFontName: '',
    defaultColor: '#163f8f',
    lineHeight: 1.2,
    fixedHeight: true,
    vAlign: 'middle',
    textType: 'title',
  }],
}]

const readLatestZhibanPayload = () => {
  if (zhibanPayloadKey) {
    return localStorage.getItem(zhibanPayloadKey) || sessionStorage.getItem(zhibanPayloadKey) || ''
  }

  const latestKey = Object.keys(localStorage)
    .filter(key => key.startsWith(ZHIBAN_PAYLOAD_PREFIX))
    .sort()
    .pop()

  return latestKey ? localStorage.getItem(latestKey) || '' : ''
}

const setFallbackSlides = (title?: string) => {
  slidesStore.setSlides(createFallbackSlides(title || 'Zhiban PPT') as any)
}

const loadMockSlides = async () => {
  try {
    const mockSlides = await api.getMockData('slides')
    if (Array.isArray(mockSlides) && mockSlides.length) {
      slidesStore.setSlides(mockSlides)
      return
    }
  }
  catch (error) {
    console.warn('[Zhiban PPTist] mock slides load failed, fallback to local slide.', error)
  }

  setFallbackSlides()
}

onMounted(async () => {
  if (isAudienceMode) {
    slidesStore.setSlides([{
      id: nanoid(10),
      elements: [],
    }])
    screenStore.setScreening(true)
  }
  else {
    const payload = readLatestZhibanPayload()

    if (payload) {
      try {
        const data = JSON.parse(payload)
        if (zhibanPayloadKey) localStorage.removeItem(zhibanPayloadKey)
        if (data.title) slidesStore.setTitle(data.title)
        if (data.theme) slidesStore.setTheme(data.theme)
        if (data.viewportSize) slidesStore.setViewportSize(data.viewportSize)
        if (data.viewportRatio) slidesStore.setViewportRatio(data.viewportRatio)
        if (Array.isArray(data.slides) && data.slides.length) {
          slidesStore.setSlides(data.slides, data.theme || undefined)
        }
        else {
          await loadMockSlides()
        }
      }
      catch (error) {
        console.warn('[Zhiban PPTist] payload parse failed, fallback to local slide.', error)
        setFallbackSlides()
      }
    }
    else {
      await loadMockSlides()
    }

    try {
      await deleteDiscardedDB()
      snapshotStore.initSnapshotDatabase()
    }
    catch (error) {
      console.warn('[Zhiban PPTist] snapshot database init failed.', error)
    }
  }
})

// 应用注销时向 localStorage 中记录下本次 indexedDB 的数据库ID，用于之后清除数据库
window.addEventListener('beforeunload', () => {
  const discardedDB = localStorage.getItem(LOCALSTORAGE_KEY_DISCARDED_DB)
  const discardedDBList: string[] = discardedDB ? JSON.parse(discardedDB) : []

  discardedDBList.push(databaseId.value)

  const newDiscardedDB = JSON.stringify(discardedDBList)
  localStorage.setItem(LOCALSTORAGE_KEY_DISCARDED_DB, newDiscardedDB)
})
</script>

<style lang="scss">
#app {
  height: 100%;
}
</style>
