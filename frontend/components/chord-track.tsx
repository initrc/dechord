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

// Two-pass: first build all segments across rows with showLabel=false,
// then for each chord that spans multiple rows, show the label only on the
// wider of the two visible parts (by seconds). Chords fully contained in
// one row are unaffected; split chords share the parent's color.
export function buildChordRows(
  chords: DisplayChord[],
  duration: number,
  rowSeconds: number,
): ChordRow[] {
  const rows = buildTimeRows(duration, rowSeconds)
  const colors = chordColorIndices(chords)

  // Pass 1: build all segments, keyed by chord index.
  const segmentsByChord: ChordRowSegment[][] = []
  for (let i = 0; i < chords.length; i++) {
    segmentsByChord.push([])
  }
  let chordIdx = 0
  const result = rows.map((row) => {
    while (chordIdx < chords.length && chords[chordIdx].end <= row.rowStart) {
      chordIdx++
    }
    const segments: ChordRowSegment[] = []
    for (
      let i = chordIdx;
      i < chords.length && chords[i].start < row.rowEnd;
      i++
    ) {
      const chord = chords[i]
      const seg: ChordRowSegment = {
        start: Math.max(chord.start, row.rowStart),
        end: Math.min(chord.end, row.rowEnd),
        label: chord.isSilence ? "" : `${chord.root}${chord.quality}`,
        isSilence: chord.isSilence,
        showLabel: false,
        colorIndex: colors[i],
      }
      segments.push(seg)
      segmentsByChord[i].push(seg)
    }
    return { ...row, segments }
  })

  // Pass 2: for each chord, show the label on its widest segment.
  for (const segs of segmentsByChord) {
    if (segs.length === 0) continue
    let widest = segs[0]
    for (let i = 1; i < segs.length; i++) {
      if (segs[i].end - segs[i].start > widest.end - widest.start) {
        widest = segs[i]
      }
    }
    if (!widest.isSilence) {
      widest.showLabel = true
    }
  }

  return result
}

export function ChordTrackRow({
  row,
  pxPerSecond,
}: {
  row: ChordRow
  pxPerSecond: number
}) {
  const width = secondsToPx(row.rowEnd - row.rowStart, pxPerSecond)
  return (
    <div className="flex" style={{ width, height: CHORD_HEIGHT }}>
      {row.segments.map((seg, j) => {
        const segWidth = secondsToPx(seg.end - seg.start, pxPerSecond)
        const borderClass = j === 0 ? "border-l border-r border-t" : "border-r border-t"
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