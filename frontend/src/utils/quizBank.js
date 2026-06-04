const SESSION_KEY = 'zhiban_quiz_sessions'

const uid = prefix => `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`

const readSessions = () => {
  try {
    const data = JSON.parse(localStorage.getItem(SESSION_KEY) || '[]')
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

const writeSessions = sessions => {
  localStorage.setItem(SESSION_KEY, JSON.stringify(sessions))
}

const stripFence = value =>
  String(value || '')
    .trim()
    .replace(/^```(?:json|markdown|md)?\s*/i, '')
    .replace(/```$/i, '')
    .trim()

const normalizeAnswer = value =>
  String(value || '')
    .trim()
    .replace(/^(答案|正确答案|参考答案)[:：]?\s*/i, '')
    .replace(/^[（(]?([A-D])[\)）.、]?\s*$/i, '$1')
    .toUpperCase()

const normalizeQuestion = (item, index) => {
  const rawOptions = item.options || item.choices || item.option || []
  const options = Array.isArray(rawOptions)
    ? rawOptions.map((option, optionIndex) => {
      const text = typeof option === 'string'
        ? option
        : String(option.text || option.content || option.value || '')
      const match = text.match(/^\s*([A-D])[\).、]\s*(.*)$/i)

      return {
        key: String(option.key || option.label || match?.[1] || String.fromCharCode(65 + optionIndex)).toUpperCase(),
        text: match?.[2] || text
      }
    })
    : []

  // 只用字符串类型的值作为题干，跳过 object（如 record 包装格式 {question: {...}}）
  const stem = (() => {
    for (const key of ['stem', 'question', 'content', 'title', 'question_text']) {
      const val = item[key]
      if (typeof val === 'string') return val
    }
    return `第 ${index + 1} 题`
  })()

  const isMulti =
    item.multi ||
    item.is_multi ||
    item.multiple ||
    ['multiple', 'multi', 'checkbox'].includes(String(item.type || item.question_type || '').toLowerCase())

  const rawAnswer = item.answer ?? item.correctAnswer ?? item.correct_answer ?? item.correct ?? ''
  const answerStr = String(rawAnswer || '').trim()
  const hasMultiple = /[,，、]/.test(answerStr) || /^[A-D]{2,}$/i.test(answerStr)

  const multi = isMulti || hasMultiple

  return {
    question_id: item.id || item.question_id || null,
    id: item.id || item.question_id || uid(`question-${index + 1}`),
    type: multi ? 'multiple' : (options.length ? 'choice' : 'short'),
    stem: String(stem).trim(),
    options,
    answer: multi
      ? answerStr.toUpperCase().replace(/[^A-D,]/g, '').split(/[,，、]+/).filter(Boolean).sort().join(',')
      : normalizeAnswer(answerStr),
    multi,
    explanation: String(item.explanation || item.analysis || item.reason || '').trim()
  }
}

const parseJsonQuestions = content => {
  const text = stripFence(content)
  const candidates = [text]
  const arrayMatch = text.match(/\[[\s\S]*\]/)
  const objectMatch = text.match(/\{[\s\S]*\}/)

  if (arrayMatch) candidates.push(arrayMatch[0])
  if (objectMatch) candidates.push(objectMatch[0])

  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate)
      const list = Array.isArray(parsed) ? parsed : parsed.questions || parsed.items || parsed.data || []
      if (Array.isArray(list) && list.length) {
        // 解包 record 包装格式 {record_id, question: {...}} → {...}
        const unwrapped = list.map(item =>
          item.question && typeof item.question === 'object' ? item.question : item
        )
        return unwrapped.map(normalizeQuestion).filter(item => item.stem)
      }
    } catch {
      // Try next candidate.
    }
  }

  return []
}

