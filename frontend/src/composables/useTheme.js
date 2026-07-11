import { ref, watchEffect } from 'vue'

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

export function useTheme() {
  const isDark = () => {
    const attr = document.documentElement.getAttribute('data-theme')
    if (attr === 'dark') return true
    if (attr === 'light') return false
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  }

  const toggle = () => {
    // Add transition class for smooth colour change
    document.documentElement.classList.add('theme-transition')
    setTimeout(() => {
      document.documentElement.classList.remove('theme-transition')
    }, 400)

    const dark = isDark()
    theme.value = dark ? 'light' : 'dark'
  }

  const currentTheme = () => theme.value || (isDark() ? 'dark' : 'light')

  return { theme, toggle, isDark, currentTheme }
}
