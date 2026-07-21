import { formatTime, secondsToPx } from "@/lib/timeline"
import type { TimeRow } from "@/lib/layout"

export const AXIS_HEIGHT = 20

export function TimelineAxis({
  row,
  width,
}: {
  row: TimeRow
  width: number
}) {
  return (
    <div className="relative" style={{ width, height: AXIS_HEIGHT }}>
      {row.ticks.map((t, j) => {
        const isFirst = j === 0
        const isLast = j === row.ticks.length - 1
        const translateClass = isFirst
          ? ""
          : isLast
            ? "-translate-x-full"
            : "-translate-x-1/2"
        return (
          <span
            key={t}
            className={`absolute top-0.5 ${translateClass} text-[10px] text-muted-foreground`}
            style={{ left: secondsToPx(t - row.rowStart) }}
          >
            {formatTime(t)}
          </span>
        )
      })}
    </div>
  )
}