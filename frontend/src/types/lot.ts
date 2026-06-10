import type { Animal } from './animal'

export interface Lot {
  id: string
  name: string
  field_id: string
}

export interface LotAnimalsResponse {
  animals: Animal[]
}

export interface AdgResponse {
  lot_id: string
  lot_name: string
  period: { from: string; to: string }
  animals_count: number
  avg_adg_kg_day: string | null
}
