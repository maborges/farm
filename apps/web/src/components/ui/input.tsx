import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, autoComplete = "off", ...props }: React.ComponentProps<"input">) {
  const localeProps =
    type === "number"
      ? { inputMode: props.inputMode ?? "decimal", lang: props.lang ?? "pt-BR" }
      : { lang: props.lang ?? "pt-BR" }

  return (
    <input
      type={type}
      autoComplete={autoComplete}
      {...localeProps}
      data-slot="input"
      className={cn(
        "h-8 w-full min-w-0 rounded-sm border border-border/60 bg-white/55 px-3 py-1 text-sm font-normal text-foreground shadow-sm shadow-black/5 transition-all duration-300 outline-none placeholder:text-muted-foreground/65 focus-visible:border-primary/60 focus-visible:bg-white/70 focus-visible:ring-4 focus-visible:ring-primary/5 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-muted/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive/20 dark:border-white/20 dark:bg-white/10 dark:text-white dark:shadow-black/10 dark:focus-visible:border-primary/50 dark:focus-visible:bg-white/15 md:text-sm",
        className
      )}
      {...props}
    />
  )
}

export { Input }
