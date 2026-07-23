"use client"

import { useTheme } from "next-themes"
import { Moon, Sun } from "lucide-react"
import { Button } from "@/components/ui/button"

const iconBase = "size-5 transition-all"

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()

  return (
    <Button
      variant="ghost"
      size="icon"
      className="relative cursor-pointer text-muted-foreground hover:bg-transparent hover:text-foreground dark:hover:bg-transparent"
      aria-label="Toggle theme"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      <Sun className={`${iconBase} rotate-0 scale-100 dark:-rotate-90 dark:scale-0`} />
      <Moon className={`${iconBase} rotate-90 scale-0 absolute dark:rotate-0 dark:scale-100`} />
    </Button>
  )
}
