import { GuideLists } from "@/components/GuideLists"
import type { EmployeeId } from "@/domain/chat"
import { useLocale } from "@/i18n/LocaleProvider"

interface EmptyStateProps {
  onAsk: (message: string) => void
  onStage: (message: string, userId: EmployeeId) => void
  disabled: boolean
}

export function EmptyState({ onAsk, onStage, disabled }: EmptyStateProps) {
  const { copy } = useLocale()

  return (
    <div className="mx-auto flex max-w-2xl flex-col pt-10 pb-8">
      <p className="text-sm font-medium tracking-wide text-accent uppercase">{copy.guideKicker}</p>
      <h2 className="mt-3 font-serif text-4xl leading-tight text-ink">{copy.guideTitle}</h2>
      <p className="mt-4 max-w-xl text-base leading-relaxed text-muted">{copy.guideLead}</p>
      <GuideLists onAsk={onAsk} onStage={onStage} disabled={disabled} />
    </div>
  )
}
