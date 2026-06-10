import { useQuery } from '@tanstack/react-query'
import { getAnimalHistory } from '@/api/animals'

export function useAnimalHistory(animalId: string, page: number) {
  return useQuery({
    queryKey: ['animal-history', animalId, page],
    queryFn: () => getAnimalHistory(animalId, page, 20),
    enabled: Boolean(animalId),
  })
}
