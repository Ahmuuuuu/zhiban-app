<template>
  <main class="quiz-runner-page">
    <header class="runner-header">
      <router-link class="soft-btn" :to="backLink">{{ fromPage === 'path' ? '返回学习路径' : '返回题库' }}</router-link>
      <div>
        <p>Quiz</p>
        <h1>{{ quiz?.title || '做题' }}</h1>
      </div>
      <span class="progress">{{ currentIndex + 1 }} / {{ questions.length || 0 }}</span>
    </header>

    <section v-if="loading" class="empty-state">
      <h2>题目加载中...</h2>
    </section>

    <section v-else-if="quiz && questions.length" class="runner-shell">
      <article v-if="!finished" class="question-panel">
        <div class="question-meta">
          <span>第 {{ currentIndex + 1 }} 题</span>
          <span>{{ currentQuestion.multi ? '多选题' : currentQuestion.options?.length ? '选择题' : '简答题' }}</span>
        </div>

        <h2>{{ currentQuestion.stem }}</h2>

        <div v-if="currentQuestion.options?.length" class="options">
          <button
            v-for="option in currentQuestion.options"
            :key="option.key"
            type="button"
            :class="{ selected: isOptionSelected(currentQuestion.id, option.key) }"
            @click="toggleOption(currentQuestion.id, option.key)"
          >
            <strong>{{ option.key }}</strong>
            <span>{{ option.text }}</span>
          </button>
          <small v-if="currentQuestion.multi" class="multi-hint">可多选</small>
        </div>

        <textarea
          v-else
          v-model.trim="answers[currentQuestion.id]"
          placeholder="输入你的答案"
        ></textarea>

        <div v-if="checked[currentQuestion.id]" class="judge" :class="{ wrong: !isCurrentCorrect }">
          <strong>{{ isCurrentCorrect ? '回答正确' : '回答错误' }}</strong>
          <span v-if="!isCurrentCorrect">
            正确答案：{{ currentQuestion.multi ? (currentQuestion.answer || '').split(',').join('、') : currentQuestion.answer || '等待老师判定' }}
          </span>
          <p v-if="currentQuestion.explanation">{{ currentQuestion.explanation }}</p>
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
        <h2 class="score-value">{{ percentScore }}<span>分</span></h2>
        <small class="score-subtitle">答对 {{ score }} / {{ questions.length }} 题</small>
        <div class="score-list">
          <div v-for="(question, index) in questions" :key="question.id">
            <span>第 {{ index + 1 }} 题</span>
            <strong :class="{ wrong: !results[question.id]?.is_correct }">
              {{ results[question.id]?.is_correct ? '正确' : '错误' }}
            </strong>
          </div>
        </div>
        <router-link class="primary-btn" :to="backLink">{{ fromPage === 'path' ? '返回学习路径' : '回到题库' }}</router-link>
      </article>
    </section>

    <section v-else class="empty-state">
      <h2>没有找到这套题</h2>
      <router-link class="primary-btn" :to="backLink">{{ fromPage === 'path' ? '返回学习路径' : '回到题库' }}</router-link>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { submitExamAnswer, completeLearningPathNode } from '../api/apis'
import { getQuizSet, recordQuizAttempt } from '../utils/quizBank'

const route = useRoute()
const quiz = ref(null)
const questions = ref([])
const loading = ref(true)
const currentIndex = ref(0)
const answers = ref({})
const checked = ref({})
const results = ref({})
const finished = ref(false)
const sessionSummary = ref(null)
const runSessionId = ref('')
const fromPage = ref(route.query.from || '')
const nodeId = ref(route.query.nodeId || '')
const routeSessionId = ref(String(route.query.sessionId || ''))

const backLink = computed(() => {
  return fromPage.value === 'path' ? '/learning-path' : { path: '/learning-resources', query: { category: 'quiz' } }
})

onMounted(() => {
  const id = String(route.params.quizId || '')
  const session = getQuizSet(id)
  quiz.value = session
  questions.value = session?.questions || []
  runSessionId.value = routeSessionId.value || session?.sessionId || session?.session_id || `quiz-${id}-${Date.now()}`
  loading.value = false
})

const currentQuestion = computed(() => questions.value[currentIndex.value] || {})

const isOptionSelected = (questionId, key) => {
  const ans = answers.value[questionId]
  return Array.isArray(ans) ? ans.includes(key) : ans === key
}

const toggleOption = (questionId, key) => {
  const q = questions.value.find(q => q.id === questionId)
  if (!q?.multi) {
    answers.value[questionId] = key
    return
  }
  if (!Array.isArray(answers.value[questionId])) {
    answers.value[questionId] = []
  }
  const idx = answers.value[questionId].indexOf(key)
  if (idx > -1) {
    answers.value[questionId].splice(idx, 1)
  } else {
    answers.value[questionId].push(key)
  }
}

const normalizeAnswer = value => {
  if (Array.isArray(value)) return value.map(k => k.toUpperCase().trim()).filter(Boolean).sort().join(',')
  return String(value || '')
    .trim()
    .replace(/^[（(]?([A-D])[\)）.、]?\s*$/i, '$1')
    .toUpperCase()
}

const unwrapData = result => result?.data?.data ?? result?.data ?? result

const getBackendQuestionId = question => {
  const id = Number(question?.question_id || question?.questionId || question?.id)
  return Number.isFinite(id) && id > 0 ? id : null
}

const toCorrectBoolean = value => value === true || value === 1 || value === '1' || String(value).toLowerCase() === 'true'

