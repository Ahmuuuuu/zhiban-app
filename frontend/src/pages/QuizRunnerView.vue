<template>
  <main class="quiz-runner-page">
    <header class="runner-header">
      <router-link class="soft-btn" to="/question-bank">返回题库</router-link>
      <div>
        <p>Quiz</p>
        <h1>{{ quiz?.title || '做题' }}</h1>
      </div>
      <span class="progress">{{ currentIndex + 1 }} / {{ questions.length }}</span>
    </header>

    <section v-if="loading" class="empty-state">
      <h2>题目加载中...</h2>
    </section>

    <section v-else-if="quiz && questions.length" class="runner-shell">
      <article v-if="!finished" class="question-panel">
        <div class="question-meta">
          <span>第 {{ currentIndex + 1 }} 题</span>
          <span>{{ currentQuestion.options?.length ? '选择题' : '简答题' }}</span>
        </div>

        <h2>{{ currentQuestion.stem }}</h2>

        <div v-if="currentQuestion.options?.length" class="options">
          <button
            v-for="option in currentQuestion.options"
            :key="option.key"
            type="button"
            :class="{ selected: answers[currentQuestion.id] === option.key }"
            @click="answers[currentQuestion.id] = option.key"
          >
            <strong>{{ option.key }}</strong>
            <span>{{ option.text }}</span>
          </button>
        </div>

        <textarea
          v-else
          v-model.trim="answers[currentQuestion.id]"
          placeholder="输入你的答案"
        ></textarea>

        <div v-if="checked[currentQuestion.id]" class="judge" :class="{ wrong: !isCurrentCorrect }">
          <strong>{{ isCurrentCorrect ? '回答正确' : '回答错误' }}</strong>
          <span v-if="!isCurrentCorrect">正确答案：{{ results[currentQuestion.id]?.correct_answer || currentQuestion.answer || '等待老师判定' }}</span>
          <p v-if="!isCurrentCorrect && (results[currentQuestion.id]?.analysis || currentQuestion.explanation)">{{ results[currentQuestion.id]?.analysis || currentQuestion.explanation }}</p>
        </div>

        <footer class="runner-actions">
          <button type="button" class="soft-btn" :disabled="currentIndex === 0" @click="currentIndex -= 1">上一题</button>
          <button type="button" class="soft-btn" @click="checkCurrent">判断对错</button>
          <button type="button" class="primary-btn" @click="goNext">
            {{ currentIndex === questions.length - 1 ? '交卷' : '下一题' }}
          </button>
        </footer>
      </article>

      <article v-else class="score-panel">
        <p>总分</p>
        <h2>{{ score }} / {{ questions.length }}</h2>
        <div class="score-list">
          <div v-for="(question, index) in questions" :key="question.id">
            <span>第 {{ index + 1 }} 题</span>
            <strong :class="{ wrong: !results[question.id]?.is_correct }">{{ results[question.id]?.is_correct ? '正确' : (results[question.id] !== undefined ? '错误' : '未作答') }}</strong>
          </div>
        </div>
        <router-link class="primary-btn" to="/question-bank">回到题库</router-link>
      </article>
    </section>

    <section v-else class="empty-state">
      <h2>没有找到这套题</h2>
      <router-link class="primary-btn" to="/question-bank">回到题库</router-link>
    </section>
  </main>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getQuizSet } from '../utils/quizBank'
import { submitExamAnswer } from '../api/apis'

const route = useRoute()
const quiz = ref(null)
const questions = ref([])
const loading = ref(true)
const currentIndex = ref(0)
const answers = ref({})
const checked = ref({})
const results = ref({}) // { questionId: { is_correct, correct_answer, analysis } }
const finished = ref(false)

onMounted(async () => {
  const id = String(route.params.quizId || '')
  let session = getQuizSet(id)

  // 如题目尚未生成完成，轮询等待（最多 10 秒）
  if (session && !session.questions?.length) {
    for (let i = 0; i < 10; i++) {
      await new Promise(r => setTimeout(r, 1000))
      session = getQuizSet(id)
      if (session?.questions?.length) break
    }
  }

  quiz.value = session
  questions.value = session?.questions || []
  loading.value = false
})

