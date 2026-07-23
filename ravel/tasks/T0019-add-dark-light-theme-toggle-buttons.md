---
id: T0019
title: Add dark/light theme toggle buttons
status: review
dependencies: []
---

# Scope

- Add a dark/light mode switch button to the top-right corner of the library page and the media page.
- On the library view (`frontend/components/library-view.tsx`), place it on the same row as the file uploader (`<Input>` + `<Button>` Upload).
- On the media page (`frontend/app/media/[id]/page.tsx`), place it on the same row as the back button and the title, on the right edge, sized the same as the back button so the title stays centered.
- Add `cursor-pointer` to clickable controls in the uploader row (Upload button, native file input and its generated "Choose File" button) so the hover affordance matches the theme toggle and back link.

# Acceptance

- A single button toggles between dark and light themes on both pages. Clicking it flips the theme immediately without a page reload, with a rotate+scale crossfade between Sun and Moon icons.
- On the library page, the button sits at the right end of the uploader row.
- On the media page, the button sits at the right end of the title row and has the same visual size/hit area as the back-button `<Link>` (which wraps an `size-5` `ArrowLeft` icon); the `<h1>` title remains horizontally centered as it is today.
- Theme choice persists across navigation/reload (handled by the existing `next-themes` provider).
- The cursor shows as a pointer over the Upload button, the whole file input (including the "No file chosen" label), and the theme toggle on both pages.
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- Theme infrastructure already exists: `next-themes` is wired up in `frontend/components/theme-provider.tsx` and `frontend/app/layout.tsx`, with a `d` hotkey toggle. This task only adds the visible button — do not introduce a second theme mechanism.
- Render the button as a small client component (`frontend/components/theme-toggle.tsx`) that calls `useTheme()` from `next-themes`. The library view is already a client component and can import it directly. The media page (`app/media/[id]/page.tsx`) is a server component — import the client `ThemeToggle` into it; Next.js allows client components in server trees.
- Use the shadcn `Button` primitive (`variant="ghost" size="icon"`) for the toggle so appearance, borders, padding, focus rings, and SVG defaults are handled by the primitive — no manual reset classes on a raw `<button>`. Add only `relative` (to anchor the absolute-positioned Moon) and `cursor-pointer`.
- Use a `lucide-react` icon pair (`Sun` / `Moon`) with `transition-all` and `dark:` rotate/scale variants for the crossfade: Sun visible in light mode, Moon in dark. Both icons share `size-5 ... transition-all`; Moon is `absolute` to overlay Sun. The `dark:` variants ride on next-themes' pre-hydration `.dark` class, so no `mounted`/`resolvedTheme` gate is needed in render — keep `resolvedTheme` only inside the `onClick` closure to avoid hydration mismatch on `aria-label`.
- Do NOT use `disableTransitionOnChange` on the next-themes provider — it injects `transition: none !important` globally for ~1ms around the theme switch, which kills the `transition-all` crossfade on the icons. The original provider had this flag set; it must be removed for the animation to play.
- The media page title row is `flex w-full items-center gap-2` with a flex-1 centered `<h1>`. Both ends are `size-5` (the `ArrowLeft` icon sizes the `<Link>`, the shadcn `Button size="icon-xs"` is `size-6` but visually matches); the `<h1>` stays centered because its two siblings are equal-footprint bookends.
- For the uploader row: add `cursor-pointer` to the Upload `<Button>` (shadcn doesn't set it by default), and `cursor-pointer` + `file:cursor-pointer` + `file:mr-2` to the file `<Input>` so the whole control (including the native "No file chosen" label) shows the pointer and has spacing between the generated "Choose File" button and the filename.
- Reference: theme provider at `frontend/components/theme-provider.tsx`; toggle at `frontend/components/theme-toggle.tsx`; media page row at `frontend/app/media/[id]/page.tsx:40`; library uploader row at `frontend/components/library-view.tsx:126`.