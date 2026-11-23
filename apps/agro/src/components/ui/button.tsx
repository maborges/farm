"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { cloneElementWithProps } from "./overlay-utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg md:rounded-sm border border-transparent bg-clip-padding text-sm font-normal whitespace-nowrap transition-[color,background-color,border-color,box-shadow,transform] outline-none select-none cursor-pointer focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:border-primary/50 focus-visible:ring-offset-1 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-100 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "border border-primary/20 bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground active:scale-95 shadow-sm shadow-primary/20 transition-all duration-300 disabled:border-border/70 disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none disabled:hover:border-border/70 disabled:hover:bg-muted disabled:hover:text-muted-foreground disabled:active:scale-100 dark:disabled:border-border dark:disabled:bg-muted/70 dark:disabled:text-muted-foreground",
        outline:
          "border border-border/60 bg-white/45 text-foreground/85 shadow-sm shadow-black/5 hover:border-primary/50 hover:bg-primary/10 hover:text-primary active:scale-95 transition-all duration-300 disabled:border-border/70 disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none disabled:hover:border-border/70 disabled:hover:bg-muted disabled:hover:text-muted-foreground disabled:active:scale-100 dark:border-white/20 dark:bg-white/10 dark:text-foreground dark:hover:border-primary/50 dark:hover:bg-primary/20 dark:hover:text-primary dark:shadow-black/10 dark:disabled:border-border dark:disabled:bg-muted/70 dark:disabled:text-muted-foreground",
        secondary:
          "border border-border/60 bg-white/45 text-secondary-foreground shadow-sm shadow-black/5 hover:border-primary/50 hover:bg-primary/10 hover:text-primary active:scale-95 transition-all duration-300 disabled:border-border/70 disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none disabled:hover:border-border/70 disabled:hover:bg-muted disabled:hover:text-muted-foreground disabled:active:scale-100 dark:border-white/20 dark:bg-white/10 dark:text-foreground dark:hover:border-primary/50 dark:hover:bg-primary/20 dark:hover:text-primary dark:disabled:border-border dark:disabled:bg-muted/70 dark:disabled:text-muted-foreground",
        ghost:
          "text-accent-foreground hover:bg-primary/10 hover:text-primary aria-expanded:bg-primary/15 active:scale-95 transition-all duration-300 disabled:border-transparent disabled:bg-transparent disabled:text-muted-foreground disabled:hover:bg-transparent disabled:hover:text-muted-foreground disabled:active:scale-100 dark:text-foreground dark:hover:bg-primary/20 dark:hover:text-primary dark:disabled:text-muted-foreground",
        destructive:
          "border border-destructive/30 bg-[color-mix(in_oklch,var(--destructive)_10%,var(--background))] text-destructive shadow-sm shadow-destructive/10 hover:border-destructive hover:bg-destructive hover:text-destructive-foreground transition-all duration-300 disabled:border-border/70 disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none disabled:hover:border-border/70 disabled:hover:bg-muted disabled:hover:text-muted-foreground dark:disabled:border-border dark:disabled:bg-muted/70 dark:disabled:text-muted-foreground",
        link: "text-primary underline-offset-4 hover:underline disabled:border-transparent disabled:bg-transparent disabled:text-muted-foreground disabled:hover:bg-transparent disabled:hover:text-muted-foreground",
      },
      size: {
        default: "h-11 md:h-8 gap-1.5 px-3.5 md:px-2.5",
        xs: "h-8 md:h-6 gap-1 px-2.5 md:px-2 text-xs",
        sm: "h-10 md:h-7 gap-1.5 md:gap-1 px-3 md:px-2.5 text-sm md:text-[0.8rem]",
        lg: "h-12 md:h-9 gap-2 md:gap-1.5 px-4 md:px-2.5 text-base md:text-sm",
        icon: "size-11 md:size-8",
        "icon-xs": "size-8 md:size-6",
        "icon-sm": "size-10 md:size-7",
        "icon-lg": "size-12 md:size-9",
      },
    },
    defaultVariants: {
      variant: "outline",
      size: "sm",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, type = "button", children, ...props }, ref) => {
    const mergedClassName = cn(buttonVariants({ variant, size }), className)

    if (asChild && React.isValidElement(children)) {
      // eslint-disable-next-line react-hooks/refs
      return cloneElementWithProps(children, {
        ...props,
        ref,
        "data-slot": "button",
        className: mergedClassName,
      })
    }

    return (
      <button
        ref={ref}
        data-slot="button"
        type={type}
        className={mergedClassName}
        {...props}
      >
        {children}
      </button>
    )
  }
)

Button.displayName = "Button"

export { Button, buttonVariants }
