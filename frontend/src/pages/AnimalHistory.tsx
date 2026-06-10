import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAnimals } from '@/hooks/useAnimals'
import { useAnimalHistory } from '@/hooks/useAnimalHistory'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorMessage } from '@/components/ErrorMessage'
import { Topbar } from '@/components/layout/Topbar'
import { IconDownload } from '@tabler/icons-react'
import { formatDate } from '@/lib/format'
import type { EventType, AnimalEvent } from '@/types/event'
import type { Animal } from '@/types/animal'

const EVENT_TYPES: EventType[] = [
  'BIRTH', 'DEATH', 'SALE', 'MOVE', 'WEIGHT', 'VACCINATION', 'RECLASSIFICATION',
]

const EVENT_LABELS: Record<EventType, string> = {
  BIRTH: 'Nacimiento', DEATH: 'Muerte', SALE: 'Venta',
  MOVE: 'Movimiento', WEIGHT: 'Pesaje',
  VACCINATION: 'Vacunación', RECLASSIFICATION: 'Reclasificación',
}

const EVENT_TAG_CLS: Record<EventType, string> = {
  BIRTH:            'bg-[#dcfce7] text-[#15803d]',
  DEATH:            'bg-[#fee2e2] text-[#dc2626]',
  SALE:             'bg-[#fef9c3] text-[#854d0e]',
  MOVE:             'bg-[#dbeafe] text-[#1d4ed8]',
  WEIGHT:           'bg-[#f3e8ff] text-[#7e22ce]',
  VACCINATION:      'bg-[#fff7ed] text-[#c2410c]',
  RECLASSIFICATION: 'bg-[#f0f9ff] text-[#0369a1]',
}

const EVENT_DOT: Record<EventType, string> = {
  BIRTH: '#16a34a', DEATH: '#dc2626', SALE: '#ca8a04',
  MOVE: '#2563eb', WEIGHT: '#7c3aed',
  VACCINATION: '#ea580c', RECLASSIFICATION: '#0891b2',
}

function payloadSummary(event: AnimalEvent): string {
  if (!Object.keys(event.payload).length) return ''
  switch (event.type) {
    case 'WEIGHT': return `weight_kg: ${event.payload.weight_kg}`
    case 'VACCINATION': return `vaccine_name: ${event.payload.vaccine_name}`
    case 'RECLASSIFICATION': return `new_category: ${event.payload.new_category}`
    case 'MOVE': return `to_lot_id: ${event.payload.to_lot_id}`
    default: return Object.entries(event.payload).map(([k, v]) => `${k}: ${v}`).join(' · ')
  }
}

