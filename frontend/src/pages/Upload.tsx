import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { DropZone } from '@/components/DropZone'
import { BulkResultCard } from '@/components/BulkResultCard'
import { Topbar } from '@/components/layout/Topbar'
import { bulkCreateAnimals, bulkCreateEvents } from '@/api/animals'
import type { BulkResult } from '@/types/animal'
import type { EventType } from '@/types/event'
import { cn } from '@/lib/utils'

const EVENT_TYPES: EventType[] = ['WEIGHT', 'MOVE', 'VACCINATION', 'DEATH', 'SALE', 'BIRTH', 'RECLASSIFICATION']

const CSV_HINTS: Record<EventType, string> = {
  WEIGHT:           'tag_number, occurred_at, weight_kg',
  MOVE:             'tag_number, occurred_at, from_lot_id, to_lot_id',
  VACCINATION:      'tag_number, occurred_at, vaccine_name',
  RECLASSIFICATION: 'tag_number, occurred_at, new_category',
  DEATH:            'tag_number, occurred_at',
  SALE:             'tag_number, occurred_at',
  BIRTH:            'tag_number, occurred_at',
}

export function Upload() {
  const [animalFile, setAnimalFile] = useState<File | null>(null)
  const [eventFile, setEventFile] = useState<File | null>(null)
  const [eventType, setEventType] = useState<EventType>('WEIGHT')
  const [animalResult, setAnimalResult] = useState<BulkResult | null>(null)
  const [eventResult, setEventResult] = useState<BulkResult | null>(null)

  const animalMutation = useMutation({
    mutationFn: (file: File) => bulkCreateAnimals(file),
    onSuccess: (data) => setAnimalResult(data),
  })

  const eventMutation = useMutation({
    mutationFn: ({ type, file }: { type: EventType; file: File }) =>
      bulkCreateEvents(type, file),
    onSuccess: (data) => setEventResult(data),
  })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Topbar title="Carga de datos" />

      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Animals panel */}
          <div className="flex flex-col gap-4 bg-white border border-[#e8eaed] rounded-xl p-5">
            <div>
              <p className="text-[14px] font-semibold text-[#1a1a2e]">Registrar animales</p>
              <p className="text-[12px] text-[#9aa0ac] mt-0.5">Subí un CSV con los datos de los animales</p>
            </div>
            <DropZone
              onFile={setAnimalFile}
              hint="tag_number, breed, category, birth_date, lot_id, occurred_at"
            />
            {animalMutation.error && (
              <p className="text-[12px] text-[#dc2626]">{String(animalMutation.error)}</p>
            )}
            <button
              className={cn(
                'mt-auto flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-[13px] font-semibold transition-colors',
                animalFile && !animalMutation.isPending
                  ? 'bg-[#2563eb] text-white hover:bg-[#1d4ed8]'
                  : 'bg-[#e8eaed] text-[#9aa0ac] cursor-not-allowed',
              )}
              disabled={!animalFile || animalMutation.isPending}
              onClick={() => animalFile && animalMutation.mutate(animalFile)}
            >
              {animalMutation.isPending ? 'Cargando…' : 'Cargar animales'}
            </button>
          </div>

          {/* Events panel */}
          <div className="flex flex-col gap-4 bg-white border border-[#e8eaed] rounded-xl p-5">
            <div>
              <p className="text-[14px] font-semibold text-[#1a1a2e]">Registrar eventos</p>
              <p className="text-[12px] text-[#9aa0ac] mt-0.5">Seleccioná el tipo y subí el CSV</p>
            </div>

            {/* Type chips */}
            <div className="flex flex-wrap gap-1.5">
              {EVENT_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => setEventType(t)}
                  className={cn(
                    'px-2.5 py-1 rounded-full text-[11px] font-semibold transition-colors',
                    eventType === t
                      ? 'bg-[#2563eb] text-white'
                      : 'bg-[#f0f2f5] text-[#6b7280] hover:bg-[#dbeafe] hover:text-[#1d4ed8]',
                  )}
                >
                  {t}
                </button>
              ))}
            </div>

            <DropZone onFile={setEventFile} hint={CSV_HINTS[eventType]} />
            {eventMutation.error && (
              <p className="text-[12px] text-[#dc2626]">{String(eventMutation.error)}</p>
            )}
            <button
              className={cn(
                'mt-auto flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-[13px] font-semibold transition-colors',
                eventFile && !eventMutation.isPending
                  ? 'bg-[#2563eb] text-white hover:bg-[#1d4ed8]'
                  : 'bg-[#e8eaed] text-[#9aa0ac] cursor-not-allowed',
              )}
              disabled={!eventFile || eventMutation.isPending}
              onClick={() => eventFile && eventMutation.mutate({ type: eventType, file: eventFile })}
            >
              {eventMutation.isPending ? 'Cargando…' : 'Cargar eventos'}
            </button>
          </div>
        </div>

        {/* Results */}
        {(animalResult || eventResult) && (
          <div className="space-y-3">
            {animalResult && (
              <div>
                <p className="text-[11px] font-medium text-[#9aa0ac] uppercase tracking-[0.5px] mb-1.5">
                  Resultado — animales
                </p>
                <BulkResultCard result={animalResult} />
              </div>
            )}
            {eventResult && (
              <div>
                <p className="text-[11px] font-medium text-[#9aa0ac] uppercase tracking-[0.5px] mb-1.5">
                  Resultado — eventos
                </p>
                <BulkResultCard result={eventResult} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
