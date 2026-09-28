import type { ReactNode } from "react"

export function TableFrame({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-panel">
      <table className="w-full text-left text-sm">{children}</table>
    </div>
  )
}

export const headCell = "px-4 py-2.5 text-xs font-semibold tracking-wide whitespace-nowrap text-muted uppercase"
export const numberHeadCell = `${headCell} text-right`
export const bodyCell = "border-t border-line px-4 py-2.5 align-top text-ink"
export const mutedCell = `${bodyCell} whitespace-nowrap text-muted`
export const numberCell = `${bodyCell} text-right tabular-nums whitespace-nowrap`
