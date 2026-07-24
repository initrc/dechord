"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export type AudioPlayer = {
  loading: boolean
  isPlaying: boolean
  currentTime: number
  toggle: () => Promise<void>
  seek: (time: number) => void
}

// Playback over an `HTMLAudioElement`. The source is resolved into a Blob
// URL on mount (see effect below) so playback reads from in-memory bytes
// rather than a live network stream.
export function useAudioPlayer(
  mediaId: string,
  duration: number,
): AudioPlayer {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [loading, setLoading] = useState(true)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)

  // Download the entire source into a Blob once on mount, then point the
  // `HTMLAudioElement` at the blob URL. A streaming `Audio(src)` reads bytes
  // on demand from the network; on a slow link the buffered-ahead range
  // underruns partway through a long track and `currentTime` freezes until
  // more arrives (see `waiting`/`stalled`). Resolving the whole file into
  // memory up front eliminates the network dependency during playback, the
  // same guarantee the old `decodeAudioData` path had. Peaks (and therefore
  // the waveform) come from the separate `/audio/peaks` endpoint, so they
  // still render instantly — only the play button waits on this fetch.
  useEffect(() => {
    let cancelled = false
    const abort = new AbortController()
    let url: string | null = null
    let audio: HTMLAudioElement | null = null
    const handlers: Array<[keyof HTMLMediaElementEventMap, () => void]> = [
      ["playing", () => setIsPlaying(true)],
      ["pause", () => setIsPlaying(false)],
      ["ended", () => { setIsPlaying(false); setCurrentTime(duration) }],
      ["error", () => { console.error("audio load failed", audio?.error); setLoading(false) }],
    ]
    void (async () => {
      try {
        const res = await fetch(`/api/media/${mediaId}/audio/source`, { signal: abort.signal })
        if (!res.ok) throw new Error(`audio fetch failed: ${res.status}`)
        const blob = await res.blob()
        if (cancelled) return
        url = URL.createObjectURL(blob)
        audio = new Audio(url)
        audio.preload = "auto"
        audioRef.current = audio
        for (const [ev, fn] of handlers) audio.addEventListener(ev, fn)
        setLoading(false)
      } catch (e) {
        if (cancelled || (e instanceof DOMException && e.name === "AbortError")) return
        console.error("audio load failed", e)
        setLoading(false)
      }
    })()
    return () => {
      cancelled = true
      abort.abort()
      if (audio) {
        audio.pause()
        for (const [ev, fn] of handlers) audio.removeEventListener(ev, fn)
      }
      if (url) URL.revokeObjectURL(url)
      audioRef.current = null
    }
  }, [mediaId, duration])

  // `timeupdate` fires at ~4 Hz, far too coarse for a smooth cursor. rAF-poll
  // `audio.currentTime` while playing — the property is a live getter, so this
  // gives 60 fps position updates without Web Audio.
  useEffect(() => {
    if (!isPlaying) return
    let raf = 0
    const tick = () => {
      const audio = audioRef.current
      if (audio) setCurrentTime(audio.currentTime)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [isPlaying])

  const toggle = useCallback(async () => {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) {
      if (audio.currentTime >= duration) audio.currentTime = 0
      await audio.play()
    } else {
      audio.pause()
    }
  }, [duration])

  const seek = useCallback(
    (time: number) => {
      const audio = audioRef.current
      if (!audio) return
      audio.currentTime = Math.max(0, Math.min(time, duration))
      // The rAF loop only runs while playing, so sync state here too — otherwise
      // seeking while paused leaves the cursor frozen until playback resumes.
      setCurrentTime(audio.currentTime)
    },
    [duration],
  )

  return { loading, isPlaying, currentTime, toggle, seek }
}