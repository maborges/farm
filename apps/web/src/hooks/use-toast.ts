"use client"

import { useCallback } from "react"
import { toast as sonnerToast } from "sonner"

type ToastOptions = {
  title?: string
  description?: React.ReactNode | string
  variant?: "default" | "destructive" | "success"
  action?: {
    label: string
    onClick: () => void
  }
  duration?: number
}

function useToast() {
  const toast = useCallback(({ title, description, variant = "default", action, duration }: ToastOptions) => {
    if (variant === "destructive") {
      return sonnerToast.error(title ?? "Erro", {
        description,
        action,
        duration,
      })
    }

    if (variant === "success") {
      return sonnerToast.success(title ?? "Sucesso", {
        description,
        action,
        duration,
      })
    }

    return sonnerToast(title ?? "", {
      description,
      action,
      duration,
    })
  }, [])

  return { toast }
}

export { useToast }
