import type { Locale } from "@/i18n/copy"

export const EMPTY_VALUE = "—"

const INTL_LOCALE: Record<Locale, string> = { es: "es-CO", en: "en-US" }
const MS_PER_SECOND = 1000
const MS_PER_MINUTE = 60_000

export function formatLatency(latencyMs: number): string {
  if (latencyMs < MS_PER_MINUTE) {
    return `${(latencyMs / MS_PER_SECOND).toFixed(1)} s`
  }
  const totalSeconds = Math.round(latencyMs / MS_PER_SECOND)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes} min ${seconds} s`
}

export function formatPercent(value: number | null): string {
  return value === null ? EMPTY_VALUE : `${Math.round(value * 100)} %`
}

export function formatCost(usd: number): string {
  return `$${usd.toFixed(4)}`
}

export function formatNumber(value: number, locale: Locale): string {
  return value.toLocaleString(INTL_LOCALE[locale])
}

export function formatTime(iso: string, locale: Locale): string {
  return new Date(iso).toLocaleString(INTL_LOCALE[locale], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}
