import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SpotFilter } from '@/api/spots'

export const useFiltersStore = defineStore('filters', () => {
  const filter = ref<SpotFilter>({
    city: undefined,
    level: undefined,
    tier: undefined,
    min_grade: undefined,
    page: 1,
    page_size: 30,
  })

  function reset() {
    filter.value = { page: 1, page_size: 30 }
  }
  function update(patch: Partial<SpotFilter>) {
    filter.value = { ...filter.value, ...patch }
  }

  return { filter, reset, update }
})
