---
id: T0022
title: Fix item view horizontal scroll and phone landscape width
status: done
dependencies:
  - T0014
---

# Scope

- Fix two regressions from T0014's responsive `--px-per-second` bump (22 → 32 at `sm:`):
  1. On viewports where the row content (e.g. 30s × 32px = 960px) exceeds the available width, the page could not be scrolled back to the start of the tracks — only toward the end.
  2. Phone landscape (≈792 CSS px) cleared Tailwind's `sm:` (640px) breakpoint and received the 32 px/sec tier, making rows wider than the viewport and forcing horizontal scrolling.
- Move the 32 px/sec tier from `sm:` to `lg:` (1024px) so only desktop-class widths get it; phone landscape stays at 22 (30s × 22px = 660px, fits).

# Acceptance

- Project builds, passes TypeScript type-checking, and passes lint.
- On a viewport narrower than the track content, the user can scroll to both the start and the end of the tracks — left overflow is reachable, not clipped.
- On a 792px-wide viewport (phone landscape), rows render at 22 px/sec (no horizontal scroll for a 30s row); at ≥1024px rows render at 32 px/sec.
- `frontend/lib/layout.ts` is unchanged; the responsive value continues to flow through `usePxPerSecond` and aligns chord track, master track, and seek math.

# Implementation Notes

- `frontend/app/media/[id]/page.tsx:39`: the wrapper `<div className="flex flex-col items-center gap-8 overflow-x-auto max-w-full">` centered an over-wide flex item, which clipped the left-side overflow (classic flexbox `items-center` + overflow bug). Switched to `items-start` so the leading edge stays in scroll range; centering is delegated to the child via `mx-auto`.
- `frontend/components/item-view.tsx:51`: root container changed from `flex flex-col gap-6` to `mx-auto flex w-max flex-col gap-6`. `w-max` sizes the flex item to its content; `mx-auto` re-centers it when it fits the viewport and collapses to `0` (left-aligned, fully scrollable) when it overflows. Also moved `--px-per-second`'s 32 tier from `sm:` to `lg:`.
- `frontend/lib/layout.ts` and `frontend/hooks/use-css-var.ts` need no changes — `useCssVar` already re-reads on resize, so the breakpoint shift is picked up automatically on viewport transitions.
- `T0014` introduced the regression; this task depends on it for context only (no code dependency).