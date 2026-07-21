"use client"

import { useEffect, useRef, useState } from "react"
import { tickInterval } from "@/lib/timeline"

const DEFAULT_ROW_SECONDS = 30
const ROW_SECONDS_VAR = "--row-seconds"

export type TimeRow = {
  index: number
  rowStart: number
  rowEnd: number
  ticks: number[]
}

export function buildTimeRows(duration: number, rowSeconds: number): TimeRow[] {
  const interval = tickInterval()
  const rowCount = Math.max(1, Math.ceil(duration / rowSeconds))
  const rows: TimeRow[] = []
  for (let r = 0; r < rowCount; r++) {
    const rowStart = r * rowSeconds
    const rowEnd = Math.min((r + 1) * rowSeconds, duration)
    const ticks: number[] = []
    for (let t = rowStart; t <= rowEnd; t += interval) {
      ticks.push(t)
    }
    if (rowEnd !== ticks.at(-1)) {
      ticks.push(rowEnd)
    }
    rows.push({ index: r, rowStart, rowEnd, ticks })
  }
  return rows
}

// Reads the responsive `--row-seconds` CSS variable off the container. Both
// the chord track and master track reuse this so their row boundaries stay
// aligned across viewport changes.
export function useRowSeconds(): {
  containerRef: React.RefObject<HTMLDivElement | null>
  rowSeconds: number
} {
  const containerRef = useRef<HTMLDivElement>(null)
  const [rowSeconds, setRowSeconds] = useState(DEFAULT_ROW_SECONDS)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const update = () => {
      const v = getComputedStyle(el).getPropertyValue(ROW_SECONDS_VAR)
      const n = parseInt(v)
      if (!Number.isNaN(n) && n > 0) setRowSeconds(n)
    }
    update()
    window.addEventListener("resize", update)
    return () => window.removeEventListener("resize", update)
  }, [])

  return { containerRef, rowSeconds }
}