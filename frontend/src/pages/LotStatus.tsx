import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useLots } from '@/hooks/useLots'
import { useLotAnimals } from '@/hooks/useLotAnimals'
import { Skeleton } from '@/components/ui/skeleton'
import { StatCard } from '@/components/StatCard'
import { ErrorMessage } from '@/components/ErrorMessage'
import { Topbar } from '@/components/layout/Topbar'
import { IconDownload } from '@tabler/icons-react'
import { formatDate } from '@/lib/format'
import type { AnimalCategory } from '@/types/animal'

const PAGE_SIZE = 20

const STATUS_CLS: Record<string, string> = {
  ACTIVE: 'bg-[#dcfce7] text-[#15803d]',
  DEAD:   'bg-[#fee2e2] text-[#dc2626]',
  SOLD:   'bg-[#fef9c3] text-[#854d0e]',
}

export function LotStatus() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const { data: lots, isLoading: loadingLots } = useLots()
  const activeLotId = searchParams.get('lot') ?? lots?.data[0]?.id ?? ''
  const { data: lotAnimals, isLoading: loadingAnimals, error } = useLotAnimals(activeLotId)

  const activeLotName = lots?.data.find((l) => l.id === activeLotId)?.name ?? ''

  const animals = lotAnimals?.animals ?? []
  const filtered = animals.filter(
    (a) =>
      a.tag_number.toLowerCase().includes(search.toLowerCase()) ||
      a.breed.toLowerCase().includes(search.toLowerCase()),
  )

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const activeCount = animals.filter((a) => a.status === 'ACTIVE').length
  const categories = animals.reduce<Record<string, number>>((acc, a) => {
    acc[a.category] = (acc[a.category] ?? 0) + 1
    return acc
  }, {})
  const categoryText = Object.entries(categories).map(([k, v]) => `${v} ${k}`).join(', ')

  function selectLot(id: string) {
    setSearchParams({ lot: id })
    setPage(1)
    setSearch('')
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Topbar
        title="Estado de lote"
        actions={
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#dde1e7] bg-white text-[13px] font-medium text-[#374151] hover:bg-[#f9fafb] transition-colors">
            <IconDownload size={14} />
            Exportar
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* Lot dropdown */}
        {loadingLots ? (
          <Skeleton className="h-9 w-48 rounded-lg" />
        ) : (
          <select
            className="px-3 py-2 border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] bg-white outline-none focus:border-[#2563eb]"
            value={activeLotId}
            onChange={(e) => selectLot(e.target.value)}
          >
            {lots?.data.map((lot) => (
              <option key={lot.id} value={lot.id}>{lot.name}</option>
            ))}
          </select>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 max-w-xs">
          <StatCard label="Animales activos" value={activeCount} />
          <StatCard label="Categorías" value={Object.keys(categories).length} sub={categoryText || '—'} />
        </div>

        {/* Card with table */}
        <div className="bg-white border border-[#e8eaed] rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-[#e8eaed] flex items-center justify-between">
            <div>
              <p className="text-[14px] font-semibold text-[#1a1a2e]">{activeLotName}</p>
              {!loadingAnimals && (
                <p className="text-[12px] text-[#9aa0ac] mt-0.5">{animals.length} animales</p>
              )}
            </div>
            <input
              className="px-3 py-1.5 border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] bg-white outline-none focus:border-[#2563eb] placeholder:text-[#9aa0ac] w-48"
              placeholder="Buscar caravana…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            />
          </div>

          {error ? (
            <div className="p-5"><ErrorMessage error={error} /></div>
          ) : loadingAnimals ? (
            <div className="p-5 space-y-2">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-[13px] text-[#9aa0ac]">
              {animals.length === 0 ? 'Este lote no tiene animales' : 'Sin resultados'}
            </div>
          ) : (
            <>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    {['Caravana', 'Raza', 'Categoría', 'Estado', 'Fecha nac.'].map((h) => (
                      <th
                        key={h}
                        className="text-[11px] font-semibold text-[#9aa0ac] uppercase tracking-[0.5px] text-left px-5 py-2.5 bg-[#fafbfc] border-b border-[#e8eaed]"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((a) => (
                    <tr key={a.id} className="hover:bg-[#fafbff] transition-colors">
                      <td className="px-5 py-3 text-[13px] text-[#374151] border-b border-[#f0f2f5] font-semibold">
                        {a.tag_number}
                      </td>
                      <td className="px-5 py-3 text-[13px] text-[#374151] border-b border-[#f0f2f5]">
                        {a.breed}
                      </td>
                      <td className="px-5 py-3 text-[13px] text-[#374151] border-b border-[#f0f2f5]">
                        {a.category as AnimalCategory}
                      </td>
                      <td className="px-5 py-3 border-b border-[#f0f2f5]">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${STATUS_CLS[a.status] ?? ''}`}>
                          {a.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-[13px] text-[#9aa0ac] border-b border-[#f0f2f5]">
                        {a.birth_date ? formatDate(a.birth_date) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="flex items-center justify-between px-5 py-3 border-t border-[#e8eaed] text-[12px] text-[#9aa0ac]">
                <span>
                  {filtered.length} animales · página {page} de {totalPages}
                </span>
                <div className="flex gap-1.5">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`px-2.5 py-1 border rounded-md text-[12px] transition-colors ${
                        p === page
                          ? 'bg-[#eff6ff] border-[#2563eb] text-[#2563eb] font-semibold'
                          : 'border-[#e8eaed] bg-white text-[#374151] hover:bg-[#f0f4ff] hover:border-[#2563eb] hover:text-[#2563eb]'
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
