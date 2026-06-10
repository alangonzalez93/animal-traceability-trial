import { useQuery } from '@tanstack/react-query'
import { getLotAdg } from '@/api/lots'
import type { AdgParams } from '@/api/lots'

export function useLotAdg(lotId: string, params: AdgParams) {
  return useQuery({
    queryKey: ['lot-adg', lotId, params.from, params.to, params.min_days],
    queryFn: () => getLotAdg(lotId, params),
    enabled: Boolean(lotId) && Boolean(params.from) && Boolean(params.to),
  })
}
