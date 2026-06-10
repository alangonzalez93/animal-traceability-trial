interface Props {
  error: unknown
}

export function ErrorMessage({ error }: Props) {
  const msg =
    error instanceof Error
      ? error.message
      : typeof error === 'object' && error !== null && 'detail' in error
        ? String((error as { detail: unknown }).detail)
        : 'Error inesperado'
  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
      {msg}
    </div>
  )
}
