export type Rating = "up" | "down"

export interface UsageSummary {
  requests: number
  blocked: number
  error_rate: number
  avg_latency_ms: number
  p95_latency_ms: number
  input_tokens: number
  output_tokens: number
  cost_usd: number
  rag_requests: number
  agent_requests: number
  feedback_up: number
  feedback_down: number
  satisfaction: number | null
}

export interface GroupMetrics extends UsageSummary {
  key: string
}

export interface Metrics extends UsageSummary {
  by_prompt_version: GroupMetrics[]
  by_model: GroupMetrics[]
}

export interface Trace {
  request_id: string
  user_id: string | null
  model: string
  prompt_version: string
  mode: string
  latency_ms: number
  input_tokens: number
  output_tokens: number
  cost_usd: number
  retrieved_documents: string[]
  tool_calls: string[]
  blocked: boolean
  blocked_reason: string | null
  question: string
  created_at: string
  feedback: Rating | null
  feedback_comment: string | null
}

export interface EvaluationCaseResult {
  id: string
  question: string
  user_id: string | null
  expected_mode: string
  mode: string
  passed: boolean
  checks: Record<string, boolean>
  answer: string
  model: string
  latency_ms: number
}

export interface EvaluationSummary {
  run_id: string
  created_at: string
  prompt_version: string
  cases: number
  passed: number
  pass_rate: number
  check_rates: Record<string, number>
  avg_latency_ms: number
  input_tokens: number
  output_tokens: number
}

export interface EvaluationReport extends EvaluationSummary {
  results: EvaluationCaseResult[]
}
