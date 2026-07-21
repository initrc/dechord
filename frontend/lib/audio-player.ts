"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export type AudioPlayer = {
  loading: boolean
  ready: boolean
  isPlaying: boolean
  currentTime: number
  channelData: Float32Array | null
  sampleRate: number
  play: () => Promise<void>
  pause: () => void
  toggle: () => Promise<void>
  seek: (time: number) => void
}

// Web Audio playback for the master track. The cursor is driven off
// `AudioContext.currentTime` (read in a rAF loop) rather than a JS timer so it
// stays in sync with the actual audio output across long playback.
//
// State:
//   startCtxTime   - AudioContext.currentTime when the current source started
//   startOffset    - buffer offset (seconds) at which the source started
//   currentTime    = startOffset + (now - startCtxTime)  (while playing)
export function useAudioPlayer(
  mediaId: string,
  duration: number,
): AudioPlayer {
  const ctxRef = useRef<AudioContext | null>(null)
  const bufferRef = useRef<AudioBuffer | null>(null)
  const sourceRef = useRef<AudioBufferSourceNode | null>(null)
  const startCtxTimeRef = useRef(0)
  const startOffsetRef = useRef(0)
  const rafRef = useRef<number | null>(null)

  const [loading, setLoading] = useState(false)
  const [ready, setReady] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [channelData, setChannelData] = useState<Float32Array | null>(null)
  const [sampleRate, setSampleRate] = useState(0)

  const isPlayingRef = useRef(false)
  useEffect(() => {
    isPlayingRef.current = isPlaying
  }, [isPlaying])

  const stopSource = useCallback(() => {
    const src = sourceRef.current
    if (src) {
      src.onended = null
      try {
        src.stop()
      } catch {
        // Already stopped; safe to ignore.
      }
      src.disconnect()
      sourceRef.current = null
    }
  }, [])

  // rAF loop: advances currentTime from the Web Audio clock while playing.
  useEffect(() => {
    if (!isPlaying) return
    const tick = () => {
      const ctx = ctxRef.current
      if (!ctx) return
      const t = startOffsetRef.current + (ctx.currentTime - startCtxTimeRef.current)
      if (t >= duration) {
        setCurrentTime(duration)
        setIsPlaying(false)
        return
      }
      setCurrentTime(t)
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
    }
  }, [isPlaying, duration])

  const ensureBuffer = useCallback(async () => {
    if (!ctxRef.current) {
      const Ctor: typeof AudioContext =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext
      ctxRef.current = new Ctor()
    }
    if (!bufferRef.current) {
      setLoading(true)
      try {
        const res = await fetch(`/api/media/${mediaId}/audio/source`)
        if (!res.ok) throw new Error(`audio fetch failed: ${res.status}`)
        const arr = await res.arrayBuffer()
        const ctx = ctxRef.current
        if (!ctx) return
        const buf = await ctx.decodeAudioData(arr)
        bufferRef.current = buf
        setChannelData(buf.getChannelData(0))
        setSampleRate(buf.sampleRate)
        setReady(true)
      } finally {
        setLoading(false)
      }
    }
  }, [mediaId])

  // Pre-load on mount so the waveform can render before the user hits play.
  // decodeAudioData works on a suspended AudioContext; resume() still waits
  // for the first user gesture inside play().
  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        await ensureBuffer()
      } catch (e) {
        if (!cancelled) console.error("audio load failed", e)
      }
    })()
    return () => {
      cancelled = true
      stopSource()
      void ctxRef.current?.close().catch(() => {})
      ctxRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const play = useCallback(
    async (startAt?: number) => {
      await ensureBuffer()
      const ctx = ctxRef.current
      if (!ctx || !bufferRef.current) return
      if (ctx.state === "suspended") {
        try {
          await ctx.resume()
        } catch {
          // Ignore resume failures; playback will simply not advance.
        }
      }
      stopSource()
      let offset = startAt ?? currentTime
      if (offset >= duration) offset = 0
      const src = ctx.createBufferSource()
      src.buffer = bufferRef.current
      src.connect(ctx.destination)
      // Fires only on natural end (stopSource clears the handler before .stop()).
      src.onended = () => {
        if (isPlayingRef.current) {
          setIsPlaying(false)
          setCurrentTime(duration)
        }
      }
      sourceRef.current = src
      startCtxTimeRef.current = ctx.currentTime
      startOffsetRef.current = offset
      setCurrentTime(offset)
      src.start(0, offset)
      setIsPlaying(true)
    },
    [ensureBuffer, currentTime, duration, stopSource],
  )

  const pause = useCallback(() => {
    const ctx = ctxRef.current
    if (!ctx) return
    const t = startOffsetRef.current + (ctx.currentTime - startCtxTimeRef.current)
    setCurrentTime(Math.min(t, duration))
    stopSource()
    setIsPlaying(false)
  }, [duration, stopSource])

  const toggle = useCallback(async () => {
    if (isPlayingRef.current) pause()
    else await play()
  }, [pause, play])

  const seek = useCallback(
    (time: number) => {
      const clamped = Math.max(0, Math.min(time, duration))
      if (isPlayingRef.current) {
        void play(clamped)
      } else {
        setCurrentTime(clamped)
      }
    },
    [duration, play],
  )

  return {
    loading,
    ready,
    isPlaying,
    currentTime,
    channelData,
    sampleRate,
    play,
    pause,
    toggle,
    seek,
  }
}