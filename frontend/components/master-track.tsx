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

    const secondsPerPx = 1 / pxPerSecond
    const peaksPerPx = Math.max(1, Math.floor(secondsPerPx * peaksPerSecond))
    const mid = MASTER_HEIGHT / 2
    // The peaks array may be slightly shorter than `duration` (encoder
    // quantization, truncation). Stop where buckets actually end so we never
    // read past peaks.length in the inner loop.
    const safeWidth = Math.min(width, peaks.length / peaksPerPx)

    for (let x = 0; x < safeWidth; x++) {
      const startBucket = Math.floor(
        (row.rowStart + x * secondsPerPx) * peaksPerSecond,
      )
      const endBucket = Math.min(startBucket + peaksPerPx, peaks.length)
      let peak = 0
      for (let i = startBucket; i < endBucket; i++) {
        const v = peaks[i] as number
        if (v > peak) peak = v
      }
      const h = Math.max(1, peak * MASTER_HEIGHT * 0.95)
      ctx.fillRect(x, mid - h / 2, 1, h)
    }
  }, [peaks, peaksPerSecond, width, row.rowStart, pxPerSecond, resolvedTheme])

  return (
    <canvas
      ref={canvasRef}
      className="block border border-primary/10"
      style={{ width, height: MASTER_HEIGHT }}
    />
  )
}