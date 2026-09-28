import Markdown from "react-markdown"

import { CitationList } from "@/components/CitationList"
import { FeedbackButtons } from "@/components/FeedbackButtons"
import type { ChatReply } from "@/domain/chat"
import { useLocale } from "@/i18n/LocaleProvider"
import { formatLatency } from "@/lib/format"

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
      <div className="mt-4 flex flex-wrap items-end justify-between gap-4 border-t border-line pt-3">
        <dl className="flex flex-wrap gap-x-6 gap-y-2" aria-label={copy.usageLabel}>
          <UsageStat label={copy.tokensUp} value={`${reply.input_tokens} ${copy.tokenUnit}`} />
          <UsageStat label={copy.tokensDown} value={`${reply.output_tokens} ${copy.tokenUnit}`} />
          <UsageStat label={copy.latency} value={formatLatency(reply.latency_ms)} />
        </dl>
        <FeedbackButtons requestId={reply.request_id} />
      </div>
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

function UsageStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-ink">{value}</dd>
    </div>
  )
}

function isDocumentTitleLine(line: string): boolean {
  const plain = line.trim().replace(/[*_#>`]/g, "")
  return /^document title\b/i.test(plain)
}

