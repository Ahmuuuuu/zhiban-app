import { computed, ref, watchEffect } from 'vue'

const STORAGE_KEY = 'zhiban-theme'
const theme = ref(localStorage.getItem(STORAGE_KEY) || '')

function applyTheme(value) {
  const html = document.documentElement
  if (value) {
    html.setAttribute('data-theme', value)
  } else {
    html.removeAttribute('data-theme')
  }
}

// Apply on init
applyTheme(theme.value)

// Watch & persist
watchEffect(() => {
  applyTheme(theme.value)
  if (theme.value) {
    localStorage.setItem(STORAGE_KEY, theme.value)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
})

// reactive — re-evaluates when theme ref or DOM attribute changes
const isDark = computed(() => {
  // trigger re-compute by reading theme ref
  const val = theme.value
  if (val === 'dark') return true
  if (val === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
})

const currentTheme = computed(() => theme.value || (isDark.value ? 'dark' : 'light'))

export function useTheme() {
  const toggle = () => {
    // Add transition class for smooth colour change
    document.documentElement.classList.add('theme-transition')
    setTimeout(() => {
      document.documentElement.classList.remove('theme-transition')
    }, 400)

    theme.value = isDark.value ? 'light' : 'dark'
  }

  return { theme, toggle, isDark, currentTheme }
}
