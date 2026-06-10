import { get } from './client'
import type { Lot, LotAnimalsResponse, AdgResponse } from '@/types/lot'
import type { PaginatedResponse } from '@/types/event'

export function getLots(params?: { page?: number; limit?: number }): Promise<PaginatedResponse<Lot>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.limit) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return get<PaginatedResponse<Lot>>(`/lots${query ? `?${query}` : ''}`)
}

export function getLotAnimals(lotId: string): Promise<LotAnimalsResponse> {
  return get<LotAnimalsResponse>(`/lots/${lotId}/animals`)
}

export interface AdgParams {
  from: string
  to: string
  min_days?: number
}

export function getLotAdg(lotId: string, params: AdgParams): Promise<AdgResponse> {
  const qs = new URLSearchParams({ from: params.from, to: params.to })
  if (params.min_days !== undefined) qs.set('min_days', String(params.min_days))
  return get<AdgResponse>(`/lots/${lotId}/adg?${qs.toString()}`)
}
