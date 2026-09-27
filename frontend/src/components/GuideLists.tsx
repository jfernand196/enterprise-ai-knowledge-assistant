import type { EmployeeId } from "@/domain/chat"
import type { GuidePrompt } from "@/i18n/copy"
import { useLocale } from "@/i18n/LocaleProvider"

interface GuideListsProps {
  onAsk: (message: string) => void
  onStage: (message: string, userId: EmployeeId) => void
  disabled: boolean
}

export function GuideLists({ onAsk, onStage, disabled }: GuideListsProps) {
  const { copy } = useLocale()

  return (
    <>
      <section className="mt-8" aria-labelledby="policy-guide">
        <h3 id="policy-guide" className="text-sm font-semibold text-ink">
          {copy.policies}
        </h3>
        <ul className="mt-2 border-t border-line">
          {copy.policyPrompts.map((item) => (
            <li key={item.prompt} className="border-b border-line">
              <button
                type="button"
                disabled={disabled}
                onClick={() => onAsk(item.prompt)}
                className="w-full py-3 text-left transition hover:text-accent disabled:opacity-50"
              >
                <PromptLine item={item} />
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8" aria-labelledby="employee-guide">
        <h3 id="employee-guide" className="text-sm font-semibold text-ink">
          {copy.aboutEmployee}
        </h3>
        <p className="mt-1 text-sm text-muted">{copy.aboutEmployeeHint}</p>
        <ul className="mt-2 border-t border-line">
          {copy.employeePrompts.map((item) => (
            <li key={`${item.userId}-${item.prompt}-${item.expect}`} className="border-b border-line">
              <button
                type="button"
                disabled={disabled}
                onClick={() => item.userId && onStage(item.prompt, item.userId)}
                className="w-full py-3 text-left transition hover:text-accent disabled:opacity-50"
              >
                <p className="text-xs font-semibold tracking-wide text-accent uppercase">{item.employee}</p>
                <PromptLine item={item} />
              </button>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}

function PromptLine({ item }: { item: GuidePrompt }) {
  return (
    <>
      <p className="text-sm font-medium text-ink">{item.prompt}</p>
      <p className="mt-1 text-sm text-muted">{item.expect}</p>
    </>
  )
}
