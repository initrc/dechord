---
id: T0024
title: Rename ItemView to SheetView
status: done
dependencies: []
---

# Scope

- Rename the `ItemView` component to `SheetView` to match its sheet-music-with-two-tracks UI.
- Rename the file `frontend/components/item-view.tsx` to `frontend/components/sheet-view.tsx`.
- Update the import and JSX usage in `frontend/app/media/[id]/page.tsx`.
- Update references in existing task docs (`item-view.tsx` → `sheet-view.tsx`, `ItemView` → `SheetView`, "item view" → "sheet view").

# Acceptance

- `ItemView` no longer appears anywhere in the codebase.
- `pnpm typecheck` passes.
- `pnpm lint` passes.

# Implementation Notes

- One import site: `frontend/app/media/[id]/page.tsx:5`.
- Renamed via `git mv` so history is preserved.
- Task filenames with the old `item-view` slug (T0012, T0022) are left as-is — they're historical task IDs and renaming the filename slug isn't necessary for content accuracy.