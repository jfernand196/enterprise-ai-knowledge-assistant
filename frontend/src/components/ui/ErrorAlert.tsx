export function ErrorAlert({ message }: { message: string }) {
  return (
    <p className="rounded-2xl border border-danger/20 bg-danger-bg px-4 py-3 text-sm text-danger" role="alert">
      {message}
    </p>
  )
}
