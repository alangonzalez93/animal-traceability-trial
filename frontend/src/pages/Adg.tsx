import { useSearchParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { useLots } from '@/hooks/useLots'
import { getLotAdg } from '@/api/lots'
import { StatCard } from '@/components/StatCard'
import { ErrorMessage } from '@/components/ErrorMessage'
import { Skeleton } from '@/components/ui/skeleton'
import { Topbar } from '@/components/layout/Topbar'
import { IconDownload } from '@tabler/icons-react'
import { formatDecimal } from '@/lib/format'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Cell, ResponsiveContainer,
} from 'recharts'

const DEFAULT_FROM = '2026-01-01T00:00:00'
const DEFAULT_TO = '2026-06-10T00:00:00'

function PerformanceBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0
  const color = pct >= 99 ? '#2563eb' : pct >= 70 ? '#16a34a' : '#ea580c'
  return (
    <div>
      <div className="flex justify-between text-[11px] text-[#9aa0ac] mb-1">
        <span>Rendimiento relativo</span>
        <span>{Math.round(pct)}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-[#f0f2f5] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  )
}

export function Adg() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: lots } = useLots()

  const selectedLot = searchParams.get('lot') ?? 'all'
  const from = searchParams.get('from') ?? DEFAULT_FROM
  const to = searchParams.get('to') ?? DEFAULT_TO
  const minDays = Number(searchParams.get('min_days') ?? '15')

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams)
    next.set(key, value)
    setSearchParams(next)
  }

  const lotsToQuery =
    selectedLot === 'all'
      ? (lots?.data ?? [])
      : (lots?.data.filter((l) => l.id === selectedLot) ?? [])

  const results = useQueries({
    queries: lotsToQuery.map((lot) => ({
      queryKey: ['lot-adg', lot.id, from, to, minDays],
      queryFn: () => getLotAdg(lot.id, { from, to, min_days: minDays }),
      enabled: Boolean(lots),
    })),
  })

  const loading = results.some((r) => r.isLoading)
  const error = results.find((r) => r.error)?.error
  const adgData = results.flatMap((r) => (r.data ? [r.data] : []))
  const adg = (d: typeof adgData[0]) => (d.avg_adg_kg_day !== null ? Number(d.avg_adg_kg_day) : 0)
  const maxAvg = Math.max(...adgData.map(adg), 0)
  const globalAvg = adgData.length
    ? adgData.reduce((s, d) => s + adg(d), 0) / adgData.length
    : null
  const bestLot = adgData.reduce<typeof adgData[0] | null>(
    (best, d) => (!best || adg(d) > adg(best) ? d : best),
    null,
  )
  const totalAnimals = adgData.reduce((s, d) => s + d.animals_count, 0)

  const selectedLotLabel =
    selectedLot === 'all'
      ? 'Todos los lotes'
      : (lots?.data.find((l) => l.id === selectedLot)?.name ?? 'Seleccionar lote')

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Topbar
        title="ADPV — Ganancia diaria de peso"
        actions={
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#dde1e7] bg-white text-[13px] font-medium text-[#374151] hover:bg-[#f9fafb] transition-colors">
            <IconDownload size={14} />
            Exportar
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* Filters */}
        <div className="flex flex-wrap gap-2.5 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium text-[#9aa0ac] uppercase tracking-[0.5px]">Lote</label>
            <select
              className="px-3 py-2 border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] bg-white outline-none focus:border-[#2563eb]"
              value={selectedLot}
              onChange={(e) => setParam('lot', e.target.value)}
            >
              <option value="all">Todos los lotes</option>
              {lots?.data.map((l) => (
                <option key={l.id} value={l.id}>{l.name}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium text-[#9aa0ac] uppercase tracking-[0.5px]">Desde</label>
            <input
              type="date"
              className="px-3 py-2 border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] bg-white outline-none focus:border-[#2563eb]"
              value={from.slice(0, 10)}
              onChange={(e) => setParam('from', e.target.value + 'T00:00:00')}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium text-[#9aa0ac] uppercase tracking-[0.5px]">Hasta</label>
            <input
              type="date"
              className="px-3 py-2 border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] bg-white outline-none focus:border-[#2563eb]"
              value={to.slice(0, 10)}
              onChange={(e) => setParam('to', e.target.value + 'T00:00:00')}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium text-[#9aa0ac] uppercase tracking-[0.5px]">Mín. días</label>
            <input
              type="number"
              min={0}
              className="px-3 py-2 border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] bg-white outline-none focus:border-[#2563eb] w-24"
              value={minDays}
              onChange={(e) => setParam('min_days', e.target.value)}
            />
          </div>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Lotes analizados" value={adgData.length} />
          <StatCard label="Total animales" value={totalAnimals} />
          <StatCard
            label="ADG promedio global"
            value={globalAvg !== null ? `${formatDecimal(globalAvg)} kg/día` : '—'}
          />
          <StatCard label="Mejor lote" value={bestLot?.lot_name ?? '—'} />
        </div>

        {error && <ErrorMessage error={error} />}

        {/* Bar chart */}
        {!loading && adgData.length > 0 && (
          <div className="bg-white border border-[#e8eaed] rounded-xl p-5">
            <p className="text-[11px] font-semibold text-[#9aa0ac] uppercase tracking-[0.5px] mb-4">
              ADPV por lote (kg/día)
            </p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={adgData.map((d) => ({ name: d.lot_name, value: adg(d) }))}
                margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
                barCategoryGap="30%"
              >
                <CartesianGrid vertical={false} stroke="#f0f2f5" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: '#9aa0ac' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#9aa0ac' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${v}`}
                />
                <Tooltip
                  cursor={{ fill: '#f0f4ff' }}
                  contentStyle={{
                    border: '1px solid #e8eaed',
                    borderRadius: 8,
                    fontSize: 12,
                    color: '#374151',
                  }}
                  formatter={(v: number) => [`${formatDecimal(v)} kg/día`, 'ADPV']}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {adgData.map((d) => {
                    const pct = maxAvg > 0 ? adg(d) / maxAvg : 0
                    const fill = pct >= 0.9 ? '#2563eb' : pct >= 0.7 ? '#16a34a' : '#ea580c'
                    return <Cell key={d.lot_id} fill={fill} />
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* ADG cards */}
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-36 rounded-xl" />)}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {adgData.map((d) => (
              <div key={d.lot_id} className="bg-white border border-[#e8eaed] rounded-xl p-5 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-[16px] font-bold text-[#1a1a2e]">{d.lot_name}</p>
                    <p className="text-[12px] text-[#9aa0ac] mt-0.5">{d.animals_count} animales medidos</p>
                  </div>
                  {d.avg_adg_kg_day !== null && d.animals_count > 0 && (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                      adg(d) / maxAvg >= 0.9
                        ? 'bg-[#dcfce7] text-[#15803d]'
                        : adg(d) / maxAvg >= 0.7
                          ? 'bg-[#dbeafe] text-[#1d4ed8]'
                          : 'bg-[#fef9c3] text-[#854d0e]'
                    }`}>
                      {adg(d) / maxAvg >= 0.9 ? 'Mejor rendimiento' : adg(d) / maxAvg >= 0.7 ? 'En progreso' : 'Bajo rendimiento'}
                    </span>
                  )}
                </div>

                {d.avg_adg_kg_day === null || d.animals_count === 0 ? (
                  <p className="text-[13px] text-[#9aa0ac] italic">Sin datos suficientes</p>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="text-center py-3 bg-[#fafbfc] rounded-lg">
                        <p className="text-[22px] font-bold text-[#2563eb]">{formatDecimal(d.avg_adg_kg_day)}</p>
                        <p className="text-[11px] text-[#9aa0ac] mt-1">ADG prom. (kg/día)</p>
                      </div>
                      <div className="text-center py-3 bg-[#fafbfc] rounded-lg">
                        <p className="text-[22px] font-bold text-[#9aa0ac]">{d.animals_count}</p>
                        <p className="text-[11px] text-[#9aa0ac] mt-1">Animales medidos</p>
                      </div>
                    </div>
                    <PerformanceBar value={adg(d)} max={maxAvg} />
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
