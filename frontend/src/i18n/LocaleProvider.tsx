import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

import { copy, readLocale, storeLocale, type Copy, type Locale } from "@/i18n/copy"

interface LocaleContextValue {
  locale: Locale
  copy: Copy
  toggleLocale: () => void
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(readLocale)

  useEffect(() => {
    storeLocale(locale)
    document.documentElement.lang = locale
    document.title = copy[locale].documentTitle
  }, [locale])

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      copy: copy[locale],
      toggleLocale: () => setLocale((current) => (current === "es" ? "en" : "es")),
    }),
    [locale],
  )

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale(): LocaleContextValue {
  const value = useContext(LocaleContext)
  if (!value) {
    throw new Error("useLocale must be used within LocaleProvider")
  }
  return value
}
