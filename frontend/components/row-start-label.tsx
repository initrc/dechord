import { formatTime } from "@/lib/timeline"
import type { TimeRow } from "@/lib/layout"

export function RowStartLabel({
  row,
}: {
  row: TimeRow
}) {
  return (
    <span className="pointer-events-none absolute bottom-0 left-0 px-0.5 text-[8px] leading-none text-muted-foreground">
      {formatTime(row.rowStart)}
    </span>
  )
}