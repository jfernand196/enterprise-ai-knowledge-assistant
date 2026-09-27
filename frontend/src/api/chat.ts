import type { ChatReply, ChatRequest } from "@/domain/chat"
import { copy, readLocale } from "@/i18n/copy"

const CHAT_TIMEOUT_MS = 90_000

export async function sendChat(request: ChatRequest): Promise<ChatReply> {
  let response: Response
  try {
    response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: request.message,
        ...(request.userId ? { user_id: request.userId } : {}),
      }),
      signal: AbortSignal.timeout(CHAT_TIMEOUT_MS),
    })
  } catch {
    throw new Error(copy[readLocale()].timeout)
  }

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return response.json() as Promise<ChatReply>
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
      return body.detail
    }
  } catch {
    return copy[readLocale()].requestFailed
  }
  return copy[readLocale()].requestFailed
}
