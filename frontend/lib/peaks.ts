"use client"

import { useEffect, useState } from "react"

// Must match `backend/app/uploads.py` `PEAKS_PER_SECOND`. A single shared value
// across the two sites keeps bucket→time mapping in sync; do not drift.
export const PEAKS_PER_SECOND = 1000

export type PeaksData = {
  peaks: Float32Array | null
  peaksPerSecond: number
  loading: boolean
}

// Fetch a precomputed peaks blob from the backend. Computed once at upload by
// the ffmpeg WAV pass; the waveform renders as soon as the small blob lands,
// no client-side `decodeAudioData` or sample scan.
export function usePeaks(mediaId: string): PeaksData {
  const [peaks, setPeaks] = useState<Float32Array | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const res = await fetch(`/api/media/${mediaId}/audio/peaks`)
        if (!res.ok) throw new Error(`peaks fetch failed: ${res.status}`)
        const arr = await res.arrayBuffer()
        if (!cancelled) setPeaks(new Float32Array(arr))
      } catch (e) {
        if (!cancelled) console.error("peaks load failed", e)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [mediaId])

  return { peaks, peaksPerSecond: PEAKS_PER_SECOND, loading }
}