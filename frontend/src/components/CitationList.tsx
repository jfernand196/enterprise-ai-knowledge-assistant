import type { Citation } from "@/domain/chat"
import { useLocale } from "@/i18n/LocaleProvider"

interface CitationListProps {
  citations: Citation[]
  answer: string
}

export function CitationList({ citations, answer }: CitationListProps) {
  const { copy } = useLocale()
  const sources = orderSources(citations, answer)
  if (sources.length === 0) {
    return null
  }
  const answerText = answer.toLowerCase()
  const cited = sources.filter((source) => answerText.includes(source.title.toLowerCase()))
  const primary = cited.length > 0 ? cited : sources.slice(0, 1)
  const extra = sources.filter((source) => !primary.includes(source))

  return (
    <section className="mt-5 border-t border-line pt-4" aria-label={copy.sources}>
      <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">{copy.sources}</h3>
      <SourceList sources={primary} categoryLabel={copy.categories} />
      {extra.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-sm text-muted">{copy.alsoChecked}</summary>
          <SourceList sources={extra} categoryLabel={copy.categories} />
        </details>
      )}
    </section>
  )
}

function SourceList({
  sources,
  categoryLabel,
}: {
  sources: Citation[]
  categoryLabel: Record<string, string>
}) {
  return (
    <ul className="mt-2">
      {sources.map((citation) => (
        <li key={citation.doc_id} className="flex items-baseline justify-between gap-4 py-2">
          <p className="text-sm font-semibold text-ink">{citation.title}</p>
          <p className="shrink-0 text-xs text-muted">{categoryLabel[citation.category] ?? citation.category}</p>
        </li>
      ))}
    </ul>
  )
}

function orderSources(citations: Citation[], answer: string): Citation[] {
  const byDocument = new Map<string, Citation>()
  for (const citation of citations) {
    const current = byDocument.get(citation.doc_id)
    if (!current || citation.score > current.score) {
      byDocument.set(citation.doc_id, citation)
    }
  }
  const answerText = answer.toLowerCase()
  return [...byDocument.values()].sort((left, right) => {
    const leftNamed = answerText.includes(left.title.toLowerCase()) ? 1 : 0
    const rightNamed = answerText.includes(right.title.toLowerCase()) ? 1 : 0
    if (leftNamed !== rightNamed) {
      return rightNamed - leftNamed
    }
    return right.score - left.score
  })
}

