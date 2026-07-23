"use client"

import { useMemo } from "react"
import { Play, Pause } from "lucide-react"

import { useAudioPlayer } from "@/lib/audio-player"
import { usePeaks } from "@/lib/peaks"
import { useRowSeconds, usePxPerSecond, buildTimeRows } from "@/lib/layout"
import { useHotkey } from "@/hooks/use-hotkey"
import { formatTime, secondsToPx } from "@/lib/timeline"
import type { DisplayChord } from "@/lib/chords"
import {
  buildChordRows,
  ChordTrackRow,
  CHORD_HEIGHT,
} from "@/components/chord-track"
import { MasterTrackRow, MASTER_HEIGHT } from "@/components/master-track"
import { TimelineAxis } from "@/components/timeline-axis"
import { Button } from "@/components/ui/button"

export function ItemView({
  mediaId,
  duration,
  chords,
}: {
  mediaId: string
  duration: number
  chords: DisplayChord[]
}) {
  const player = useAudioPlayer(mediaId, duration)
  const { peaks, peaksPerSecond } = usePeaks(mediaId)
  const { containerRef, rowSeconds } = useRowSeconds()
  const pxPerSecond = usePxPerSecond(containerRef)

  useHotkey(" ", () => void player.toggle())

  const rows = useMemo(
    () => buildTimeRows(duration, rowSeconds),
    [duration, rowSeconds],
  )
  const chordRows = useMemo(
    () => buildChordRows(chords, duration, rowSeconds, pxPerSecond),
    [chords, duration, rowSeconds, pxPerSecond],
  )
  const hasChords = chords.length > 0
  const trackBlockHeight = hasChords ? CHORD_HEIGHT + MASTER_HEIGHT : MASTER_HEIGHT

  return (
    <div
      ref={containerRef}
      className="[--row-seconds:15] sm:[--row-seconds:30] [--px-per-second:22] lg:[--px-per-second:32] mx-auto flex w-max flex-col gap-6"
    >
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={player.toggle}
          disabled={player.loading}
          aria-label={player.isPlaying ? "Pause" : "Play"}
        >
          {player.isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
        </Button>
        <span className="text-sm tabular-nums text-muted-foreground">
          {formatTime(player.currentTime)} / {formatTime(duration)}
        </span>
      </div>

      {!hasChords && (
        <p className="text-sm text-muted-foreground">No chords detected.</p>
      )}

      <div className="flex flex-col gap-2 overflow-x-hidden">
        {rows.map((row, i) => {
          const width = secondsToPx(row.rowEnd - row.rowStart, pxPerSecond)
          const cursorActive =
            player.currentTime >= row.rowStart && player.currentTime < row.rowEnd
          return (
            <div
              key={row.index}
              className="relative shrink-0"
              style={{ width }}
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect()
                const x = e.clientX - rect.left
                player.seek(row.rowStart + x / pxPerSecond)
              }}
            >
              <div className="border border-primary/10">
                {hasChords && (
                  <ChordTrackRow row={chordRows[i]} pxPerSecond={pxPerSecond} />
                )}
                <MasterTrackRow
                  row={row}
                  peaks={peaks}
                  peaksPerSecond={peaksPerSecond}
                  pxPerSecond={pxPerSecond}
                />
              </div>
              <TimelineAxis row={row} width={width} pxPerSecond={pxPerSecond} />
              {cursorActive && (
                <div
                  className="pointer-events-none absolute top-0 z-10 bg-primary"
                  style={{
                    left: secondsToPx(player.currentTime - row.rowStart, pxPerSecond) - 2,
                    height: trackBlockHeight,
                    width: 2,
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}