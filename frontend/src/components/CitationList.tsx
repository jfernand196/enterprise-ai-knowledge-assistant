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

  return (
    <section className="mt-5 border-t border-line pt-4" aria-label={copy.sources}>
      <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">{copy.sources}</h3>
      <ul className="mt-2">
        {sources.map((citation) => (
          <li key={citation.doc_id} className="py-2.5">
            <div className="flex items-baseline justify-between gap-4">
              <p className="text-sm font-semibold text-ink">{citation.title}</p>
              <p className="shrink-0 text-xs text-muted">
                {copy.categories[citation.category] ?? citation.category}
              </p>
            </div>
            <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-ink-soft">
              {readableExcerpt(citation.excerpt)}
            </p>
          </li>
        ))}
      </ul>
    </section>
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

function readableExcerpt(excerpt: string): string {
  const clean = excerpt.replace(/\s+/g, " ").trim()
  const cut = clean.match(/^(.*?)(?:\.{3}|…)$/)
  if (!cut) {
    return clean
  }
  let body = cut[1].trimEnd()
  const lastSpace = body.lastIndexOf(" ")
  const lastToken = lastSpace === -1 ? body : body.slice(lastSpace + 1)
  if (lastToken.length > 0 && lastToken.length < 8 && !/[.!?]$/.test(lastToken)) {
    body = lastSpace === -1 ? "" : body.slice(0, lastSpace)
  }
  return body ? `${body}…` : clean
}
