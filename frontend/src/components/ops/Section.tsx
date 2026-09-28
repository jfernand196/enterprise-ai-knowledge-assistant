import type { ReactNode } from "react"

interface SectionProps {
  title: string
  hint?: string
  action?: ReactNode
  children: ReactNode
}

export function Section({ title, hint, action, children }: SectionProps) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-serif text-xl text-ink">{title}</h2>
          {hint && <p className="mt-1 max-w-2xl text-sm text-muted">{hint}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}
