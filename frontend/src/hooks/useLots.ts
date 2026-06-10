import { useQuery } from '@tanstack/react-query'
import { getLots } from '@/api/lots'

export function useLots() {
  return useQuery({
    queryKey: ['lots'],
    queryFn: () => getLots({ limit: 100 }),
  })
}
