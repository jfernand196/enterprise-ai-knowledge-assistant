import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { fetchEvaluations, runEvaluation } from "@/api/llmops"
import { Section } from "@/components/ops/Section"
import { bodyCell, headCell, mutedCell, numberCell, numberHeadCell, TableFrame } from "@/components/ops/Table"
import { ErrorAlert } from "@/components/ui/ErrorAlert"
import type { EvaluationReport, EvaluationSummary } from "@/domain/llmops"
import { useLocale } from "@/i18n/LocaleProvider"
import { EMPTY_VALUE, formatLatency, formatPercent, formatTime } from "@/lib/format"

const EVALUATIONS_KEY = ["evaluations"]

export function EvaluationPanel() {
  const { copy } = useLocale()
  const queryClient = useQueryClient()
  const history = useQuery({ queryKey: EVALUATIONS_KEY, queryFn: fetchEvaluations })
  const run = useMutation({
    mutationFn: runEvaluation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EVALUATIONS_KEY }),
  })

  return (
    <Section
      title={copy.ops.evaluation}
      hint={copy.ops.evaluationHint}
      action={
        <button
          type="button"
          onClick={() => run.mutate()}
          disabled={run.isPending}
          className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-strong disabled:opacity-60"
        >
          {run.isPending ? copy.ops.runningEvaluation : copy.ops.runEvaluation}
        </button>
      }
    >
      {run.isError && <ErrorAlert message={run.error.message} />}
      {run.data && <ReportTable report={run.data} />}
      <h3 className="mt-2 text-sm font-semibold text-ink">{copy.ops.history}</h3>
      <HistoryTable runs={history.data ?? []} />
    </Section>
  )
}

function passedLabel(summary: EvaluationSummary): string {
  return `${summary.passed}/${summary.cases} (${formatPercent(summary.pass_rate)})`
}

function ReportTable({ report }: { report: EvaluationReport }) {
  const { copy } = useLocale()

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-ink">
        <span className="font-semibold">
          {copy.ops.passRate}: {passedLabel(report)}
        </span>
        <span className="text-muted"> · {report.prompt_version}</span>
      </p>
      <TableFrame>
        <thead>
          <tr>
            <th className={headCell}>{copy.ops.case}</th>
            <th className={headCell}>{copy.ops.checks}</th>
            <th className={headCell}>{copy.ops.model}</th>
            <th className={numberHeadCell}>{copy.latency}</th>
          </tr>
        </thead>
        <tbody>
          {report.results.map((result) => (
            <tr key={result.id}>
              <td className={`${bodyCell} min-w-56`}>
                <p className="font-medium">
                  <span className={result.passed ? "text-accent" : "text-danger"}>
                    {result.passed ? `✓ ${copy.ops.passed}` : `✗ ${copy.ops.failed}`}
                  </span>{" "}
                  {result.id}
                </p>
                <p className="mt-0.5 text-xs text-muted">{result.question}</p>
              </td>
              <td className={bodyCell}>
                <ul className="flex flex-wrap gap-1.5">
                  {Object.entries(result.checks).map(([name, ok]) => (
                    <li
                      key={name}
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${ok ? "bg-paper text-ink-soft" : "bg-danger-bg text-danger"}`}
                    >
                      {ok ? "✓" : "✗"} {name}
                    </li>
                  ))}
                </ul>
              </td>
              <td className={mutedCell}>{result.model || EMPTY_VALUE}</td>
              <td className={numberCell}>{formatLatency(result.latency_ms)}</td>
            </tr>
          ))}
        </tbody>
      </TableFrame>
    </div>
  )
}

function HistoryTable({ runs }: { runs: EvaluationSummary[] }) {
  const { copy, locale } = useLocale()

  if (runs.length === 0) {
    return <p className="text-sm text-muted">{copy.ops.noHistory}</p>
  }

  return (
    <TableFrame>
      <thead>
        <tr>
          <th className={headCell}>{copy.ops.when}</th>
          <th className={headCell}>{copy.ops.group}</th>
          <th className={numberHeadCell}>{copy.ops.passRate}</th>
          <th className={numberHeadCell}>{copy.ops.avgLatency}</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((item) => (
          <tr key={item.run_id}>
            <td className={mutedCell}>{formatTime(item.created_at, locale)}</td>
            <td className={`${bodyCell} whitespace-nowrap`}>{item.prompt_version}</td>
            <td className={numberCell}>{passedLabel(item)}</td>
            <td className={numberCell}>{formatLatency(item.avg_latency_ms)}</td>
          </tr>
        ))}
      </tbody>
    </TableFrame>
  )
}
