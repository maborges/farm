"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export interface TextareaProps
    extends React.TextareaHTMLAttributes<HTMLTextAreaElement> { }

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
    ({ className, ...props }, ref) => {
        return (
            <textarea
                className={cn(
                    "flex min-h-[60px] w-full rounded-sm border border-border/60 bg-white/55 px-3 py-2 text-sm text-foreground shadow-sm shadow-black/5 transition-all duration-300 outline-none placeholder:text-muted-foreground/65 focus-visible:border-primary/60 focus-visible:bg-white/70 focus-visible:ring-4 focus-visible:ring-primary/5 disabled:cursor-not-allowed disabled:bg-muted/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-2 aria-invalid:ring-destructive/20 dark:border-white/20 dark:bg-white/10 dark:text-white dark:focus-visible:border-primary/50 dark:focus-visible:bg-white/15 md:text-sm",
                    className
                )}
                ref={ref}
                {...props}
            />
        )
    }
)
Textarea.displayName = "Textarea"

export { Textarea }
