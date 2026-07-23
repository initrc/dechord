"use client"

import { useRef } from "react"
import { useCssVar } from "@/hooks/use-css-var"

const DEFAULT_ROW_SECONDS = 30
const ROW_SECONDS_VAR = "--row-seconds"
const DEFAULT_PX_PER_SECOND = 22
const PX_PER_SECOND_VAR = "--px-per-second"

export type TimeRow = {
  index: number
  rowStart: number
  rowEnd: number
}

export function buildTimeRows(duration: number, rowSeconds: number): TimeRow[] {
  const rowCount = Math.max(1, Math.ceil(duration / rowSeconds))
  const rows: TimeRow[] = []
  for (let r = 0; r < rowCount; r++) {
    const rowStart = r * rowSeconds
    const rowEnd = Math.min((r + 1) * rowSeconds, duration)
    rows.push({ index: r, rowStart, rowEnd })
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
  const rowSeconds = useCssVar(
    containerRef,
    ROW_SECONDS_VAR,
    DEFAULT_ROW_SECONDS,
  )
  return { containerRef, rowSeconds }
}

// Reads the responsive `--px-per-second` CSS variable off the same container
// as `useRowSeconds`. pxPerSecond drives every width computation in the item
// view (chord squares, waveform canvas, seek math) so the chord track and
// master track stay aligned across viewport changes.
export function usePxPerSecond(
  containerRef: React.RefObject<HTMLDivElement | null>,
): number {
  return useCssVar(
    containerRef,
    PX_PER_SECOND_VAR,
    DEFAULT_PX_PER_SECOND,
  )
}