const currentQuestion = computed(() => questions.value[currentIndex.value] || {})

// 记录开始时间用于 time_spent
const startTime = ref(Date.now())

const checkCurrent = async () => {
  const q = currentQuestion.value
  if (!q?.id) return
  checked.value[q.id] = true

  // 提交答案到后端，用后端返回的评判结果
  try {
    const res = await submitExamAnswer({
      question_id: q.id,
      answer: answers.value[q.id] || '',
      time_spent: Math.round((Date.now() - startTime.value) / 1000),
    })
    const data = res?.data || res
    if (data) {
      results.value[q.id] = {
        is_correct: data.is_correct,
        correct_answer: data.correct_answer || q.answer,
        analysis: data.analysis || q.explanation || '',
      }
    }
  } catch (err) {
    console.error('提交答案失败：', err)
  }
}

const isCurrentCorrect = computed(() => {
  const r = results.value[currentQuestion.value?.id]
  return r !== undefined ? r.is_correct : false
})

const score = computed(() => {
  let total = 0
  for (const q of questions.value) {
    const r = results.value[q.id]
    if (r?.is_correct) total += 1
  }
  return total
})

const goNext = async () => {
  await checkCurrent()

  if (currentIndex.value >= questions.value.length - 1) {
    finished.value = true
    return
  }

  currentIndex.value += 1
}
</script>

<style scoped>
.quiz-runner-page {
  min-height: 100vh;
  padding: 30px 36px;
  background:
    radial-gradient(ellipse 72% 44% at 10% 0%, rgba(209, 244, 250, 0.46), transparent 70%),
    linear-gradient(135deg, #fafafa 0%, rgb(237, 249, 252) 52%, #fafafa 100%);
  color: #163f8f;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.runner-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 18px;
  margin-bottom: 28px;
}

.runner-header p,
.score-panel p {
  margin: 0 0 4px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.runner-header h1,
.score-panel h2 {
  margin: 0;
  font-size: 30px;
}

.progress {
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  background: #c9dce9;
  display: inline-flex;
  align-items: center;
  font-weight: 900;
}

.runner-shell,
.empty-state {
  max-width: 920px;
  margin: 0 auto;
}

.question-panel,
.score-panel,
.empty-state {
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 18px 44px rgba(22, 63, 143, 0.08);
}

.question-panel,
.score-panel {
  padding: 24px;
}

.question-meta {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.question-meta span {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #c9dce9;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 900;
}

.question-panel h2 {
  margin: 0 0 20px;
  font-size: 22px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.options {
  display: grid;
  gap: 12px;
}

.options button {
  min-height: 54px;
  padding: 12px 14px;
  border: 1px solid #c9dce9;
  border-radius: 16px;
  background: #ffffff;
  color: #163f8f;
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.options button.selected {
  border-color: #163f8f;
  box-shadow: 0 0 0 3px rgba(22, 63, 143, 0.12);
}

.options strong {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #163f8f;
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

textarea {
  width: 100%;
  min-height: 140px;
  padding: 14px;
  border: 1px solid #c9dce9;
  border-radius: 16px;
  color: #163f8f;
  font: inherit;
  resize: vertical;
}

.judge {
  margin-top: 16px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(34, 197, 94, 0.12);
  color: #166534;
}

.judge.wrong {
  background: rgba(239, 68, 68, 0.1);
  color: #991b1b;
}

.judge p {
  margin: 8px 0 0;
  line-height: 1.7;
}

.runner-actions {
  margin-top: 22px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.soft-btn,
.primary-btn {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid rgba(22, 63, 143, 0.2);
  border-radius: 18px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.soft-btn {
  background: #ffffff;
  color: #163f8f;
}

.primary-btn {
  background: #163f8f;
  color: #ffffff;
}

.soft-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.score-list {
  margin: 22px 0;
  display: grid;
  gap: 10px;
}

.score-list div {
  min-height: 42px;
  padding: 0 14px;
  border-radius: 14px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.score-list strong {
  color: #166534;
}

.score-list strong.wrong {
  color: #991b1b;
}

.empty-state {
  min-height: 360px;
  padding: 32px;
  display: grid;
  place-items: center;
  text-align: center;
}
</style>
