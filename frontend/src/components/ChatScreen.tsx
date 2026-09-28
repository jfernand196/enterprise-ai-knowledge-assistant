import { useMutation } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"

import { sendChat } from "@/api/chat"
import { AssistantMessage } from "@/components/AssistantMessage"
import { Composer } from "@/components/Composer"
import { EmptyState } from "@/components/EmptyState"
import { GuideDialog } from "@/components/GuideDialog"
import { ErrorAlert } from "@/components/ui/ErrorAlert"
import { PageHeader } from "@/components/ui/PageHeader"
import { pillButton } from "@/components/ui/styles"
import type { ChatReply, EmployeeId } from "@/domain/chat"
import { useLocale } from "@/i18n/LocaleProvider"

interface ComposerDraft {
  nonce: string
  message: string
  userId: EmployeeId
}

type ThreadItem =
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "assistant"; reply: ChatReply }
  | { id: string; kind: "error"; text: string }

export function ChatScreen() {
  const { copy } = useLocale()
  const [items, setItems] = useState<ThreadItem[]>([])
  const [draft, setDraft] = useState<ComposerDraft | null>(null)
  const [guideOpen, setGuideOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const composerRef = useRef<HTMLDivElement>(null)
  const mutation = useMutation({ mutationFn: sendChat })
  const showingGuide = items.length === 0 && !mutation.isPending

  useEffect(() => {
    if (showingGuide) {
      return
    }
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [items, mutation.isPending, showingGuide])

  useEffect(() => {
    if (!draft) {
      return
    }
    composerRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [draft])

  function ask(message: string, userId?: EmployeeId) {
    setItems((current) => [...current, { id: crypto.randomUUID(), kind: "user", text: message }])
    mutation.mutate(
      { message, userId },
      {
        onSuccess: (reply) => {
          setItems((current) => [...current, { id: reply.request_id, kind: "assistant", reply }])
        },
        onError: (error: Error) => {
          setItems((current) => [
            ...current,
            { id: crypto.randomUUID(), kind: "error", text: error.message },
          ])
        },
      },
    )
  }

  function stage(message: string, userId: EmployeeId) {
    setDraft({ nonce: crypto.randomUUID(), message, userId })
  }

  return (
    <div className={showingGuide ? "flex min-h-dvh flex-col" : "flex h-dvh flex-col"}>
      <PageHeader
        kicker={copy.brand}
        title={copy.title}
        width="max-w-3xl"
        actions={
          <>
            {!showingGuide && (
              <button
                type="button"
                onClick={() => setGuideOpen(true)}
                className={`flex items-center gap-1.5 ${pillButton}`}
                aria-label={copy.guideButtonLabel}
                aria-haspopup="dialog"
              >
                <span
                  className="flex size-4 items-center justify-center rounded-full border border-current text-[0.625rem] leading-none"
                  aria-hidden="true"
                >
                  i
                </span>
                {copy.guideButton}
              </button>
            )}
            <Link to="/ops" className={pillButton} aria-label={copy.ops.linkLabel}>
              {copy.ops.link}
            </Link>
          </>
        }
      />
      <GuideDialog
        open={guideOpen}
        onClose={() => setGuideOpen(false)}
        onAsk={(message) => ask(message)}
        onStage={stage}
        disabled={mutation.isPending}
      />
      <main className={showingGuide ? "mx-auto flex w-full max-w-3xl flex-1 flex-col px-5" : "mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-5"}>
        <div className={showingGuide ? undefined : "min-h-0 flex-1 overflow-y-auto"}>
          {items.length === 0 ? (
            <EmptyState onAsk={(message) => ask(message)} onStage={stage} disabled={mutation.isPending} />
          ) : (
            <ol className="flex flex-col gap-5 py-8">
              {items.map((item) => (
                <li key={item.id}>
                  {item.kind === "user" && (
                    <div className="flex justify-end">
                      <p className="max-w-lg rounded-2xl bg-accent px-4 py-3 text-sm leading-relaxed text-white">
                        {item.text}
                      </p>
                    </div>
                  )}
                  {item.kind === "assistant" && <AssistantMessage reply={item.reply} />}
                  {item.kind === "error" && <ErrorAlert message={item.text} />}
                </li>
              ))}
              {mutation.isPending && (
                <li>
                  <div
                    className="flex items-start gap-3 rounded-2xl border border-line bg-panel px-5 py-4"
                    role="status"
                    aria-live="polite"
                  >
                    <span className="mt-1.5 size-2 shrink-0 animate-pulse rounded-full bg-accent" aria-hidden="true" />
                    <div>
                      <p className="text-sm font-medium text-ink">{copy.reviewing}</p>
                      <p className="mt-1 text-sm text-muted">{copy.reviewingHint}</p>
                    </div>
                  </div>
                </li>
              )}
            </ol>
          )}
          <div ref={bottomRef} />
        </div>
        <div ref={composerRef}>
          <Composer key={copy.documentTitle} pending={mutation.isPending} draft={draft} onSend={ask} />
        </div>
      </main>
    </div>
  )
}
