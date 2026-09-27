import Markdown from "react-markdown"

import { CitationList } from "@/components/CitationList"
import type { ChatReply } from "@/domain/chat"
import { useLocale } from "@/i18n/LocaleProvider"

interface AssistantMessageProps {
  reply: ChatReply
}

export function AssistantMessage({ reply }: AssistantMessageProps) {
  const { copy } = useLocale()
  const answer = presentAnswer(reply.answer)

  return (
    <article className="rounded-2xl border border-line bg-panel px-5 py-5">
      <div className="font-serif text-[1.125rem] leading-relaxed text-ink [&_li]:mt-1 [&_ol]:mt-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_p+p]:mt-3 [&_strong]:font-semibold [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5">
        <Markdown>{answer}</Markdown>
      </div>
      {reply.tool_calls.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2" aria-label={copy.toolsUsed}>
          {reply.tool_calls.map((call) => (
            <li key={`${call.name}-${JSON.stringify(call.arguments)}`} className="rounded-full bg-paper px-3 py-1 text-xs text-muted">
              {copy.tools[call.name] ?? call.name}
            </li>
          ))}
        </ul>
      )}
      <CitationList citations={reply.citations} answer={reply.answer} />
      <p className="mt-4 text-xs text-muted">
        {formatLatency(reply.latency_ms)} · {reply.model}
      </p>
    </article>
  )
}

function presentAnswer(answer: string): string {
  return answer
    .split("\n")
    .filter((line) => !isDocumentTitleLine(line))
    .join("\n")
    .trim()
}

function isDocumentTitleLine(line: string): boolean {
  const plain = line.trim().replace(/[*_#>`]/g, "")
  return /^document title\b/i.test(plain)
}

function formatLatency(latencyMs: number): string {
  if (latencyMs < 60_000) {
    return `${(latencyMs / 1000).toFixed(1)} s`
  }
  const totalSeconds = Math.round(latencyMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes} min ${seconds} s`
}
