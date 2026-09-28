import { useMutation } from "@tanstack/react-query"

import { sendFeedback } from "@/api/llmops"
import type { Rating } from "@/domain/llmops"
import { useLocale } from "@/i18n/LocaleProvider"

interface FeedbackButtonsProps {
  requestId: string
}

export function FeedbackButtons({ requestId }: FeedbackButtonsProps) {
  const { copy } = useLocale()
  const mutation = useMutation({ mutationFn: (rating: Rating) => sendFeedback(requestId, rating) })
  const chosen = mutation.isSuccess ? mutation.variables : null

  return (
    <div className="flex items-center gap-2" role="group" aria-label={copy.feedbackPrompt}>
      {chosen ? (
        <p className="text-xs text-muted" role="status">
          {copy.feedbackThanks}
        </p>
      ) : (
        <>
          <VoteButton label={copy.feedbackUp} symbol="👍" disabled={mutation.isPending} onClick={() => mutation.mutate("up")} />
          <VoteButton label={copy.feedbackDown} symbol="👎" disabled={mutation.isPending} onClick={() => mutation.mutate("down")} />
          {mutation.isError && (
            <p className="text-xs text-danger" role="alert">
              {mutation.error.message}
            </p>
          )}
        </>
      )}
    </div>
  )
}

interface VoteButtonProps {
  label: string
  symbol: string
  disabled: boolean
  onClick: () => void
}

function VoteButton({ label, symbol, disabled, onClick }: VoteButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className="flex size-8 items-center justify-center rounded-full border border-line bg-paper text-sm hover:border-accent disabled:opacity-50"
    >
      <span aria-hidden="true">{symbol}</span>
    </button>
  )
}