const parseMarkdownQuestions = content => {
  const text = stripFence(content)
  const blocks = text
    .split(/\n(?=\s*(?:#{1,4}\s*)?(?:第\s*)?\d+\s*[.、）)]|\n-{3,}\n)/)
    .map(block => block.trim())
    .filter(Boolean)

  const sourceBlocks = blocks.length > 1
    ? blocks
    : text.split(/\n{2,}/).map(block => block.trim()).filter(Boolean)

  return sourceBlocks.map((block, index) => {
    const lines = block.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
    const stemLines = []
    const options = []
    let answer = ''
    let explanation = ''

    lines.forEach(line => {
      const optionMatch = line.match(/^(?:[-*]\s*)?([A-D])[\).、]\s*(.+)$/i)
      const answerMatch = line.match(/^(?:[-*]\s*)?(?:答案|正确答案|参考答案|answer)[:：]\s*(.+)$/i)
      const explanationMatch = line.match(/^(?:[-*]\s*)?(?:解析|解释|说明|analysis)[:：]\s*(.+)$/i)

      if (optionMatch) {
        options.push({ key: optionMatch[1].toUpperCase(), text: optionMatch[2].trim() })
        return
      }

      if (answerMatch) {
        answer = answerMatch[1].trim()
        return
      }

      if (explanationMatch) {
        explanation = explanationMatch[1].trim()
        return
      }

      stemLines.push(line.replace(/^#{1,4}\s*/, '').replace(/^(?:第\s*)?\d+\s*[.、）)]\s*/, ''))
    })

    return normalizeQuestion({ stem: stemLines.join('\n'), options, answer, explanation }, index)
  }).filter(item => item.stem && (item.options.length || item.answer))
}

export const parseQuizQuestions = content => {
  const jsonQuestions = parseJsonQuestions(content)
  if (jsonQuestions.length) return jsonQuestions
  return parseMarkdownQuestions(content)
}

export const looksLikeQuizContent = content => {
  const text = String(content || '')
  if (!text.trim()) return false
  if (parseQuizQuestions(text).length > 0) return true
  return /question_type|single_choice|multi_choice|true_false|正确答案|参考答案|答案[:：]|解析[:：]/i.test(text)
}

export const QUIZ_BANK_KEY = SESSION_KEY
export const QUIZ_ATTEMPTS_KEY = 'zhiban_quiz_attempts'

export const upsertQuizSet = payload => {
  const questions = payload.questions || parseQuizQuestions(payload.content)
  if (!questions.length) return null

  const sessionId =
    payload.id ||
    (payload.sourceId ? `quiz-resource-${payload.sourceId}` : uid('quiz'))

  const session = {
    id: sessionId,
    sourceId: payload.sourceId || '',
    sessionId: payload.sessionId || payload.session_id || '',
    title: payload.title || 'AI 生成题目',
    content: payload.content || '',
    fileType: payload.fileType || 'exercise',
    filename: payload.filename || '',
    questionCount: questions.length,
    questions,
    attempts: payload.attempts || [],
    bestScore: payload.bestScore ?? null,
    lastScore: payload.lastScore ?? null,
    lastAttemptAt: payload.lastAttemptAt || '',
    createdAt: payload.createdAt || new Date().toISOString()
  }

  const sessions = readSessions()
  const next = [session, ...sessions.filter(item => item.id !== sessionId && item.sourceId !== session.sourceId)]
  writeSessions(next)
  window.dispatchEvent(new CustomEvent('zhiban-quiz-bank-updated', { detail: session }))
  return session
}

export const readQuizBank = () => readSessions()

export const getQuizSet = quizId => {
  const session = readSessions().find(item => item.id === quizId) || null
  // 清理已缓存的老格式垃圾数据（record 包装 → stem 成了 [object Object]）
  if (session?.questions?.length) {
    const clean = session.questions.filter(q => q.stem && q.stem !== '[object Object]')
    if (clean.length !== session.questions.length) {
      const sessions = readSessions()
      if (clean.length === 0) {
        // 全部损坏，移除整个 session，让上游重新生成
        const next = sessions.filter(s => s.id !== session.id)
        writeSessions(next)
        return null
      }
      session.questions = clean
      session.questionCount = clean.length
      const next = sessions.map(s => s.id === session.id ? session : s)
      writeSessions(next)
    }
  }
  return session
}

const readAttempts = () => {
  try {
    const data = JSON.parse(localStorage.getItem(QUIZ_ATTEMPTS_KEY) || '[]')
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

const writeAttempts = attempts => {
  localStorage.setItem(QUIZ_ATTEMPTS_KEY, JSON.stringify(attempts))
}

export const readQuizAttempts = quizId => {
  const attempts = readAttempts()
  return quizId ? attempts.filter(item => item.quizId === quizId) : attempts
}

export const recordQuizAttempt = payload => {
  const quizId = String(payload.quizId || '')
  if (!quizId) return null

  const attempt = {
    id: uid('attempt'),
    quizId,
    sessionId: payload.sessionId || '',
    title: payload.title || '',
    score: Number(payload.score || 0),
    total: Number(payload.total || 0),
    percent: Number(payload.percent || 0),
    answers: payload.answers || {},
    results: payload.results || {},
    createdAt: new Date().toISOString()
  }

  const attempts = [attempt, ...readAttempts()]
  writeAttempts(attempts)

  const sessions = readSessions()
  const next = sessions.map(session => {
    if (session.id !== quizId) return session
    const sessionAttempts = [attempt, ...(session.attempts || [])]
    const bestScore = Math.max(Number(session.bestScore || 0), attempt.percent)
    return {
      ...session,
      attempts: sessionAttempts,
      bestScore,
      lastScore: attempt.percent,
      lastAttemptAt: attempt.createdAt
    }
  })
  writeSessions(next)
  window.dispatchEvent(new CustomEvent('zhiban-quiz-bank-updated', { detail: getQuizSet(quizId) }))
  return attempt
}
