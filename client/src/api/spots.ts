import { api } from './client'
import type { SpotBrief, SpotDetail } from './types'

export interface SpotFilter {
  city?: string
  level?: string
  tier?: 'high' | 'medium' | 'low' | 'silent'
  min_grade?: number
  page?: number
  page_size?: number
}

export interface SpotListPage {
  items: SpotBrief[]
  total: number
}

export const spotsApi = {
  list: (params: SpotFilter = {}): Promise<SpotListPage> =>
    api.get<SpotBrief[]>('/spots', { params }).then((r) => ({
      items: r.data,
      // 后端通过 X-Total-Count 返回筛选条件下的全量行数，缺失时回退到当前页长度
      total: Number(r.headers['x-total-count'] ?? r.data.length) || 0,
    })),

  detail: (id: number) =>
    api.get<SpotDetail>(`/spots/${id}`).then(r => r.data),

  gradeDist: (id: number) =>
    api.get(`/spots/${id}/comment-distribution`).then(r => r.data),

  cities: () =>
    api.get<Array<{ city: string; spot_count: number; total_real_comments: number }>>(
      '/spots/cities/list',
    ).then(r => r.data),
}
