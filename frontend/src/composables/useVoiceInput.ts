import { ref } from 'vue'
import { transcribeVoiceInput } from '../api/apis'

type VoiceInputOptions = {
  onText: (text: string) => void
  onError?: (message: string) => void
}

type BrowserSpeechRecognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onresult: ((event: any) => void) | null
  onerror: ((event: any) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

const getPreferredMimeType = () => {
  if (typeof MediaRecorder === 'undefined') return ''
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/wav'
  ]
  return candidates.find(type => MediaRecorder.isTypeSupported(type)) || ''
}

const getResponseData = (res: any) => res?.data ?? res ?? {}

const extractTranscript = (res: any) => {
  const data = getResponseData(res)
  if (typeof data === 'string') return data.trim()
  const nested = data?.data && typeof data.data === 'object' ? data.data : data
  return String(
    nested?.text ||
    nested?.transcript ||
    nested?.transcription ||
    nested?.content ||
    nested?.result ||
    nested?.message ||
    ''
  ).trim()
}

const getSpeechErrorMessage = (error: any) => {
  const code = error?.error || error?.name
  if (code === 'not-allowed' || code === 'service-not-allowed' || code === 'NotAllowedError') {
    return '麦克风权限被拒绝'
  }
  if (code === 'no-speech') return '没有识别到声音，请再说一次'
  if (code === 'audio-capture') return '无法启动麦克风'
  if (code === 'network') return '语音识别网络异常，请稍后再试'
  return '语音识别失败，请稍后再试'
}

export function useVoiceInput(options: VoiceInputOptions) {
  const isRecording = ref(false)
  const isTranscribing = ref(false)
  const voiceError = ref('')
  let recorder: MediaRecorder | null = null
  let stream: MediaStream | null = null
  let chunks: BlobPart[] = []
  let speechRecognition: BrowserSpeechRecognition | null = null
  let speechFinalText = ''
  let speechHadError = false

  const setError = (message: string) => {
    voiceError.value = message
    options.onError?.(message)
  }

  const cleanupRecorder = () => {
    stream?.getTracks().forEach(track => track.stop())
    stream = null
    recorder = null
    chunks = []
    isRecording.value = false
  }

  const stopSpeechRecognition = () => {
    if (!speechRecognition) return
    try {
      speechRecognition.stop()
    } catch (error) {
      console.warn('停止语音识别失败：', error)
      speechRecognition = null
      isRecording.value = false
    }
  }

  const startSpeechRecognition = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) return false

    speechFinalText = ''
    speechHadError = false
    const recognition = new SpeechRecognition() as BrowserSpeechRecognition
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onresult = event => {
      let finalText = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i]
        if (result?.isFinal) {
          finalText += result[0]?.transcript || ''
        }
      }
      if (finalText.trim()) speechFinalText += finalText
    }

    recognition.onerror = event => {
      speechHadError = true
      console.error('语音识别失败：', event)
      setError(getSpeechErrorMessage(event))
    }

    recognition.onend = () => {
      const text = speechFinalText.trim()
      speechRecognition = null
      isRecording.value = false
      if (text) {
        options.onText(text)
        return
      }
      if (!speechHadError) {
        setError('没有识别到文字，请再说一次')
      }
    }

    try {
      recognition.start()
      speechRecognition = recognition
      isRecording.value = true
      return true
    } catch (error) {
      console.warn('启动浏览器语音识别失败：', error)
      speechRecognition = null
      isRecording.value = false
      return false
    }
  }

  const startRecorderTranscription = async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('当前浏览器不支持语音输入')
      return
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = getPreferredMimeType()
      recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      chunks = []

      recorder.ondataavailable = event => {
        if (event.data?.size) chunks.push(event.data)
      }

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' })
        cleanupRecorder()
        if (!audioBlob.size) {
          setError('没有录到声音，请再试一次')
          return
        }

        isTranscribing.value = true
        try {
          const result = await transcribeVoiceInput(audioBlob)
          const text = extractTranscript(result)
          if (!text) {
            setError('没有识别到文字，请再说一次')
            return
          }
          options.onText(text)
        } catch (error: any) {
          console.error('语音输入转写失败：', error)
          const status = error?.response?.status
          const fallbackMessage = status === 404
            ? '后端语音转写接口不可用，请使用 Chrome 或 Edge 浏览器重试'
            : '语音识别失败，请稍后再试'
          setError(error?.response?.data?.detail || error?.response?.data?.msg || error?.message || fallbackMessage)
        } finally {
          isTranscribing.value = false
        }
      }

      recorder.start()
      isRecording.value = true
    } catch (error: any) {
      cleanupRecorder()
      console.error('语音输入启动失败：', error)
      setError(error?.name === 'NotAllowedError' ? '麦克风权限被拒绝' : '无法启动麦克风')
    }
  }

  const start = async () => {
    voiceError.value = ''
    options.onError?.('')

    if (startSpeechRecognition()) return
    await startRecorderTranscription()
  }

  const stop = () => {
    if (speechRecognition) {
      stopSpeechRecognition()
      return
    }
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
      return
    }
    cleanupRecorder()
  }

  const toggle = () => {
    if (isTranscribing.value) return
    if (isRecording.value) {
      stop()
      return
    }
    void start()
  }

  return {
    isRecording,
    isTranscribing,
    voiceError,
    startVoiceInput: start,
    stopVoiceInput: stop,
    toggleVoiceInput: toggle
  }
}
