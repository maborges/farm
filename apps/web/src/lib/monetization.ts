"use client"

import * as React from "react"

type MonetizationEventName =
  | "monetization_blocked"
  | "monetization_cta_clicked"
  | string

type MonetizationContext = {
  feature?: string
  surface?: string
  requiredTier?: string
  ctaLabel?: string
  reason?: string
  [key: string]: unknown
}

function trackMonetizationEvent(
  _eventName: MonetizationEventName,
  _context: MonetizationContext = {}
) {
  return
}

function useMonetizationPromptTracking(
  enabled: boolean,
  _context: MonetizationContext = {}
) {
  React.useEffect(() => {
    if (!enabled) return
  }, [enabled])
}

export { trackMonetizationEvent, useMonetizationPromptTracking }
