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
  const [theme, setThemeState] = React.useState<Theme>(() => {
    if (typeof window === "undefined") return defaultTheme
    return (window.localStorage.getItem(STORAGE_KEY) as Theme | null) ?? defaultTheme
  })

  const [systemTheme, setSystemTheme] = React.useState<"light" | "dark">(() =>
    getSystemTheme()
  )

  const resolvedTheme = theme === "system" && enableSystem ? systemTheme : theme

  React.useEffect(() => {
    applyTheme(theme)
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, theme)
    }
  }, [theme])

  React.useEffect(() => {
    if (!enableSystem || theme !== "system") return
    const media = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => {
      const next = media.matches ? "dark" : "light"
      setSystemTheme(next)
      applyTheme("system")
    }
    media.addEventListener("change", handleChange)
    return () => media.removeEventListener("change", handleChange)
  }, [enableSystem, theme])

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
