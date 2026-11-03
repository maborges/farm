"use client";

import * as React from "react";

type Theme = "light" | "dark";

type ThemeContextValue = {
  theme: Theme;
  resolvedTheme: Theme;
  setTheme: (theme: Theme) => void;
};

const ThemeContext = React.createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "campo-theme";

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function ThemeProvider({
  defaultTheme = "light",
  children,
}: React.PropsWithChildren<{
  defaultTheme?: Theme;
}>) {
  // Keep the server render and the client's first render identical. Load the
  // saved browser preference after hydration to avoid mismatched toggle classes.
  const [theme, setThemeState] = React.useState<Theme>(defaultTheme);
  const [initialized, setInitialized] = React.useState(false);

  React.useEffect(() => {
    let savedTheme: string | null = null;
    try {
      savedTheme = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      // Use the default theme when browser storage is unavailable.
    }
    if (savedTheme === "dark" || savedTheme === "light") {
      setThemeState(savedTheme);
    }
    setInitialized(true);
  }, []);

  React.useEffect(() => {
    if (!initialized) return;
    applyTheme(theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Theme changes still apply for this page when browser storage is blocked.
    }
  }, [initialized, theme]);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        resolvedTheme: theme,
        setTheme: setThemeState,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = React.useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider.");
  }
  return context;
}
