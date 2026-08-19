<template>
  <Transition name="home-notice-fade">
    <div v-if="visible" class="home-notice-mask" role="presentation" @click.self="dismiss">
      <article
        class="home-notice-popup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="home-notice-title"
        aria-describedby="home-notice-copy"
      >
        <button class="home-notice-close" type="button" aria-label="关闭通知" title="关闭通知" @click="dismiss">
          <X :size="19" />
        </button>

        <div class="home-notice-mark" aria-hidden="true">
          <HeartHandshake :size="24" />
        </div>
        <span class="home-notice-eyebrow">{{ notice.eyebrow }}</span>
        <h2 id="home-notice-title">{{ notice.title }}</h2>
        <div id="home-notice-copy" class="home-notice-copy">
          <p v-for="paragraph in notice.paragraphs" :key="paragraph">{{ paragraph }}</p>
        </div>

        <footer class="home-notice-actions">
          <button class="home-notice-secondary" type="button" @click="dismiss">知道了</button>
        </footer>
      </article>
    </div>
  </Transition>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { HeartHandshake, X } from 'lucide-vue-next'
import { HOME_NOTICE as notice } from './homeNoticeContent'

// 模块状态会在刷新或重新打开网站时重置，但站内路由切换时会保留。
let hasShownInCurrentApp = false

const visible = ref(false)

const dismiss = () => {
  visible.value = false
}

const handleKeydown = event => {
  if (event.key === 'Escape' && visible.value) dismiss()
}

onMounted(() => {
  if (!hasShownInCurrentApp) {
    visible.value = true
    hasShownInCurrentApp = true
  }
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
</script>

<style scoped>
.home-notice-mask {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(16, 42, 74, 0.28);
  backdrop-filter: blur(6px);
}

.home-notice-popup {
  position: relative;
  width: min(560px, 100%);
  padding: 34px 38px 30px;
  border: 1px solid #d5e5f2;
  border-radius: 16px;
  color: #234d7d;
  background: #ffffff;
  box-shadow: 0 24px 70px rgba(25, 70, 116, 0.22);
}

.home-notice-close {
  position: absolute;
  top: 16px;
  right: 16px;
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid #d8e7f2;
  border-radius: 9px;
  color: #5f88aa;
  background: #f8fbfe;
  cursor: pointer;
}

.home-notice-close:hover {
  color: #174b91;
  background: #edf6fd;
}

.home-notice-mark {
  display: grid;
  width: 48px;
  height: 48px;
  margin-bottom: 16px;
  place-items: center;
  border-radius: 13px;
  color: #ffffff;
  background: #2b75be;
}

.home-notice-eyebrow {
  color: #5d91bf;
  font-size: 12px;
  font-weight: 900;
}

.home-notice-popup h2 {
  max-width: calc(100% - 22px);
  margin: 7px 0 17px;
  color: #174b91;
  font-size: 27px;
  line-height: 1.3;
}

.home-notice-copy {
  display: grid;
  gap: 10px;
}

.home-notice-copy p {
  margin: 0;
  color: #4d7091;
  font-size: 14px;
  line-height: 1.85;
}

.home-notice-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.home-notice-actions .home-notice-secondary {
  min-width: 92px;
}

.home-notice-secondary,
.home-notice-primary {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 14px;
  border-radius: 9px;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  text-decoration: none;
  cursor: pointer;
}

.home-notice-secondary {
  border: 1px solid #cfe1ef;
  color: #477399;
  background: #ffffff;
}

.home-notice-secondary:hover {
  background: #f1f8fd;
}

.home-notice-primary {
  border: 1px solid #2365ac;
  color: #ffffff;
  background: #2365ac;
}

.home-notice-primary:hover {
  background: #174b91;
}

.home-notice-fade-enter-active,
.home-notice-fade-leave-active {
  transition: opacity 0.2s ease;
}

.home-notice-fade-enter-active .home-notice-popup,
.home-notice-fade-leave-active .home-notice-popup {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.home-notice-fade-enter-from,
.home-notice-fade-leave-to {
  opacity: 0;
}

.home-notice-fade-enter-from .home-notice-popup,
.home-notice-fade-leave-to .home-notice-popup {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}

@media (max-width: 560px) {
  .home-notice-mask {
    padding: 16px;
  }

  .home-notice-popup {
    padding: 28px 22px 22px;
  }

  .home-notice-popup h2 {
    font-size: 23px;
  }

  .home-notice-actions {
    flex-direction: column-reverse;
  }

  .home-notice-secondary,
  .home-notice-primary {
    width: 100%;
  }
}
</style>
