import { api } from './client'

export const searchApi = {
  spots: (q: string, limit = 20) =>
    api.get('/search/spots', { params: { q, limit } }).then(r => r.data),

  nearby: (lon: number, lat: number, km = 50, limit = 50) =>
    api.get('/search/nearby', { params: { lon, lat, km, limit } }).then(r => r.data),
}
