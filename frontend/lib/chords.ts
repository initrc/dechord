import { Chord } from "tonal"
import type { ChordSegment } from "@/lib/api"

export type DisplayChord = {
  start: number
  end: number
  root: string
  quality: string
  isSilence: boolean
}

const QUALITY_SUFFIX: Record<string, string> = {
  major: "",
  minor: "m",
}

function qualitySuffix(type: string): string {
  return QUALITY_SUFFIX[type] ?? type
}

export function parseChordLabel(label: string): { root: string; quality: string; isSilence: boolean } {
  if (label === "N" || label === "") {
    return { root: "", quality: "", isSilence: true }
  }

  const tonalLabel = label.includes(":") ? label.replace(":", "") : label
  const parsed = Chord.get(tonalLabel)

  if (parsed.empty || !parsed.tonic) {
    return { root: label, quality: "", isSilence: true }
  }

  return {
    root: parsed.tonic ?? label,
    quality: qualitySuffix(parsed.type ?? ""),
    isSilence: false,
  }
}

export function toDisplayChords(chords: ChordSegment[]): DisplayChord[] {
  return chords.map((c) => ({
    start: c.start,
    end: c.end,
    ...parseChordLabel(c.label),
  }))
}
