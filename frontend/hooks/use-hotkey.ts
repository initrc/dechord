"use client"

import { useEffect } from "react"
import { isTypingTarget } from "@/lib/keyboard"

// Register a global single-key hotkey. Handles the boilerplate common to app
// shortcuts: ignore already-handled events, repeats, modifier-held combos, and
// keys pressed while typing in a form field. Matched events get
// preventDefault() so the browser doesn't also act on them (e.g. space scrolling
// the page).
export function useHotkey(key: string, onMatch: () => void) {
  useEffect(() => {
    const lower = key.toLowerCase()
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.repeat) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key.toLowerCase() !== lower) return
      if (isTypingTarget(e.target)) return
      e.preventDefault()
      onMatch()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [key, onMatch])
}