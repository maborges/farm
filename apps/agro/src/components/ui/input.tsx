"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { PasswordInput } from "./password-input";

export const inputBaseClassName =
  "h-11 md:h-8 w-full min-w-0 rounded-lg md:rounded-sm border border-border/60 bg-white/55 px-3 py-1 text-base md:text-sm font-normal text-foreground shadow-sm shadow-black/5 transition-all duration-300 outline-none placeholder:text-muted-foreground/65 focus-visible:border-primary/60 focus-visible:bg-white/70 focus-visible:ring-4 focus-visible:ring-primary/5 disabled:pointer-events-none disabled:cursor-not-allowed disabled:border-border/70 disabled:bg-muted disabled:text-muted-foreground disabled:opacity-100 disabled:shadow-none aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive/20 dark:border-white/20 dark:bg-white/10 dark:text-white dark:shadow-black/10 dark:focus-visible:border-primary/50 dark:focus-visible:bg-white/15 dark:disabled:border-border dark:disabled:bg-muted/70 dark:disabled:text-muted-foreground";

export interface InputProps extends React.ComponentProps<"input"> {
  slotProps?: Record<string, unknown>;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, autoComplete = "off", slotProps: _slotProps, ...props }, ref) => {
    if (type === "password") {
      return <PasswordInput ref={ref} className={className} autoComplete={autoComplete} {...props} />;
    }

    const localeProps =
      type === "number"
        ? { inputMode: props.inputMode ?? "decimal", lang: props.lang ?? "pt-BR" }
        : { lang: props.lang ?? "pt-BR" };

    return (
      <input
        ref={ref}
        type={type}
        autoComplete={autoComplete}
        {...localeProps}
        data-slot="input"
        className={cn(inputBaseClassName, className)}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";

export { Input, PasswordInput };
