import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"

import { fetchMetrics, fetchTraces } from "@/api/llmops"
import { EvaluationPanel } from "@/components/ops/EvaluationPanel"
import { GroupTable } from "@/components/ops/GroupTable"
import { MetricsOverview } from "@/components/ops/MetricsOverview"
import { Section } from "@/components/ops/Section"
import { TraceTable } from "@/components/ops/TraceTable"
import { ErrorAlert } from "@/components/ui/ErrorAlert"
import { PageHeader } from "@/components/ui/PageHeader"
import { pillButton } from "@/components/ui/styles"
import { useLocale } from "@/i18n/LocaleProvider"

const REFRESH_MS = 15_000
const RECENT_TRACES = 20

export function OpsScreen() {
  const { copy } = useLocale()
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics, refetchInterval: REFRESH_MS })
  const traces = useQuery({
    queryKey: ["traces", RECENT_TRACES],
    queryFn: () => fetchTraces(RECENT_TRACES),
    refetchInterval: REFRESH_MS,
  })

  return (
    <div className="min-h-dvh">
      <PageHeader
        kicker={copy.ops.kicker}
        title={copy.ops.title}
        width="max-w-5xl"
        actions={
          <Link to="/" className={pillButton}>
            {copy.ops.back}
          </Link>
        }
      />
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-5 py-8">
        <p className="max-w-2xl text-sm leading-relaxed text-ink-soft">{copy.ops.lead}</p>
        {metrics.isError && <ErrorAlert message={copy.ops.loadFailed} />}
        {metrics.isPending && <p className="text-sm text-muted">{copy.ops.loading}</p>}
        {metrics.data && (
          <>
            <MetricsOverview metrics={metrics.data} />
            <Section title={copy.ops.byVersion} hint={copy.ops.byVersionHint}>
              <GroupTable groups={metrics.data.by_prompt_version} />
            </Section>
            <Section title={copy.ops.byModel}>
              <GroupTable groups={metrics.data.by_model} />
            </Section>
          </>
        )}
        <Section title={copy.ops.recentTraces}>
          <TraceTable traces={traces.data ?? []} />
        </Section>
        <EvaluationPanel />
      </main>
    </div>
  )
}