const checkCurrent = async () => {
  const question = currentQuestion.value
  if (!question?.id) return
  if (checked.value[question.id]) return

  const userAnswer = normalizeAnswer(answers.value[question.id])
  const backendQuestionId = getBackendQuestionId(question)

  if (backendQuestionId && userAnswer) {
    try {
      const result = await submitExamAnswer({
        question_id: backendQuestionId,
        answer: userAnswer,
        time_spent: null,
        session_id: runSessionId.value
      })
      const data = unwrapData(result)
      checked.value[question.id] = true
      results.value[question.id] = {
        is_correct: toCorrectBoolean(data?.is_correct),
        correct_answer: data?.correct_answer || question.answer,
        analysis: data?.analysis || question.explanation || '',
        session_id: data?.session_id || runSessionId.value,
        score: data?.score,
        weight: data?.weight
      }
      if (data?.session_id) {
        runSessionId.value = data.session_id
      }
      if (data?.session_summary) {
        sessionSummary.value = data.session_summary
      }
      return
    } catch (error) {
      console.error('提交答题记录失败，使用本地判分：', error)
    }
  }

  checked.value[question.id] = true
  const correctAnswer = normalizeAnswer(question.answer)
  results.value[question.id] = {
    is_correct: correctAnswer ? userAnswer === correctAnswer : Boolean(userAnswer),
    correct_answer: question.answer,
    analysis: question.explanation || ''
  }
}

const isCurrentCorrect = computed(() => {
  const result = results.value[currentQuestion.value?.id]
  return result !== undefined ? result.is_correct : false
})

const score = computed(() => questions.value.reduce((total, question) => {
  return total + (results.value[question.id]?.is_correct ? 1 : 0)
}, 0))

const percentScore = computed(() => {
  const summaryTotal = Number(sessionSummary.value?.total_questions)
  const summaryMatchesCurrentQuiz = !Number.isFinite(summaryTotal) || summaryTotal <= questions.value.length
  const backendScore = Number(
    sessionSummary.value?.percentage ??
    sessionSummary.value?.earned_points
  )
  if (summaryMatchesCurrentQuiz && Number.isFinite(backendScore)) return backendScore.toFixed(1)

  if (!questions.value.length) return '0.0'
  return ((score.value / questions.value.length) * 100).toFixed(1)
})

const goNext = async () => {
  await checkCurrent()

  if (currentIndex.value >= questions.value.length - 1) {
    finished.value = true
    recordQuizAttempt({
      quizId: quiz.value?.id,
      title: quiz.value?.title,
      score: score.value,
      total: questions.value.length,
      percent: Number(percentScore.value),
      sessionId: runSessionId.value,
      answers: answers.value,
      results: results.value
    })
    if (fromPage.value !== 'path' || !nodeId.value || !runSessionId.value) {
      return
    }
    if (fromPage.value === 'path' && nodeId.value && runSessionId.value) {
      try {
        const completeResult = await completeLearningPathNode(Number(nodeId.value), runSessionId.value)
        window.sessionStorage.setItem('zhiban_path_needs_refresh', '1')
        window.dispatchEvent(new CustomEvent('zhiban-path-node-completed', {
          detail: {
            nodeId: nodeId.value,
            sessionId: runSessionId.value,
            result: unwrapData(completeResult)
          }
        }))
        console.log('[QuizRunner] 节点自动完成成功')
      } catch (e) {
        console.error('[QuizRunner] 自动完成节点失败:', e)
      }
    }
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
  font-family: "Open Sans", "PingFang SC", "Microsoft YaHei", sans-serif;
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
.question-panel h2,
.score-panel h2 {
  margin: 0;
}

.progress,
.soft-btn,
.primary-btn {
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
}

.runner-shell,
.empty-state,
.question-panel,
.score-panel {
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 44px rgba(22, 63, 143, 0.08);
}

.runner-shell {
  padding: 24px;
}

.question-panel,
.score-panel,
.empty-state {
  padding: 28px;
}

.score-panel {
  text-align: center;
}

.score-value {
  color: #163f8f;
  font-size: clamp(58px, 9vw, 112px);
  font-weight: 900;
  line-height: 1;
}

.score-value span {
  margin-left: 8px;
  font-size: clamp(20px, 3vw, 34px);
}

.score-subtitle {
  display: block;
  margin-top: 10px;
  color: #5f8fc3;
  font-size: 15px;
  font-weight: 800;
}

.question-meta,
.runner-actions,
.score-list div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.question-meta {
  margin-bottom: 18px;
  color: #5f8fc3;
  font-weight: 800;
}

.options {
  display: grid;
  gap: 12px;
  margin-top: 22px;
}

.options button {
  width: 100%;
  min-height: 54px;
  padding: 12px 14px;
  border: 1px solid #c9dce9;
  border-radius: 18px;
  background: #fff;
  color: #163f8f;
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  cursor: pointer;
}

.options button.selected {
  border-color: #163f8f;
  background: #edf9fc;
}

.multi-hint {
  display: block;
  margin-top: 6px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

textarea {
  width: 100%;
  min-height: 140px;
  margin-top: 22px;
  padding: 14px;
  border: 1px solid #c9dce9;
  border-radius: 18px;
  color: #163f8f;
  font: inherit;
  resize: vertical;
}

.judge {
  margin-top: 18px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(73, 156, 111, 0.12);
  color: #2f7d57;
}

.judge.wrong {
  background: rgba(178, 65, 65, 0.1);
  color: #b24141;
}

.runner-actions {
  margin-top: 24px;
}

.primary-btn {
  background: #163f8f;
  color: #fff;
}

.score-list {
  display: grid;
  gap: 10px;
  margin: 24px auto;
  max-width: 620px;
  text-align: left;
}

.score-list div {
  min-height: 42px;
  padding: 0 14px;
  border-radius: 16px;
  background: #edf9fc;
}

.wrong {
  color: #b24141;
}

.empty-state {
  min-height: 320px;
  display: grid;
  place-items: center;
  text-align: center;
}
</style>
