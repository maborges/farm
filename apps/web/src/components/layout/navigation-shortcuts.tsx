"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function NavigationShortcuts() {
  const router = useRouter();

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
      if (event.altKey && event.shiftKey && event.key.toLowerCase() === "d") {
        event.preventDefault();
        router.push("/dashboard");
      }
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [router]);

  return null;
}

