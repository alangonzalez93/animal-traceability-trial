import { useQuery } from '@tanstack/react-query'
import { getAnimals } from '@/api/animals'

export function useAnimals(tagNumber: string) {
  return useQuery({
    queryKey: ['animals', tagNumber],
    queryFn: () => getAnimals({ tag_number: tagNumber, limit: 10 }),
    enabled: tagNumber.length >= 2,
  })
}
