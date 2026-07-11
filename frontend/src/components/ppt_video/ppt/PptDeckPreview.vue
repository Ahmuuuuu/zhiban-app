<template>
  <PptPreview
    v-if="slidesModel.length"
    v-model:slides="slidesModel"
    :title="title"
    :editable="editable"
    :exporting="exporting"
    :annotatable="annotatable"
    :annotations="annotations"
    :theme-id="themeId"
    @change="$emit('change', $event)"
    @export-pptx="$emit('export-pptx', $event)"
    @create-note="$emit('create-note', $event)"
    @update-note="(id, payload) => $emit('update-note', id, payload)"
    @delete-note="$emit('delete-note', $event)"
  />
</template>

<script setup>
import { computed } from 'vue'
import PptPreview from '../../PptPreview.vue'

const props = defineProps({
  slides: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: ''
  },
  editable: {
    type: Boolean,
    default: true
  },
  exporting: {
    type: Boolean,
    default: false
  },
  annotatable: {
    type: Boolean,
    default: false
  },
  annotations: {
    type: Array,
    default: () => []
  },
  themeId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'update:slides',
  'change',
  'export-pptx',
  'create-note',
  'update-note',
  'delete-note'
])

const slidesModel = computed({
  get: () => props.slides,
  set: value => emit('update:slides', value)
})
</script>
