"use client";

import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label="Alternar tema entre claro e escuro"
      title="Alternar tema"
      className="w-10 h-10 rounded-lg flex items-center justify-center text-foreground/80 hover:text-foreground hover:bg-muted active:scale-95 transition-all"
    >
      <Sun className="w-5 h-5 text-amber-400 hidden dark:block" />
      <Moon className="w-5 h-5 text-emerald-800 block dark:hidden" />
    </button>
  );
}
