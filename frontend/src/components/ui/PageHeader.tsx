import type { ReactNode } from "react"

import { LocaleToggle } from "@/components/ui/LocaleToggle"

interface PageHeaderProps {
  kicker: string
  title: string
  width: string
  actions?: ReactNode
}

export function PageHeader({ kicker, title, width, actions }: PageHeaderProps) {
  return (
    <header className="sticky top-0 z-10 shrink-0 border-b border-line bg-paper px-5 py-4">
      <div className={`mx-auto flex w-full items-baseline justify-between gap-4 ${width}`}>
        <div>
          <p className="text-xs font-semibold tracking-wide text-accent uppercase">{kicker}</p>
          <h1 className="font-serif text-2xl text-ink">{title}</h1>
        </div>
        <div className="flex items-center gap-2">
          {actions}
          <LocaleToggle />
        </div>
      </div>
    </header>
  )
}
