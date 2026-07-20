"use client"

import { useEffect, useRef, useState } from "react"
import { type DisplayChord } from "@/lib/chords"
import { formatTime, secondsToPx, tickInterval } from "@/lib/timeline"

const CHORD_HEIGHT = 40
const AXIS_HEIGHT = 20

const CHORD_COLORS = ["bg-primary/10", "bg-primary/5"]
const SILENCE_COLOR = "bg-muted/10"
const CHORD_BORDER_COLOR = "border-primary/10"

type RowSegment = {
  start: number
  end: number
  label: string
  isSilence: boolean
  showLabel: boolean
  colorIndex: number
}

type Row = {
  rowStart: number
  rowEnd: number
  segments: RowSegment[]
  ticks: number[]
}

function buildRows(chords: DisplayChord[], duration: number, rowSeconds: number): Row[] {
  const interval = tickInterval()
  const rows: Row[] = []
  const rowCount = Math.ceil(duration / rowSeconds)

  // Precompute color indices for non-silence chords
  let colorIdx = 0
  const chordColors = chords.map(c => (c.isSilence ? -1 : colorIdx++))

  // Chords are pre-sorted by start time (backend _stitch guarantees this).
  // Use a sliding window pointer to avoid re-scanning all chords per row.
  let chordIdx = 0

  for (let r = 0; r < rowCount; r++) {
    const rowStart = r * rowSeconds
    const rowEnd = Math.min((r + 1) * rowSeconds, duration)

    // Advance past chords that end before this row
    while (chordIdx < chords.length && chords[chordIdx].end <= rowStart) {
      chordIdx++
    }

    // Collect chords that overlap this row (contiguous data → no gaps between them)
    const segments: RowSegment[] = []
    for (let i = chordIdx; i < chords.length && chords[i].start < rowEnd; i++) {
      const chord = chords[i]
      segments.push({
        start: Math.max(chord.start, rowStart),
        end: Math.min(chord.end, rowEnd),
        label: chord.isSilence ? "" : `${chord.root}${chord.quality}`,
        isSilence: chord.isSilence,
        showLabel: !chord.isSilence && chord.start >= rowStart,
        colorIndex: chordColors[i],
      })
    }

    // Build tick positions (time axis labels).
    const ticks: number[] = []
    for (let t = rowStart; t <= rowEnd; t += interval) {
      ticks.push(t)
    }
    // Last tick of the song likely doesn't fall on an interval.
    if (rowEnd !== ticks.at(-1)) {
      ticks.push(rowEnd)
    }

    rows.push({ rowStart, rowEnd, segments, ticks })
  }

  return rows
}

function segmentColor(seg: RowSegment): string {
  if (seg.isSilence) return SILENCE_COLOR
  return CHORD_COLORS[seg.colorIndex % 2]
}

export function ChordTrack({
  chords,
  duration,
}: {
  chords: DisplayChord[]
  duration: number
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [rowSeconds, setRowSeconds] = useState(30)

  useEffect(() => {
    const updateRowSeconds = () => {
      if (containerRef.current) {
        const value = getComputedStyle(containerRef.current).getPropertyValue("--row-seconds")
        setRowSeconds(parseInt(value) || 30)
      }
    }
    updateRowSeconds()
    window.addEventListener("resize", updateRowSeconds)
    return () => window.removeEventListener("resize", updateRowSeconds)
  }, [])

  const rows = buildRows(chords, duration, rowSeconds)

  return (
    <div ref={containerRef} className="[--row-seconds:15] sm:[--row-seconds:30] flex flex-col gap-2">
      {rows.map((row, i) => (
        <div key={i} style={{ width: secondsToPx(row.rowEnd - row.rowStart) }}>
          <div className="flex" style={{ height: CHORD_HEIGHT }}>
            {row.segments.map((seg, j) => {
              const width = secondsToPx(seg.end - seg.start)
              const borderClass = j === 0 ? "border-l border-r border-y" : "border-r border-y"
              return (
                <div
                  key={j}
                  className={`flex shrink-0 items-center justify-center overflow-hidden ${borderClass} ${CHORD_BORDER_COLOR} text-xs ${segmentColor(seg)}`}
                  style={{ width }}
                  title={seg.label}
                >
                  {seg.showLabel && (
                    <span className="px-1">{seg.label}</span>
                  )}
                </div>
              )
            })}
          </div>
          <div className="relative" style={{ height: AXIS_HEIGHT }}>
            {row.ticks.map((t, j) => {
              const isFirst = j === 0
              const isLast = j === row.ticks.length - 1
              const translateClass = isFirst
                ? ""
                : isLast
                  ? "-translate-x-full"
                  : "-translate-x-1/2"
              const displayTime = isLast && i === rows.length - 1 ? Math.ceil(t) : t
              return (
                <span
                  key={t}
                  className={`absolute top-0.5 ${translateClass} text-[10px] text-muted-foreground`}
                  style={{ left: secondsToPx(t - row.rowStart) }}
                >
                  {formatTime(displayTime)}
                </span>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
