"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export type AudioPlayer = {
  loading: boolean
  isPlaying: boolean
  currentTime: number
  toggle: () => Promise<void>
  seek: (time: number) => void
}

// Streaming playback over an `HTMLAudioElement`. The browser decodes on demand.
export function useAudioPlayer(
  mediaId: string,
  duration: number,
): AudioPlayer {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [loading, setLoading] = useState(true)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)

  useEffect(() => {
    const audio = new Audio(`/api/media/${mediaId}/audio/source`)
    audio.preload = "auto"
    audioRef.current = audio
    const handlers: Array<[keyof HTMLMediaElementEventMap, () => void]> = [
      ["canplay", () => setLoading(false)],
      ["playing", () => setIsPlaying(true)],
      ["pause", () => setIsPlaying(false)],
      ["ended", () => { setIsPlaying(false); setCurrentTime(duration) }],
      ["error", () => { console.error("audio load failed", audio.error); setLoading(false) }],
    ]
    for (const [ev, fn] of handlers) audio.addEventListener(ev, fn)
    return () => {
      audio.pause()
      for (const [ev, fn] of handlers) audio.removeEventListener(ev, fn)
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