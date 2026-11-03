"use client"

import * as React from "react"

type Theme = "light" | "dark" | "system"

type ThemeContextValue = {
  theme: Theme
  resolvedTheme: "light" | "dark"
  setTheme: (theme: Theme) => void
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null)
const STORAGE_KEY = "theme"

function getSystemTheme() {
  if (typeof window === "undefined") return "light"
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return
  const resolved = theme === "system" ? getSystemTheme() : theme
  document.documentElement.classList.toggle("dark", resolved === "dark")
}

function ThemeProvider({
  attribute = "class",
  defaultTheme = "system",
  enableSystem = true,
  children,
}: React.PropsWithChildren<{
  attribute?: "class"
  defaultTheme?: Theme
  enableSystem?: boolean
}>) {
  // Keep the server render and the client's first render identical. Browser
  // preferences are loaded in an effect after hydration.
  const [theme, setThemeState] = React.useState<Theme>(defaultTheme)
  const [systemTheme, setSystemTheme] = React.useState<"light" | "dark">("light")
  const [initialized, setInitialized] = React.useState(false)

  const resolvedTheme = theme === "system" && enableSystem ? systemTheme : theme

  React.useEffect(() => {
    let storedTheme: string | null = null
    try {
      storedTheme = window.localStorage.getItem(STORAGE_KEY)
    } catch {
      // The default theme still works when browser storage is unavailable.
    }
    if (storedTheme === "light" || storedTheme === "dark" || storedTheme === "system") {
      setThemeState(storedTheme)
    }
    setSystemTheme(getSystemTheme())
    setInitialized(true)
  }, [])

  React.useEffect(() => {
    if (!initialized) return
    applyTheme(theme)
    try {
      window.localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // Theme changes remain applied to the current page without browser storage.
    }
  }, [initialized, theme])

  React.useEffect(() => {
    if (!initialized || !enableSystem || theme !== "system") return
    const media = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => {
      const next = media.matches ? "dark" : "light"
      setSystemTheme(next)
      applyTheme("system")
    }
    handleChange()
    media.addEventListener("change", handleChange)
    return () => media.removeEventListener("change", handleChange)
  }, [enableSystem, initialized, theme])

  return (
    <ThemeContext.Provider
      value={{
        theme,
        resolvedTheme: resolvedTheme === "dark" ? "dark" : "light",
        setTheme: setThemeState,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

function useTheme() {
  const context = React.useContext(ThemeContext)
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider.")
  }
  return context
}

export { ThemeProvider, useTheme }
