---
id: T0008
title: Bootstrap frontend project
status: new
dependencies: []
---

# Scope

- Initialize the Next.js + React + shadcn/ui frontend at `/Users/davidshi/code/dechord/frontend/` using the Lyra preset command from design-v1.md.
- Add the `tonal.js` library dependency (used by T0010 to parse chord labels for display).
- Set up an API client module that points at the backend (`http://localhost:8000` by default) for development.

# Acceptance

- `pnpm install` and `pnpm dev` start the Next.js dev server at `http://localhost:3000`.
- The default page renders without errors.
- `tonal.js` is importable from a component (smoke-tested).
- `pnpm typecheck` and `pnpm lint` (the shadcn preset configures these) pass on the empty state.

# Implementation Notes

- Use the exact command from design-v1.md: `pnpm dlx shadcn@latest init --preset buFywKm --template next`.
- Proposed repo layout: `frontend/` at the repo root, sibling to `backend/`. Adjust if a different layout is preferred.
- The API client for v1 can be a thin wrapper over `fetch`. Don't pull in `axios` or `react-query` unless the preset already includes them; keep deps minimal per AGENTS.md rule 2.
- CORS is enabled on the backend (T0001) to allow `http://localhost:3000`.
- Reference: `ravel/docs/design-v1.md` Frontend section.