import { generateExamQuestions } from '../api/apis'

const SESSION_KEY = 'zhiban_quiz_sessions'

function readSessions() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || '[]')
  } catch {
    return []
  }
}

function writeSessions(sessions) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(sessions))
}

/** 将后端题目格式转为前端期望的格式 */
function toFrontendQuestion(q) {
  const optionLabels = Array.isArray(q.options) ? q.options : []
  const options = optionLabels.map((opt, i) => {
    const match = String(opt).match(/^\s*([A-D])[\).、]?\s*(.*)$/)
    return {
      key: match?.[1]?.toUpperCase() || String.fromCharCode(65 + i),
      text: match?.[2] || String(opt),
    }
  })

  return {
    id: q.question_id,
    type: ['single_choice', 'multi_choice', 'true_false'].includes(q.question_type) ? 'choice' : 'short',
    stem: q.content,
    options,
    answer: Array.isArray(q.answer)
      ? q.answer.map(a => String(a).replace(/^([A-D])[\).、]?\s*$/, '$1')).join(',')
      : String(q.answer || '').replace(/^([A-D])[\).、]?\s*$/, '$1'),
    explanation: q.analysis || '',
    question_type: q.question_type,
  }
}

export const QUIZ_BANK_KEY = SESSION_KEY

/**
 * 调用后端 API 生成题目，并记录会话到本地索引
 * 返回 session 对象（questions 字段可能在 API 返回后填充）
 */
export async function upsertQuizSet(payload) {
  const sessionId =
    payload.id || `session-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`

  const session = {
    id: sessionId,
    sourceId: payload.sourceId || '',
    title: payload.title || 'AI 生成题目',
    content: payload.content || '',
    fileType: payload.fileType || 'exercise',
    filename: payload.filename || '',
    questionCount: 0,
    questions: [],
    createdAt: new Date().toISOString(),
  }

  // 先写入占位
  const sessions = readSessions()
  const next = [session, ...sessions.filter(s => s.id !== sessionId)]
  writeSessions(next)

  try {
    const res = await generateExamQuestions({
      topic: payload.title || '练习题',
      count: 5,
      difficulty: 'medium',
      question_types: 'single_choice',
    })
    const apiQuestions = Array.isArray(res?.data) ? res.data : []
    session.questions = apiQuestions.map(toFrontendQuestion)
    session.questionCount = session.questions.length

    // 持久化更新
    const all = readSessions()
    const idx = all.findIndex(s => s.id === sessionId)
    if (idx !== -1) all[idx] = session
    writeSessions(all)
  } catch (err) {
    console.error('生成题目失败：', err)
  }

  window.dispatchEvent(new CustomEvent('zhiban-quiz-bank-updated', { detail: session }))
  return session
}

/** 读取本地会话索引（同步，仅含元数据） */
export function readQuizBank() {
  return readSessions()
}

/** 按 ID 获取会话（含 questions，如 API 尚未返回则为空数组） */
export function getQuizSet(quizId) {
  return readSessions().find(s => s.id === quizId) || null
}
