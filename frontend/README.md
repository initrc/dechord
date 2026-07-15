# Dechord Frontend

Next.js + React + shadcn/ui frontend for Dechord.

## Getting started

```bash
pnpm install
pnpm dev
```

The dev server starts at `http://localhost:3000`.

## Available commands

```bash
pnpm dev          # Start dev server
pnpm build        # Build for production
pnpm start        # Start production server
pnpm lint         # Run ESLint
pnpm typecheck    # Run TypeScript type checking
pnpm format       # Format code with Prettier
```

## Adding components

```bash
pnpm dlx shadcn@latest add button
```

Components are placed in `components/ui/` and imported as:

```tsx
import { Button } from "@/components/ui/button"
```
