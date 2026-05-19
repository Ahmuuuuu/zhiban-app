<template>
  <main class="study-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">Study Status</p>
        <h1>学习情况</h1>
        <p>汇总近期学习状态，帮助你快速看到进度、活跃度和待加强内容。</p>
      </div>
    </header>

    <section class="status-grid">
      <article
        v-for="item in statusItems"
        :key="item.label"
        class="status-card"
      >
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
        <span>{{ item.tip }}</span>
      </article>
    </section>

    <section class="review-panel">
      <h2>学习观察</h2>
      <p>这里可以继续接入后端学习统计接口，用真实进度、资源阅读记录和 AI 对话情况填充。</p>
    </section>
  </main>
</template>

<script setup>
const statusItems = [
  { label: '资源数量', value: '--', tip: '等待后端统计' },
  { label: '学习进度', value: '--', tip: '等待后端统计' },
  { label: '近期活跃', value: '--', tip: '等待后端统计' }
]
</script>

<style scoped>
.study-panel {
  height: 100%;
  min-height: 0;
  padding: 26px 34px 30px;
  color: #163f8f;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.panel-header h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.15;
}

.panel-header p:last-child {
  margin: 8px 0 0;
  color: #5f8fc3;
  font-size: 14px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.status-card,
.review-panel {
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #fafafa;
}

.status-card {
  min-height: 150px;
  padding: 20px;
}

.status-card p {
  margin: 0;
  color: #5f8fc3;
  font-size: 13px;
  font-weight: 800;
}

.status-card strong {
  display: block;
  margin-top: 18px;
  color: #163f8f;
  font-size: 34px;
  line-height: 1;
}

.status-card span {
  display: block;
  margin-top: 12px;
  color: #5f8fc3;
  font-size: 13px;
}

.review-panel {
  flex: 1;
  min-height: 0;
  padding: 22px;
  background: #c9dce9;
}

.review-panel h2 {
  margin: 0;
  color: #163f8f;
  font-size: 20px;
}

.review-panel p {
  margin: 12px 0 0;
  color: #5f8fc3;
  font-size: 14px;
  line-height: 1.8;
}

@media (max-width: 980px) {
  .study-panel {
    height: auto;
    min-height: 100%;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .study-panel {
    padding: 20px;
  }
}
</style>
