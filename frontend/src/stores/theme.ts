import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', () => {
  const storedTheme = (() => { try { return localStorage.getItem('theme') } catch { return null } })()
  const isDark = ref(storedTheme !== 'light')

  function applyTheme() {
    document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
    try { localStorage.setItem('theme', isDark.value ? 'dark' : 'light') } catch { /* ignore */ }
  }

  function toggleTheme() {
    isDark.value = !isDark.value
    applyTheme()
  }

  // Apply on init
  applyTheme()

  return { isDark, toggleTheme }
})
