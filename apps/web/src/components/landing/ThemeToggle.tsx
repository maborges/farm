"use client";

import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Sun, Moon } from "lucide-react";
import { useEffect, useState } from "react";

/**
 * Botão premium de alternância de tema para a landing page.
 * Utiliza o hook useTheme do ThemeProvider.
 */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <Button variant="outline" size="sm" className="size-8 rounded-sm p-0" aria-label="Carregando tema">
        <Sun className="size-4 shrink-0 opacity-40" />
      </Button>
    );
  }

  const isDark = theme === "dark";

  return (
    <Button
      variant="outline"
      size="sm"
      className="size-8 rounded-sm p-0 text-primary border-primary/20 hover:border-primary/45"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Alternar tema escuro/claro"
    >
      {isDark ? (
        <Sun className="size-4 shrink-0 transition-all duration-300" />
      ) : (
        <Moon className="size-4 shrink-0 transition-all duration-300" />
      )}
    </Button>
  );
}
