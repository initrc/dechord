export const PX_PER_SECOND = 22

export function secondsToPx(seconds: number): number {
  return seconds * PX_PER_SECOND
}

export function formatTime(seconds: number): string {
  const total = Math.ceil(seconds)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function tickInterval(): number {
  return 15
}
