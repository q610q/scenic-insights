/* Shared types matching FastAPI Pydantic schemas. */

export interface GlobalKPI {
  spot_total: number
  real_comment_total: number
  avg_grade: number | null
  city_count: number
}

export interface CityKPI {
  city: string
  province: string | null
  spot_count: number
  avg_grade: number | null
  total_real_comments: number
  hot_spot_count: number
}

export interface SpotMetric {
  id: number
  name: string
  city: string | null
  level: string | null
  tag: string | null
  grade: number | null
  hot: number | null
  comment_count_real: number
  avg_co_grade: number | null
  grade_5_count: number
  grade_4_count: number
  grade_3_count: number
  grade_2_count: number
  grade_1_count: number
  lon: number | null
  lat: number | null
}

export interface SpotBrief {
  id: number
  name: string
  level: string | null
  city: string | null
  grade: number | null
  hot: number | null
  comment_count_real: number
  comment_tier: string | null
  lon: number | null
  lat: number | null
}

export interface SpotDetail extends SpotBrief {
  tag: string | null
  location: string | null
  province: string | null
  district: string | null
  phone: string | null
  open_time_raw: string | null
  intro: string | null
  notice: string | null
  tips: string | null
  total_comments_raw: number | null
  comment_count_all: number
  comment_count_default: number
  has_real_comments: boolean
}

export interface HeatmapPoint {
  name: string
  value: number[]   // [lon, lat, count, grade]
}

export interface LevelDist {
  level: string
  spot_count: number
  total_comments: number
  avg_grade: number | null
}

export interface MonthlyTrend {
  ym: string
  cnt: number
  avg_grade: number | null
}

export interface CommentItem {
  id: number
  spot_id: number
  co_name: string | null
  co_grade: number | null
  content: string
  ip_region: string | null
  co_time: string
  src_schema: string | null
}

export interface CursorPage<T> {
  items: T[]
  next_cursor: number | null
  has_more: boolean
}
