import { pillButton } from "@/components/ui/styles"
import { useLocale } from "@/i18n/LocaleProvider"

export function LocaleToggle() {
  const { copy, toggleLocale } = useLocale()

  return (
    <button type="button" onClick={toggleLocale} className={pillButton} aria-label={copy.languageToggleLabel}>
      {copy.languageToggle}
    </button>
  )
}
