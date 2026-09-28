import { bodyCell, headCell, mutedCell, numberCell, numberHeadCell, TableFrame } from "@/components/ops/Table"
import type { Trace } from "@/domain/llmops"
import { useLocale } from "@/i18n/LocaleProvider"
import { EMPTY_VALUE, formatLatency, formatTime } from "@/lib/format"

const VOTE_SYMBOL = { up: "👍", down: "👎" } as const
const BLOCKED_MODE = "blocked"

export function TraceTable({ traces }: { traces: Trace[] }) {
  const { copy, locale } = useLocale()

  if (traces.length === 0) {
    return <p className="text-sm text-muted">{copy.ops.noTraces}</p>
  }

  return (
    <TableFrame>
      <thead>
        <tr>
          <th className={headCell}>{copy.ops.when}</th>
          <th className={headCell}>{copy.ops.question}</th>
          <th className={headCell}>{copy.ops.mode}</th>
          <th className={headCell}>{copy.ops.model}</th>
          <th className={numberHeadCell}>{copy.latency}</th>
          <th className={numberHeadCell}>{copy.tokenUnit}</th>
          <th className={`${headCell} text-center`}>{copy.ops.feedback}</th>
        </tr>
      </thead>
      <tbody>
        {traces.map((trace) => (
          <tr key={trace.request_id}>
            <td className={mutedCell}>{formatTime(trace.created_at, locale)}</td>
            <td className={`${bodyCell} min-w-64`}>
              <p className="line-clamp-2">{trace.question || EMPTY_VALUE}</p>
              {trace.tool_calls.length > 0 && (
                <p className="mt-1 text-xs text-muted">{trace.tool_calls.map((name) => copy.tools[name] ?? name).join(" · ")}</p>
              )}
            </td>
            <td className={`${bodyCell} whitespace-nowrap`}>
              <ModeBadge mode={trace.mode} />
            </td>
            <td className={mutedCell}>
              {trace.model}
              <span className="block text-xs">{trace.prompt_version}</span>
            </td>
            <td className={numberCell}>{formatLatency(trace.latency_ms)}</td>
            <td className={numberCell}>
              {trace.input_tokens} / {trace.output_tokens}
            </td>
            <td className={`${bodyCell} text-center`} title={trace.feedback_comment ?? undefined}>
              {trace.feedback ? VOTE_SYMBOL[trace.feedback] : EMPTY_VALUE}
            </td>
          </tr>
        ))}
      </tbody>
    </TableFrame>
  )
}

function ModeBadge({ mode }: { mode: string }) {
  const tone = mode === BLOCKED_MODE ? "bg-danger-bg text-danger" : "bg-paper text-ink-soft"
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${tone}`}>{mode}</span>
}
