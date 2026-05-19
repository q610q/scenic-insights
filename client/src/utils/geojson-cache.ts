/**
 * China geojson 缓存（perf #3）
 *
 * 问题：原 ChinaMap onMounted 每次都 fetch 800KB geojson，路由切回也重下。
 * 方案：模块级 promise 单例 + sessionStorage 持久化，全应用首次加载后零网络。
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type GeoJSON = any

const CHINA_GEO_URL = 'https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json'
const SS_KEY = 'china-geojson-v1'

let promise: Promise<GeoJSON> | null = null

export function getChinaGeoJSON(): Promise<GeoJSON> {
  if (promise) return promise

  // sessionStorage 命中（同浏览器 session 内秒返）
  try {
    const cached = sessionStorage.getItem(SS_KEY)
    if (cached) {
      promise = Promise.resolve(JSON.parse(cached) as GeoJSON)
      return promise
    }
  } catch {
    // sessionStorage 不可用（隐私模式 / quota），降级到内存
  }

  promise = fetch(CHINA_GEO_URL)
    .then((r) => {
      if (!r.ok) throw new Error(`geojson ${r.status}`)
      return r.json()
    })
    .then((geo: GeoJSON) => {
      try {
        sessionStorage.setItem(SS_KEY, JSON.stringify(geo))
      } catch {
        // quota 超限，无视
      }
      return geo
    })
    .catch((e) => {
      promise = null // 失败重置，允许下次重试
      throw e
    })

  return promise
}
