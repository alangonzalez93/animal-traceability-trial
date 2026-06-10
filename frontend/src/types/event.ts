export type EventType =
  | 'BIRTH'
  | 'DEATH'
  | 'SALE'
  | 'MOVE'
  | 'WEIGHT'
  | 'VACCINATION'
  | 'RECLASSIFICATION'

export interface AnimalEvent {
  id: string
  animal_id: string
  type: EventType
  occurred_at: string
  payload: Record<string, string>
}

export interface PaginatedResponse<T> {
  data: T[]
  page: number
  limit: number
  has_next: boolean
}
