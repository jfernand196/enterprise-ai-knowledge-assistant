import { bodyCell, headCell, numberCell, numberHeadCell, TableFrame } from "@/components/ops/Table"
import type { GroupMetrics } from "@/domain/llmops"
import { useLocale } from "@/i18n/LocaleProvider"
import { formatCost, formatLatency, formatNumber, formatPercent } from "@/lib/format"

export function GroupTable({ groups }: { groups: GroupMetrics[] }) {
  const { copy, locale } = useLocale()

  if (groups.length === 0) {
    return <p className="text-sm text-muted">{copy.ops.noTraces}</p>
  }

  return (
    <TableFrame>
      <thead>
        <tr>
          <th className={headCell}>{copy.ops.group}</th>
          <th className={numberHeadCell}>{copy.ops.requests}</th>
          <th className={numberHeadCell}>{copy.ops.avgLatency}</th>
          <th className={numberHeadCell}>{copy.ops.p95Latency}</th>
          <th className={numberHeadCell}>{copy.tokenUnit}</th>
          <th className={numberHeadCell}>{copy.ops.cost}</th>
          <th className={numberHeadCell}>{copy.ops.satisfaction}</th>
          <th className={numberHeadCell}>{copy.ops.blocked}</th>
        </tr>
      </thead>
      <tbody>
        {groups.map((group) => (
          <tr key={group.key}>
            <td className={`${bodyCell} font-medium whitespace-nowrap`}>{group.key}</td>
            <td className={numberCell}>{formatNumber(group.requests, locale)}</td>
            <td className={numberCell}>{formatLatency(group.avg_latency_ms)}</td>
            <td className={numberCell}>{formatLatency(group.p95_latency_ms)}</td>
            <td className={numberCell}>
              {formatNumber(group.input_tokens, locale)} / {formatNumber(group.output_tokens, locale)}
            </td>
            <td className={numberCell}>{formatCost(group.cost_usd)}</td>
            <td className={numberCell}>{formatPercent(group.satisfaction)}</td>
            <td className={numberCell}>{group.blocked}</td>
          </tr>
        ))}
      </tbody>
    </TableFrame>
  )
}
