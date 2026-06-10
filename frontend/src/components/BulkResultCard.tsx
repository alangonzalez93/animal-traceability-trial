import { useState } from 'react'
import type { BulkResult } from '@/types/animal'

interface Props {
  result: BulkResult
}

export function BulkResultCard({ result }: Props) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-2">
      <div className="flex gap-6">
        <span className="text-sm font-medium text-green-600">
          {result.created} creados
        </span>
        <span className="text-sm font-medium text-destructive">
          {result.failed.length} fallidos
        </span>
      </div>
      {result.failed.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-muted-foreground underline"
          >
            {expanded ? 'Ocultar detalles' : 'Ver detalles'}
          </button>
          {expanded && (
            <ul className="mt-2 space-y-1">
              {result.failed.map((f, i) => (
                <li key={i} className="text-xs text-destructive font-mono bg-destructive/5 rounded px-2 py-1">
                  {JSON.stringify(f)}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
