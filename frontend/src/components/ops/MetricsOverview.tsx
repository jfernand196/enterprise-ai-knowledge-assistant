import type { Metrics } from "@/domain/llmops"
import { useLocale } from "@/i18n/LocaleProvider"
import { formatCost, formatLatency, formatNumber, formatPercent } from "@/lib/format"

export function MetricsOverview({ metrics }: { metrics: Metrics }) {
  const { copy, locale } = useLocale()
  const votes = metrics.feedback_up + metrics.feedback_down

  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <Stat label={copy.ops.requests} value={formatNumber(metrics.requests, locale)} />
      <Stat label={copy.ops.avgLatency} value={formatLatency(metrics.avg_latency_ms)} />
      <Stat label={copy.ops.p95Latency} value={formatLatency(metrics.p95_latency_ms)} />
      <Stat
        label={copy.ops.tokens}
        value={`${formatNumber(metrics.input_tokens, locale)} / ${formatNumber(metrics.output_tokens, locale)}`}
      />
      <Stat label={copy.ops.cost} value={formatCost(metrics.cost_usd)} />
      <Stat
        label={copy.ops.satisfaction}
        value={votes === 0 ? copy.ops.noFeedback : formatPercent(metrics.satisfaction)}
        detail={votes > 0 ? `👍 ${metrics.feedback_up} · 👎 ${metrics.feedback_down}` : undefined}
      />
    </dl>
  )
}

function Stat({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-panel px-4 py-3">
      <dt className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</dt>
      <dd className="mt-1 text-lg font-semibold text-ink tabular-nums">{value}</dd>
      {detail && <dd className="mt-0.5 text-xs text-muted">{detail}</dd>}
    </div>
  )
}
