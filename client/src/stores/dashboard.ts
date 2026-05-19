import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi } from '@/api/dashboard'
import type {
  CityKPI, GlobalKPI, HeatmapPoint, LevelDist, SpotMetric,
} from '@/api/types'

export const useDashboardStore = defineStore('dashboard', () => {
  const globalKpi = ref<GlobalKPI | null>(null)
  const cityKpi   = ref<CityKPI[]>([])
  const topSpots  = ref<SpotMetric[]>([])
  const heatmap   = ref<HeatmapPoint[]>([])
  const levelDist = ref<LevelDist[]>([])
  const wordcloud = ref<Array<{ name: string; value: number }>>([])
  const loading   = ref(false)
  const error     = ref<string | null>(null)

  async function loadAll() {
    loading.value = true
    error.value = null
    try {
      const [g, c, t, h, l, w] = await Promise.all([
        dashboardApi.globalKpi(),
        dashboardApi.cityKpi(20),
        dashboardApi.topSpots(10, 'comment_count_real'),
        dashboardApi.heatmap(),
        dashboardApi.levelDist(),
        dashboardApi.wordcloud(undefined, 80).catch(() => []),
      ])
      globalKpi.value = g
      cityKpi.value   = c
      topSpots.value  = t
      heatmap.value   = h
      levelDist.value = l
      wordcloud.value = w
    } catch (e: unknown) {
      error.value = (e as Error)?.message || 'load failed'
    } finally {
      loading.value = false
    }
  }

  return { globalKpi, cityKpi, topSpots, heatmap, levelDist, wordcloud, loading, error, loadAll }
})
