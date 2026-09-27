export type EmployeeId = "emp-1" | "emp-2"

export interface ChatRequest {
  message: string
  userId?: EmployeeId
}

export interface Citation {
  title: string
  doc_id: string
  category: string
  score: number
  excerpt: string
}

export interface ToolCallResult {
  name: string
  arguments: Record<string, string>
  result: Record<string, unknown>
}

export interface ChatReply {
  request_id: string
  message: string
  answer: string
  sources: string[]
  citations: Citation[]
  tool_calls: ToolCallResult[]
  mode: string
  model: string
  latency_ms: number
  input_tokens: number
  output_tokens: number
}

export interface Suggestion {
  label: string
  message: string
  userId?: EmployeeId
}
