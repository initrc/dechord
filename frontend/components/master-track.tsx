"use client"

import { useEffect, useRef } from "react"
import { useTheme } from "next-themes"
import { secondsToPx } from "@/lib/timeline"
import type { TimeRow } from "@/lib/layout"

export const MASTER_HEIGHT = 40

// One row's waveform (a thin peak-per-pixel canvas). Pixels map 1:1 to seconds
// via the shared `secondsToPx` helper, so the canvas width always equals
// `secondsToPx(rowEnd - rowStart)` and aligns with the chord row above it.
export function MasterTrackRow({
  row,
  peaks,
  peaksPerSecond,
  pxPerSecond,
}: {
  row: TimeRow
  peaks: Float32Array | null
  peaksPerSecond: number
  pxPerSecond: number
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { resolvedTheme } = useTheme()
  const width = secondsToPx(row.rowEnd - row.rowStart, pxPerSecond)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.floor(width * dpr)
    canvas.height = Math.floor(MASTER_HEIGHT * dpr)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, width, MASTER_HEIGHT)

    if (!peaks || peaksPerSecond <= 0) return

    // Read --chart-2 off the canvas so the waveform inherits the active theme.
    // The preset defines it as an oklch() string (see globals.css), which
    // canvas fillStyle accepts natively — no wrapping needed.
    const cssVar = getComputedStyle(canvas).getPropertyValue("--chart-2").trim()
    ctx.fillStyle = cssVar || "currentColor"

    const gapWidth = 1
    const barWidth = 2
    const stepWidth = gapWidth + barWidth  // 3px per bar, gap first, then gap at the end of the row
    const numBars = Math.max(1, Math.floor((width - gapWidth) / stepWidth))
    const secondsPerBar = (row.rowEnd - row.rowStart) / numBars
    const peaksPerBar = Math.max(1, Math.floor(secondsPerBar * peaksPerSecond))
    const mid = MASTER_HEIGHT / 2

    for (let i = 0; i < numBars; i++) {
      const startBucket = Math.floor(
        (row.rowStart + i * secondsPerBar) * peaksPerSecond,
      )
      // The peaks array may be slightly shorter than `duration` (encoder
      // quantization, truncation). Stop when we run past the array so we
      // never read past peaks.length in the inner loop.
      if (startBucket >= peaks.length) break
      const endBucket = Math.min(startBucket + peaksPerBar, peaks.length)
      let peak = 0
      for (let j = startBucket; j < endBucket; j++) {
        const v = peaks[j] as number
        if (v > peak) peak = v
      }
      const h = Math.max(barWidth, peak * MASTER_HEIGHT * 0.95)
      const x = i * stepWidth + gapWidth
      const y = mid - h / 2
      const radius = Math.min(1, h / 2)
      ctx.globalAlpha = 0.3 + peak * 0.7
      ctx.beginPath()
      ctx.roundRect(x, y, barWidth, h, radius)
      ctx.fill()
    }
  }, [peaks, peaksPerSecond, width, row.rowStart, row.rowEnd, pxPerSecond, resolvedTheme])

  return (
    <canvas
      ref={canvasRef}
      className="block"
      style={{ width, height: MASTER_HEIGHT }}
    />
  )
}
