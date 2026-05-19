import { api } from './client'
import type {
  CityKPI, GlobalKPI, HeatmapPoint, LevelDist, MonthlyTrend, SpotMetric,
} from './types'

export const dashboardApi = {
  globalKpi: () => api.get<GlobalKPI>('/dashboard/global-kpi').then(r => r.data),

  cityKpi:   (limit = 20) =>
    api.get<CityKPI[]>('/dashboard/city-kpi', { params: { limit } }).then(r => r.data),

  topSpots: (limit = 10, sort: 'comment_count_real' | 'grade' | 'hot' | 'avg_co_grade' = 'comment_count_real') =>
    api.get<SpotMetric[]>('/dashboard/spots/top', { params: { limit, sort } }).then(r => r.data),

  heatmap: () =>
    api.get<HeatmapPoint[]>('/dashboard/heatmap').then(r => r.data),

  levelDist: () =>
    api.get<LevelDist[]>('/dashboard/level-dist').then(r => r.data),

  monthlyTrend: (spotId: number) =>
    api.get<MonthlyTrend[]>(`/dashboard/spots/${spotId}/monthly`).then(r => r.data),

  wordcloud: (spotId?: number, limit = 80) =>
    api.get<Array<{ name: string; value: number }>>('/dashboard/wordcloud', {
      params: { spot_id: spotId, limit },
    }).then(r => r.data),
}
