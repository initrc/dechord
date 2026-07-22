"use client"

import { useEffect, useState } from "react"

// Fixed peaks resolution. 1000/sec is fine-grained enough to bucket for any
// visible zoom in the item view without rescanning the raw sample buffer.
const PEAKS_PER_SECOND = 1000

export type PeaksData = {
  peaks: Float32Array | null
  peaksPerSecond: number
  loading: boolean
}

// Decode the source once on mount, scan the first channel into a fixed-rate
// max-abs peaks array. `MasterTrackRow` then reads buckets from the array
// instead of walking raw samples per pixel, so resize/theme/row re-renders
// are O(peaks), not O(samples).
//
// A second fetch of the source file (the player already streams it) is the
// one-time price. The browser cache typically dedupes the bytes.
export function usePeaks(mediaId: string): PeaksData {
  const [peaks, setPeaks] = useState<Float32Array | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const res = await fetch(`/api/media/${mediaId}/audio/source`)
        if (!res.ok) throw new Error(`audio fetch failed: ${res.status}`)
        const arr = await res.arrayBuffer()
        const Ctor: typeof AudioContext =
          window.AudioContext ??
          (window as unknown as { webkitAudioContext: typeof AudioContext })
            .webkitAudioContext
        const ctx = new Ctor()
        try {
          const buf = await ctx.decodeAudioData(arr)
          if (cancelled) return
          const data = buf.getChannelData(0)
          const bucketSize = Math.max(
            1,
            Math.floor(buf.sampleRate / PEAKS_PER_SECOND),
          )
          const bucketCount = Math.floor(data.length / bucketSize)
          const out = new Float32Array(bucketCount)
          for (let b = 0; b < bucketCount; b++) {
            let peak = 0
            const base = b * bucketSize
            for (let i = 0; i < bucketSize; i++) {
              const v = Math.abs(data[base + i] as number)
              if (v > peak) peak = v
            }
            out[b] = peak
          }
          if (!cancelled) setPeaks(out)
        } finally {
          void ctx.close().catch(() => {})
        }
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