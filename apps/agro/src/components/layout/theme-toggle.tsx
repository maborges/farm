"use client";

import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <Button
      type="button"
      variant="outline"
      size="icon-sm"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label="Alternar tema entre claro e escuro"
      title="Alternar tema"
    >
      <Sun className="size-4 text-amber-400 hidden dark:block" />
      <Moon className="size-4 text-emerald-800 block dark:hidden" />
    </Button>
  );
}
