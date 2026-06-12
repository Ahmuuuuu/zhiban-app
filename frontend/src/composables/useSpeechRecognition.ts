import { ref, onUnmounted } from "vue"

const SpeechRecognitionAPI =
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

export function useSpeechRecognition(lang = "zh-CN") {
  const listening = ref(false)
  const error = ref("")
  const interim = ref("")
  const supported = !!SpeechRecognitionAPI

  let recognition: any = null
  let resolvePromise: ((text: string) => void) | null = null
  let rejectPromise: ((e: Error) => void) | null = null

  const teardown = () => {
    resolvePromise = null
    rejectPromise = null
    listening.value = false
    interim.value = ""
  }

  const stop = () => {
    if (recognition) {
      try { recognition.stop() } catch { /* already stopped */ }
    }
    if (rejectPromise) {
      rejectPromise(new Error("用户取消"))
    }
    teardown()
  }

  const start = (): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!supported) {
        reject(new Error("浏览器不支持语音识别，请使用 Chrome 或 Edge"))
        return
      }

      // 每次 start 建新实例，避免复用导致的事件错乱
      recognition = new SpeechRecognitionAPI()
      recognition.lang = lang
      recognition.interimResults = true
      recognition.continuous = false
      recognition.maxAlternatives = 1

      resolvePromise = resolve
      rejectPromise = reject
      error.value = ""
      interim.value = ""

      recognition.onresult = (event: any) => {
        let finalTranscript = ""
        let interimTranscript = ""
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i]
          if (result.isFinal) {
            finalTranscript += result[0].transcript
          } else {
            interimTranscript += result[0].transcript
          }
        }
        if (interimTranscript) interim.value = interimTranscript
        if (finalTranscript) {
          resolvePromise?.(finalTranscript)
          recognition?.stop()
          teardown()
        }
      }

      recognition.onerror = (event: any) => {
        console.warn("[语音] 识别错误:", event.error, event.message)
        const msg =
          event.error === "no-speech" ? "未检测到语音，请再试一次" :
          event.error === "not-allowed" ? "请授权麦克风权限后重试" :
          event.error === "aborted" ? "" :
          event.error === "audio-capture" ? "未找到麦克风设备" :
          event.error === "network" ? "语音识别需要网络连接" :
          `语音识别失败`
        if (msg) {
          error.value = msg
          setTimeout(() => { error.value = "" }, 3000)
        }
        rejectPromise?.(new Error(msg || event.error))
        teardown()
      }

      recognition.onend = () => {
        // onend 在 onresult(final) 或 onerror 之后触发，做兜底清理
        if (resolvePromise) {
          // 没有拿到任何 final 结果就结束了（比如没有说话）
          if (interim.value) {
            resolvePromise(interim.value)
          } else {
            resolvePromise("")
          }
        }
        teardown()
      }

      // SpeechRecognition 自带权限弹窗，直接 start 即可
      try {
        recognition.start()
        listening.value = true
      } catch (e: any) {
        console.warn("[语音] start 失败:", e)
        error.value = "语音功能需要 Chrome/Edge 浏览器"
        setTimeout(() => { error.value = "" }, 3000)
        reject(e)
        teardown()
      }
    })
  }

  onUnmounted(() => {
    stop()
  })

  return { listening, error, interim, supported, start, stop }
}
