"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

type MaybeElement = React.ReactElement | undefined | null

function composeEventHandlers<E>(
  theirHandler?: (_event: E) => void,
  ourHandler?: (_event: E) => void
) {
  return (event: E) => {
    theirHandler?.(event)
    ourHandler?.(event)
  }
}

function useControllableState<T>({
  prop,
  defaultProp,
  onChange,
}: {
  prop?: T
  defaultProp: T
  onChange?: (_value: T) => void
}) {
  const [uncontrolled, setUncontrolled] = React.useState(defaultProp)
  const value = prop ?? uncontrolled

  const setValue = React.useCallback(
    (next: T | ((_prev: T) => T)) => {
      const resolved = typeof next === "function" ? (next as (_prev: T) => T)(value) : next
      if (prop === undefined) {
        setUncontrolled(resolved)
      }
      onChange?.(resolved)
    },
    [onChange, prop, value]
  )

  return [value, setValue] as const
}

function useFocusTrap(ref: React.RefObject<HTMLElement | null>, active: boolean) {
  React.useEffect(() => {
    if (!active) return

    const container = ref.current
    if (!container) return

    const focusableSelector = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      "[tabindex]:not([tabindex='-1'])",
    ].join(",")

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return

      const focusable = Array.from(container.querySelectorAll<HTMLElement>(focusableSelector))
      if (focusable.length === 0) {
        event.preventDefault()
        container.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const current = document.activeElement

      if (current === container || !container.contains(current)) {
        event.preventDefault()
        const target = event.shiftKey ? last : first
        target.focus()
        return
      }

      if (event.shiftKey && current === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && current === last) {
        event.preventDefault()
        first.focus()
      }
    }

    container.addEventListener("keydown", handleKeyDown)
    return () => container.removeEventListener("keydown", handleKeyDown)
  }, [active, ref])
}

function cloneElementWithProps<P extends Record<string, unknown>>(
  element: MaybeElement,
  props: P,
  children?: React.ReactNode
) {
  if (!React.isValidElement(element)) return null

  const elementProps = element.props as Record<string, unknown>

  const merged: Record<string, unknown> = {
    ...elementProps,
    ...props,
  }

  if (elementProps.className || props.className) {
    merged.className = cn(
      elementProps.className as string | undefined,
      props.className as string | undefined
    )
  }

  if (elementProps.style || props.style) {
    merged.style = {
      ...(typeof elementProps.style === "object" && elementProps.style ? elementProps.style : {}),
      ...(typeof props.style === "object" && props.style ? props.style : {}),
    }
  }

  for (const key of Object.keys(props)) {
    if (!key.startsWith("on")) continue
    const theirs = elementProps[key]
    const ours = props[key]
    if (typeof theirs === "function" && typeof ours === "function") {
      merged[key] = composeEventHandlers(theirs as (_event: unknown) => void, ours as (_event: unknown) => void)
    }
  }

  if (children !== undefined) {
    merged.children = children
  }

  return React.cloneElement(element, merged)
}

export { cloneElementWithProps, composeEventHandlers, useControllableState, useFocusTrap }
