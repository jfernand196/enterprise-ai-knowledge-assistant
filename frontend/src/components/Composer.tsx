import { zodResolver } from "@hookform/resolvers/zod"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { EmployeeId } from "@/domain/chat"
import { useLocale } from "@/i18n/LocaleProvider"

interface ComposerDraft {
  nonce: string
  message: string
  userId: EmployeeId
}

interface ComposerProps {
  pending: boolean
  draft: ComposerDraft | null
  onSend: (message: string, userId?: EmployeeId) => void
}

export function Composer({ pending, draft, onSend }: ComposerProps) {
  const { copy } = useLocale()
  const schema = z.object({
    message: z.string().trim().min(1, copy.messageRequired).max(4000, copy.messageTooLong),
    userId: z.enum(["", "emp-1", "emp-2"]),
  })
  type ComposerValues = z.infer<typeof schema>

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ComposerValues>({
    resolver: zodResolver(schema),
    defaultValues: { message: "", userId: "" },
  })

  useEffect(() => {
    if (!draft) {
      return
    }
    reset({ message: draft.message, userId: draft.userId })
  }, [draft, reset])

  const submit = handleSubmit((values) => {
    const userId = values.userId === "" ? undefined : values.userId
    onSend(values.message, userId)
    reset({ message: "", userId: values.userId })
  })

  return (
    <form onSubmit={submit} className="shrink-0 border-t border-line bg-paper py-4" aria-busy={pending}>
      <div className="mb-3">
        <div className="flex items-center gap-3">
          <label className="text-sm text-muted" htmlFor="employee">
            {copy.employeeLabel}
          </label>
          <select
            id="employee"
            className="min-w-52 rounded-xl border border-line bg-panel px-3 py-2 text-sm text-ink outline-none focus-visible:border-accent"
            {...register("userId")}
          >
            <option value="">{copy.policiesOnly}</option>
            <option value="emp-1">Juan Perez</option>
            <option value="emp-2">Ana Gomez</option>
          </select>
        </div>
        <p className="mt-2 text-sm text-muted">{copy.employeeHint}</p>
      </div>
      <div className="flex items-end gap-3">
        <div className="min-w-0 flex-1">
          <label className="sr-only" htmlFor="message">
            {copy.questionLabel}
          </label>
          <textarea
            id="message"
            rows={2}
            placeholder={copy.placeholder}
            className="w-full resize-none rounded-2xl border border-line bg-panel px-4 py-3 text-base text-ink outline-none focus-visible:border-accent"
            {...register("message")}
          />
          {errors.message && <p className="mt-1 text-sm text-danger">{errors.message.message}</p>}
        </div>
        <button
          type="submit"
          disabled={pending}
          className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white hover:bg-accent-strong disabled:opacity-60"
        >
          {pending ? copy.searching : copy.ask}
        </button>
      </div>
    </form>
  )
}
