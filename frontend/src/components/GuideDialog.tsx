import { useEffect, useRef } from "react"

import { GuideLists } from "@/components/GuideLists"
import type { EmployeeId } from "@/domain/chat"
import { useLocale } from "@/i18n/LocaleProvider"

interface GuideDialogProps {
  open: boolean
  onClose: () => void
  onAsk: (message: string) => void
  onStage: (message: string, userId: EmployeeId) => void
  disabled: boolean
}

export function GuideDialog({ open, onClose, onAsk, onStage, disabled }: GuideDialogProps) {
  const { copy } = useLocale()
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) {
      return
    }
    if (open && !dialog.open) {
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(event) => event.target === event.currentTarget && onClose()}
      aria-labelledby="guide-dialog-title"
      className="m-auto max-h-[85dvh] w-[min(40rem,calc(100vw-2rem))] overflow-y-auto rounded-2xl border border-line bg-panel p-0 text-ink backdrop:bg-ink/40"
    >
      <div className="px-6 py-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium tracking-wide text-accent uppercase">{copy.guideKicker}</p>
            <h2 id="guide-dialog-title" className="mt-2 font-serif text-3xl leading-tight">
              {copy.guideTitle}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-line px-3 py-1.5 text-sm font-semibold hover:border-accent"
          >
            {copy.close}
          </button>
        </div>
        <p className="mt-4 text-base leading-relaxed text-muted">{copy.guideLead}</p>
        <GuideLists
          disabled={disabled}
          onAsk={(message) => {
            onClose()
            onAsk(message)
          }}
          onStage={(message, userId) => {
            onClose()
            onStage(message, userId)
          }}
        />
      </div>
    </dialog>
  )
}