export function AnimalHistory() {
  const [searchParams, setSearchParams] = useSearchParams()
  const animalId = searchParams.get('animal') ?? ''
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const { data: animals, isLoading: loadingAnimals } = useAnimals(debouncedSearch)
  const { data: history, isLoading: loadingHistory, error } = useAnimalHistory(animalId, page)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node))
        setShowDropdown(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function selectAnimal(animal: Animal) {
    setSearch(animal.tag_number)
    setShowDropdown(false)
    setPage(1)
    setSearchParams({ animal: animal.id })
  }

  const filtered = history?.data.filter(
    (e) => typeFilter === 'all' || e.type === typeFilter,
  )

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Topbar
        title="Historial animal"
        actions={
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#dde1e7] bg-white text-[13px] font-medium text-[#374151] hover:bg-[#f9fafb] transition-colors">
            <IconDownload size={14} />
            Exportar
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        {/* Filter row */}
        <div className="flex gap-2.5 mb-5">
          <div className="relative flex-1 max-w-xs" ref={dropdownRef}>
            <input
              className="w-full px-3 py-2 border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] bg-white outline-none focus:border-[#2563eb] placeholder:text-[#9aa0ac]"
              placeholder="Buscar por número de caravana…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setShowDropdown(true) }}
              onFocus={() => debouncedSearch.length >= 2 && setShowDropdown(true)}
            />
            {showDropdown && debouncedSearch.length >= 2 && (
              <div className="absolute z-10 mt-1 w-full rounded-lg border border-[#e8eaed] bg-white shadow-md overflow-hidden">
                {loadingAnimals ? (
                  <div className="px-3 py-2 text-[13px] text-[#9aa0ac]">Buscando…</div>
                ) : animals?.data.length === 0 ? (
                  <div className="px-3 py-2 text-[13px] text-[#9aa0ac]">Sin resultados</div>
                ) : (
                  animals?.data.map((a) => (
                    <button
                      key={a.id}
                      className="w-full text-left px-3 py-2 text-[13px] hover:bg-[#f0f4ff] border-b border-[#f0f2f5] last:border-0"
                      onMouseDown={() => selectAnimal(a)}
                    >
                      <span className="font-semibold text-[#1a1a2e]">{a.tag_number}</span>
                      <span className="ml-2 text-[#9aa0ac]">
                        {a.breed} · {a.category} · {a.status}
                      </span>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          <select
            className="px-3 py-2 border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] bg-white outline-none focus:border-[#2563eb]"
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
          >
            <option value="all">Todos los eventos</option>
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>{EVENT_LABELS[t]}</option>
            ))}
          </select>
        </div>

        {/* Content */}
        {!animalId ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#e8eaed] bg-white p-16 text-center">
            <p className="text-[13px] text-[#9aa0ac]">
              Buscá un animal por número de caravana para ver su historial
            </p>
          </div>
        ) : error ? (
          <ErrorMessage error={error} />
        ) : (
          <div className="bg-white border border-[#e8eaed] rounded-xl overflow-hidden">
            {/* Card header */}
            <div className="px-5 py-4 border-b border-[#e8eaed] flex items-center justify-between">
              <div>
                <p className="text-[14px] font-semibold text-[#1a1a2e]">Línea de tiempo</p>
                {history && (
                  <p className="text-[12px] text-[#9aa0ac] mt-0.5">
                    {filtered?.length ?? 0} evento{filtered?.length !== 1 ? 's' : ''}
                  </p>
                )}
              </div>
            </div>

            {/* Timeline */}
            {loadingHistory ? (
              <div className="p-5 space-y-3">
                {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : filtered?.length === 0 ? (
              <div className="py-12 text-center text-[13px] text-[#9aa0ac]">
                No hay eventos{typeFilter !== 'all' ? ` de tipo ${EVENT_LABELS[typeFilter as EventType]}` : ''}
              </div>
            ) : (
              <div>
                {filtered?.map((event, i) => (
                  <div key={event.id} className="flex px-5">
                    {/* Dot + line */}
                    <div className="flex flex-col items-center w-9 shrink-0">
                      <div
                        className="w-2.5 h-2.5 rounded-full shrink-0 mt-[15px]"
                        style={{ background: EVENT_DOT[event.type] ?? '#9aa0ac' }}
                      />
                      {i < (filtered?.length ?? 0) - 1 && (
                        <div className="w-0.5 bg-[#f0f2f5] flex-1 min-h-5" />
                      )}
                    </div>
                    {/* Content */}
                    <div className={`flex-1 py-2.5 pl-3 ${i < (filtered?.length ?? 0) - 1 ? 'border-b border-[#f0f2f5]' : ''}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${EVENT_TAG_CLS[event.type]}`}>
                          {EVENT_LABELS[event.type]}
                        </span>
                        <span className="text-[11px] text-[#9aa0ac]">
                          {formatDate(event.occurred_at)}
                        </span>
                      </div>
                      {payloadSummary(event) && (
                        <span className="text-[12px] text-[#9aa0ac] font-mono bg-[#f8f9fa] px-2 py-0.5 rounded-md">
                          {payloadSummary(event)}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination */}
            <div className="flex items-center justify-between px-5 py-3 border-t border-[#e8eaed] text-[12px] text-[#9aa0ac]">
              <span>Página {page}</span>
              <div className="flex gap-1.5">
                <button
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-2.5 py-1 border border-[#e8eaed] rounded-md bg-white text-[#374151] hover:bg-[#f0f4ff] hover:border-[#2563eb] hover:text-[#2563eb] disabled:opacity-40 disabled:cursor-default transition-colors"
                >
                  ←
                </button>
                <button
                  disabled={!history?.has_next}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-2.5 py-1 border border-[#e8eaed] rounded-md bg-white text-[#374151] hover:bg-[#f0f4ff] hover:border-[#2563eb] hover:text-[#2563eb] disabled:opacity-40 disabled:cursor-default transition-colors"
                >
                  →
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
