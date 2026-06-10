import { useQuery } from '@tanstack/react-query'
import { getLotAnimals } from '@/api/lots'

export function useLotAnimals(lotId: string) {
  return useQuery({
    queryKey: ['lot-animals', lotId],
    queryFn: () => getLotAnimals(lotId),
    enabled: Boolean(lotId),
  })
}
