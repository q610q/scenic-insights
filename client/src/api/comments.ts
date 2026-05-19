import { api } from './client'
import type { CommentItem, CursorPage } from './types'

export const commentsApi = {
  list: (spotId: number, cursor: number | null = null, limit = 20, minGrade?: number) =>
    api.get<CursorPage<CommentItem>>('/comments', {
      params: {
        spot_id: spotId,
        cursor: cursor ?? undefined,
        limit,
        min_grade: minGrade,
      },
    }).then(r => r.data),
}
