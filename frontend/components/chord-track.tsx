"use client"

import { type DisplayChord } from "@/lib/chords"
import { secondsToPx } from "@/lib/timeline"
import { buildTimeRows, type TimeRow } from "@/lib/layout"

export const CHORD_HEIGHT = 40

export type ChordRowSegment = {
  start: number
  end: number
  label: string
  isSilence: boolean
  showLabel: boolean
  colorIndex: number
}

const CHORD_COLORS = ["bg-primary/10", "bg-primary/5"]
const SILENCE_COLOR = "bg-muted/10"
const CHORD_BORDER_COLOR = "border-primary/10"

function segmentColor(seg: ChordRowSegment): string {
  if (seg.isSilence) return SILENCE_COLOR
  return CHORD_COLORS[seg.colorIndex % 2]
}

// Per-chord color index (silence chords share the -1 sentinel). Computed once
// so split parts of a cross-row chord inherit the same color.
function chordColorIndices(chords: DisplayChord[]): number[] {
  let idx = 0
  return chords.map((c) => (c.isSilence ? -1 : idx++))
}

export type ChordRow = TimeRow & { segments: ChordRowSegment[] }

// Sliding-window pass over sorted chords, matching each chord to the row(s)
// it overlaps. Crosses-row chords are split; the first part keeps the label,
// the second part is blank but inherits the parent's color.
export function buildChordRows(
  chords: DisplayChord[],
  duration: number,
  rowSeconds: number,
): ChordRow[] {
  const rows = buildTimeRows(duration, rowSeconds)
  const colors = chordColorIndices(chords)
  let chordIdx = 0
  return rows.map((row) => {
    while (chordIdx < chords.length && chords[chordIdx].end <= row.rowStart) {
      chordIdx++
    }
    const segments: ChordRowSegment[] = []
    for (let i = chordIdx; i < chords.length && chords[i].start < row.rowEnd; i++) {
      const chord = chords[i]
      segments.push({
        start: Math.max(chord.start, row.rowStart),
        end: Math.min(chord.end, row.rowEnd),
        label: chord.isSilence ? "" : `${chord.root}${chord.quality}`,
        isSilence: chord.isSilence,
        showLabel: !chord.isSilence && chord.start >= row.rowStart,
        colorIndex: colors[i],
      })
    }
    return { ...row, segments }
  })
}

export function ChordTrackRow({ row }: { row: ChordRow }) {
  const width = secondsToPx(row.rowEnd - row.rowStart)
  return (
    <div className="flex" style={{ width, height: CHORD_HEIGHT }}>
      {row.segments.map((seg, j) => {
        const segWidth = secondsToPx(seg.end - seg.start)
        const borderClass = j === 0 ? "border-l border-r border-y" : "border-r border-y"
        return (
          <div
            key={j}
            className={`flex shrink-0 items-center justify-center overflow-hidden ${borderClass} ${CHORD_BORDER_COLOR} text-xs ${segmentColor(seg)}`}
            style={{ width: segWidth }}
            title={seg.label}
          >
            {seg.showLabel && <span className="px-1">{seg.label}</span>}
          </div>
        )
      })}
    </div>
  )
}