"use client"

import { useEffect, useState } from "react"

// Reads a CSS custom property off the element behind `ref` and re-reads it on
// `window` resize. Used by responsive layout hooks (row seconds,
// px-per-second) that ride on Tailwind `sm:`-driven CSS variables — the var
// itself flips at the breakpoint, this hook just reports the current computed
// value back to React.
export function useCssVar(
  ref: React.RefObject<HTMLElement | null>,
  varName: string,
  initial: number,
  parse: (v: string) => number = parseInt,
): number {
  const [value, setValue] = useState(initial)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => {
      const v = getComputedStyle(el).getPropertyValue(varName)
      const n = parse(v)
      if (!Number.isNaN(n) && n > 0) setValue(n)
    }
    update()
    window.addEventListener("resize", update)
    return () => window.removeEventListener("resize", update)
  }, [ref, varName, parse])

  return value
}