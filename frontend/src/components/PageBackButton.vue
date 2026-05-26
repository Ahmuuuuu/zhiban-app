<template>
  <button class="back-pill" type="button" @click="goBack">
    返回
  </button>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }

  router.push('/')
}
</script>

<style scoped>
.back-pill {
  min-height: 56px;
  padding: 0 22px;
  border: 1px solid rgba(22, 63, 143, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: #163f8f;
  text-decoration: none;
  font: inherit;
  font-size: 14px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(22, 63, 143, 0.08);
}

.back-pill:hover {
  border-color: rgba(22, 63, 143, 0.26);
  background: rgba(255, 255, 255, 0.92);
}
</style>
