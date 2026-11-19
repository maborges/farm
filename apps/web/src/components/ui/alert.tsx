import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const alertVariants = cva(
  "relative w-full rounded-sm border px-4 py-3 text-sm [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-3.5 [&>svg]:size-4 [&>svg~*]:pl-7",
  {
    variants: {
      variant: {
        default:
          "border-alert-default-border bg-alert-default-bg text-alert-default-description [&>svg]:text-alert-default-icon",
        info:
          "border-alert-info-border bg-alert-info-bg text-alert-info-description [&>svg]:text-alert-info-icon",
        warning:
          "border-alert-warning-border bg-alert-warning-bg text-alert-warning-description [&>svg]:text-alert-warning-icon",
        success:
          "border-alert-success-border bg-alert-success-bg text-alert-success-description [&>svg]:text-alert-success-icon",
        destructive:
          "border-alert-destructive-border bg-alert-destructive-bg text-alert-destructive-description [&>svg]:text-alert-destructive-icon",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

type AlertVariant = NonNullable<VariantProps<typeof alertVariants>["variant"]>

const Alert = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>
>(({ className, variant, ...props }, ref) => (
  <div
    ref={ref}
    role="alert"
    data-slot="alert"
    data-variant={variant ?? "default"}
    className={cn(alertVariants({ variant }), className)}
    {...props}
  />
))
Alert.displayName = "Alert"

const AlertTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    data-slot="alert-title"
    className={cn(
      "mb-1 font-semibold leading-snug tracking-tight text-alert-title",
      className
    )}
    {...props}
  />
))
AlertTitle.displayName = "AlertTitle"

const AlertDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    data-slot="alert-description"
    className={cn(
      "text-sm leading-relaxed text-alert-description [&_p]:leading-relaxed",
      className
    )}
    {...props}
  />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertTitle, AlertDescription, alertVariants, type AlertVariant }
