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
// then for each chord that spans multiple rows, show the label on the
// first part if it is wide enough (in pixels) to fit the label text; otherwise
// fall back to the wider part. Chords fully contained in one row are
// unaffected; split chords share the parent's color.
export function buildChordRows(
  chords: DisplayChord[],
  duration: number,
  rowSeconds: number,
  pxPerSecond: number,
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

  // Pass 2: prefer the first segment if it fits the label; else use the widest.
  const measureLabelWidth = createLabelWidthMeasurer()
  for (const segs of segmentsByChord) {
    if (segs.length === 0) continue
    let pick = segs[0]
    if (!pick.isSilence && labelFits(pick, pxPerSecond, measureLabelWidth)) {
      pick.showLabel = true
      continue
    }
    for (let i = 1; i < segs.length; i++) {
      if (segs[i].end - segs[i].start > pick.end - pick.start) {
        pick = segs[i]
      }
    }
    if (!pick.isSilence) {
      pick.showLabel = true
    }
  }

  return result
}

// Match the `px-0.5` label padding (0.125rem each side) used in JSX.
const LABEL_PADDING_PX = 4

function labelFits(
  seg: ChordRowSegment,
  pxPerSecond: number,
  measureLabelWidth: (label: string) => number,
): boolean {
  if (!seg.label) return false
  const segWidth = secondsToPx(seg.end - seg.start, pxPerSecond)
  return measureLabelWidth(seg.label) + LABEL_PADDING_PX <= segWidth
}

// Canvas-based text width measurement, cached by label string. Chord labels
// come from a small vocabulary so the cache stays tiny. Lazily created on
// first call so SSR does not touch the DOM. Returns width in CSS pixels.
function createLabelWidthMeasurer(): (label: string) => number {
  const cache = new Map<string, number>()
  let ctx: CanvasRenderingContext2D | null = null
  return (label: string) => {
    const hit = cache.get(label)
    if (hit !== undefined) return hit
    if (ctx === null) {
      const canvas = document.createElement("canvas")
      ctx = canvas.getContext("2d")
    }
    const width = ctx ? ctx.measureText(label).width : 0
    cache.set(label, width)
    return width
  }
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
            {seg.showLabel && <span className="px-0.5">{seg.label}</span>}
          </div>
        )
      })}
    </div>
  )
}