import { useEffect, useState } from 'react'

export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.classList.contains('dark') ? 'dark' : 'light')
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#121722' : '#f5f6fa')
    try { localStorage.setItem('videomaker.theme.v1', theme) } catch { /* Browsing without storage still supports themes. */ }
  }, [theme])
  return { theme, toggleTheme: () => setTheme(current => current === 'light' ? 'dark' : 'light') }
}
