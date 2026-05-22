<template>
  <main class="question-bank-page">
    <header class="bank-header">
      <router-link class="back-link" to="/chat">返回对话</router-link>
      <div>
        <p>Question Bank</p>
        <h1>题库</h1>
      </div>
      <button type="button" class="refresh-btn" @click="loadQuizzes">刷新</button>
    </header>

    <section v-if="quizzes.length" class="quiz-grid">
      <article v-for="quiz in quizzes" :key="quiz.id" class="quiz-card">
        <div class="quiz-card__top">
          <span>{{ quiz.questionCount || quiz.questions?.length || 0 }} 题</span>
          <small>{{ formatDate(quiz.createdAt) }}</small>
        </div>
        <h2>{{ quiz.title || 'AI 生成题目' }}</h2>
        <p>{{ quiz.filename || 'AI 生成练习题' }}</p>
        <p v-if="quiz.lastAttemptAt" class="score-line">
          最近 {{ formatScore(quiz.lastScore) }} 分 / 最好 {{ formatScore(quiz.bestScore) }} 分
        </p>
        <router-link class="start-btn" :to="`/question-bank/${quiz.id}`">开始练习</router-link>
      </article>
    </section>

    <section v-else class="empty-state">
      <h2>还没有生成题目</h2>
      <p>在 AI 对话里生成练习题，保存到资源中心后也会出现在这里。</p>
      <router-link class="start-btn" to="/chat">去生成题目</router-link>
    </section>
  </main>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { readQuizBank } from '../utils/quizBank'

const quizzes = ref([])

const loadQuizzes = () => {
  quizzes.value = readQuizBank()
}

const formatDate = value => {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

const formatScore = value => {
  const score = Number(value)
  return Number.isFinite(score) ? score.toFixed(1) : '0.0'
}

onMounted(() => {
  loadQuizzes()
  window.addEventListener('zhiban-quiz-bank-updated', loadQuizzes)
})

onUnmounted(() => {
  window.removeEventListener('zhiban-quiz-bank-updated', loadQuizzes)
})
</script>

<style scoped>
.question-bank-page {
  min-height: 100vh;
  padding: 30px 36px;
  background:
    radial-gradient(ellipse 72% 44% at 10% 0%, rgba(209, 244, 250, 0.46), transparent 70%),
    linear-gradient(135deg, #fafafa 0%, rgb(237, 249, 252) 52%, #fafafa 100%);
  color: #163f8f;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.bank-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 18px;
  margin-bottom: 28px;
}

.bank-header p {
  margin: 0 0 4px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.bank-header h1 {
  margin: 0;
  font-size: 30px;
}

.back-link,
.refresh-btn,
.start-btn {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid rgba(22, 63, 143, 0.2);
  border-radius: 18px;
  background: #ffffff;
  color: #163f8f;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.quiz-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px;
}

.quiz-card,
.empty-state {
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 44px rgba(22, 63, 143, 0.08);
}

.quiz-card {
  min-height: 230px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quiz-card__top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.quiz-card__top span {
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: #c9dce9;
  color: #163f8f;
  display: inline-flex;
  align-items: center;
}

.quiz-card h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.35;
}

.quiz-card p,
.empty-state p {
  margin: 0;
  color: #5f8fc3;
  line-height: 1.7;
}

.score-line {
  color: #163f8f !important;
  font-size: 13px;
  font-weight: 800;
}

.start-btn {
  margin-top: auto;
  background: #163f8f;
  color: #ffffff;
}

.empty-state {
  min-height: 360px;
  padding: 32px;
  display: grid;
  place-items: center;
  text-align: center;
}
</style>
