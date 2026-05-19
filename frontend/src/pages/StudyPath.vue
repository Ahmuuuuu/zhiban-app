<template>
  <main class="study-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">Study Path</p>
        <h1>学习路径</h1>
        <p>整理阶段目标、学习任务和下一步计划，让学习节奏更清晰。</p>
      </div>
    </header>

    <section class="path-board">
      <article
        v-for="item in pathItems"
        :key="item.title"
        class="path-card"
      >
        <span>{{ item.step }}</span>
        <div>
          <h2>{{ item.title }}</h2>
          <p>{{ item.desc }}</p>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup>
const pathItems = [
  { step: '01', title: '确认学习目标', desc: '把课程、考试或项目目标拆成可以执行的小阶段。' },
  { step: '02', title: '匹配学习资源', desc: '结合已导入资料和公开资源，优先学习最相关的内容。' },
  { step: '03', title: '复盘学习进度', desc: '根据学习情况调整节奏，补齐薄弱环节。' }
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

.path-board {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  align-content: start;
}

.path-card {
  min-height: 220px;
  padding: 20px;
  border: 1px solid #c9dce9;
  border-radius: 8px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 24px;
}

.path-card span {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  background: #163f8f;
  color: #fafafa;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
}

.path-card h2 {
  margin: 0;
  color: #163f8f;
  font-size: 18px;
}

.path-card p {
  margin: 10px 0 0;
  color: #5f8fc3;
  font-size: 14px;
  line-height: 1.7;
}

@media (max-width: 980px) {
  .study-panel {
    height: auto;
    min-height: 100%;
  }

  .path-board {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .study-panel {
    padding: 20px;
  }
}
</style>
