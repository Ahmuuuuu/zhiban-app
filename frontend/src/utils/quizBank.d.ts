export type QuizOption = {
  key: string
  text: string
}

export type QuizQuestion = {
  id: string
  type: 'choice' | 'short'
  stem: string
  options: QuizOption[]
  answer: string
  explanation: string
}

export type QuizSet = {
  id: string
  sourceId: string
  title: string
  content: string
  fileType: string
  filename: string
  questionCount: number
  questions: QuizQuestion[]
  createdAt: string
}

export const QUIZ_BANK_KEY: string

export function parseQuizQuestions(content: string): QuizQuestion[]

export function looksLikeQuizContent(content: string): boolean

export function upsertQuizSet(payload: {
  id?: string
  sourceId?: string | number
  title?: string
  content?: string
  fileType?: string
  filename?: string
  questions?: QuizQuestion[]
  createdAt?: string
}): QuizSet | null

export function readQuizBank(): QuizSet[]

export function getQuizSet(quizId: string): QuizSet | null
