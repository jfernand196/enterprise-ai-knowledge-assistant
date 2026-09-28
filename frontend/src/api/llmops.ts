import type { EvaluationReport, EvaluationSummary, Metrics, Rating, Trace } from "@/domain/llmops"
import { copy, readLocale } from "@/i18n/copy"

const EVALUATION_TIMEOUT_MS = 600_000

export async function sendFeedback(requestId: string, rating: Rating): Promise<void> {
  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_id: requestId, rating }),
  })
  if (!response.ok) {
    throw new Error(copy[readLocale()].feedbackFailed)
  }
}

export function fetchMetrics(): Promise<Metrics> {
  return getJson("/api/metrics")
}

export function fetchTraces(limit: number): Promise<Trace[]> {
  return getJson(`/api/traces?limit=${limit}`)
}

export function fetchEvaluations(): Promise<EvaluationSummary[]> {
  return getJson("/api/evaluations")
}

export async function runEvaluation(): Promise<EvaluationReport> {
  const response = await fetch("/api/evaluations", {
    method: "POST",
    signal: AbortSignal.timeout(EVALUATION_TIMEOUT_MS),
  })
  if (!response.ok) {
    throw new Error(copy[readLocale()].ops.loadFailed)
  }
  return response.json() as Promise<EvaluationReport>
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(copy[readLocale()].ops.loadFailed)
  }
  return response.json() as Promise<T>
}
