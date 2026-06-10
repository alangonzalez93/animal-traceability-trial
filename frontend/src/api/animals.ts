import { get, postForm } from './client'
import type { Animal, BulkResult } from '@/types/animal'
import type { AnimalEvent, EventType, PaginatedResponse } from '@/types/event'

interface GetAnimalsParams {
  page?: number
  limit?: number
  status?: string
  lot_id?: string
  tag_number?: string
}

export function getAnimals(params?: GetAnimalsParams): Promise<PaginatedResponse<Animal>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.limit) qs.set('limit', String(params.limit))
  if (params?.status) qs.set('status', params.status)
  if (params?.lot_id) qs.set('lot_id', params.lot_id)
  if (params?.tag_number) qs.set('tag_number', params.tag_number)
  const query = qs.toString()
  return get<PaginatedResponse<Animal>>(`/animals${query ? `?${query}` : ''}`)
}

export function getAnimalHistory(
  id: string,
  page: number,
  limit: number,
): Promise<PaginatedResponse<AnimalEvent>> {
  return get<PaginatedResponse<AnimalEvent>>(
    `/animals/${id}/history?page=${page}&limit=${limit}`,
  )
}

export function bulkCreateAnimals(file: File): Promise<BulkResult> {
  const fd = new FormData()
  fd.append('file', file)
  return postForm<BulkResult>('/animals/bulk', fd)
}

export function bulkCreateEvents(type: EventType, file: File): Promise<BulkResult> {
  const fd = new FormData()
  fd.append('file', file)
  return postForm<BulkResult>(`/animals/bulk/events?type=${type}`, fd)
}
