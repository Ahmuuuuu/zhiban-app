import { ref } from 'vue'
import { transcribeVoiceInput } from '../api/apis'

type VoiceInputOptions = {
  onText: (text: string) => void
  onError?: (message: string) => void
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

export function useVoiceInput(options: VoiceInputOptions) {
  const isRecording = ref(false)
  const isTranscribing = ref(false)
  const voiceError = ref('')
  let recorder: MediaRecorder | null = null
  let stream: MediaStream | null = null
  let chunks: BlobPart[] = []

  const setError = (message: string) => {
    voiceError.value = message
    options.onError?.(message)
  }

  const cleanup = () => {
    stream?.getTracks().forEach(track => track.stop())
    stream = null
    recorder = null
    chunks = []
    isRecording.value = false
  }

  const start = async () => {
    voiceError.value = ''
    options.onError?.('')

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
        cleanup()
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
          setError(error?.response?.data?.detail || error?.response?.data?.msg || error?.message || '语音识别失败，请稍后再试')
        } finally {
          isTranscribing.value = false
        }
      }

      recorder.start()
      isRecording.value = true
    } catch (error: any) {
      cleanup()
      console.error('语音输入启动失败：', error)
      setError(error?.name === 'NotAllowedError' ? '麦克风权限被拒绝' : '无法启动麦克风')
    }
  }

  const stop = () => {
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
      return
    }
    cleanup()
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
