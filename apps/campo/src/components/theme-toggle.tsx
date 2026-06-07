"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/theme-provider";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="inline-flex items-center rounded-sm border border-border bg-card p-1 shadow-sm">
      <button
        type="button"
        onClick={() => setTheme("light")}
        aria-label="Tema claro"
        className={cn(
          "inline-flex size-8 items-center justify-center rounded-sm transition-colors",
          theme === "light"
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        )}
      >
        <Sun className="size-4" />
      </button>
      <button
        type="button"
        onClick={() => setTheme("dark")}
        aria-label="Tema escuro"
        className={cn(
          "inline-flex size-8 items-center justify-center rounded-sm transition-colors",
          theme === "dark"
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        )}
      >
        <Moon className="size-4" />
      </button>
    </div>
  );
}
