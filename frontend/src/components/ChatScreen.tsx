import { useMutation } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"

import { sendChat } from "@/api/chat"
import { AssistantMessage } from "@/components/AssistantMessage"
import { Composer } from "@/components/Composer"
import { EmptyState } from "@/components/EmptyState"
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
  const { copy, toggleLocale } = useLocale()
  const [items, setItems] = useState<ThreadItem[]>([])
  const [draft, setDraft] = useState<ComposerDraft | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const mutation = useMutation({ mutationFn: sendChat })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [items, mutation.isPending])

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
    <div className="flex h-dvh flex-col">
      <header className="shrink-0 border-b border-line px-5 py-4">
        <div className="mx-auto flex w-full max-w-3xl items-baseline justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-wide text-accent uppercase">{copy.brand}</p>
            <h1 className="font-serif text-2xl text-ink">{copy.title}</h1>
          </div>
          <button
            type="button"
            onClick={toggleLocale}
            className="rounded-full border border-line bg-panel px-3 py-1.5 text-sm font-semibold text-ink hover:border-accent"
            aria-label={copy.languageToggleLabel}
          >
            {copy.languageToggle}
          </button>
        </div>
      </header>
      <main className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-5">
        <div className="min-h-0 flex-1 overflow-y-auto">
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
                  {item.kind === "error" && (
                    <p className="rounded-2xl border border-danger/20 bg-danger-bg px-4 py-3 text-sm text-danger" role="alert">
                      {item.text}
                    </p>
                  )}
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
        <Composer key={copy.documentTitle} pending={mutation.isPending} draft={draft} onSend={ask} />
      </main>
    </div>
  )
}
