export type AnimalStatus = 'ACTIVE' | 'DEAD' | 'SOLD'
export type Breed = 'ANGUS' | 'HEREFORD' | 'BRAHMAN' | 'LIMOUSIN' | 'SHORTHORN' | 'CRIOLLO'
export type AnimalCategory = 'CALF' | 'STEER' | 'COW' | 'BULL' | 'HEIFER'

export interface Animal {
  id: string
  tag_number: string
  breed: Breed
  category: AnimalCategory
  status: AnimalStatus
  birth_date: string | null
  current_lot_id: string | null
}

export interface BulkResult {
  created: number
  failed: Record<string, unknown>[]
}
