<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as echarts from 'echarts/core'
import BaseChart from './BaseChart.vue'
import type { HeatmapPoint } from '@/api/types'
import { getChinaGeoJSON } from '@/utils/geojson-cache'

const props = defineProps<{ data: HeatmapPoint[]; height?: string }>()

const mapReady = ref(false)
const loadError = ref<string | null>(null)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const baseChartRef = ref<any>(null)

// feat #13: zoom 通过响应式 ref 驱动 computed.option, 保证 geo region + scatter 同步重渲染
// (dispatchAction 'geoRoam' 只改 _roamTransform, geo region view 不刷新 → 只有 scatter 跟着变)
const INITIAL_ZOOM = 1.2
const ZOOM_MIN = 0.8
const ZOOM_MAX = 6
const userZoom = ref(INITIAL_ZOOM)

onMounted(async () => {
  // perf #3: 全局缓存的 china geojson（首次 fetch 后 sessionStorage 命中秒返）
  try {
    const geo = await getChinaGeoJSON()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    echarts.registerMap('china', geo as any)
    mapReady.value = true
  } catch (e) {
    loadError.value = (e as Error)?.message || 'failed'
    console.error('Failed to load china geojson', e)
  }
})

// perf #1: 拆 effectScatter — Top N 用 effectScatter（涟漪），其余用普通 scatter (large+progressive)
const EFFECT_TOP_N = 50

const option = computed(() => {
  if (!props.data || props.data.length === 0) {
    return { backgroundColor: 'transparent' } as echarts.EChartsCoreOption
  }

  // 按 value[2] (comment_count_real) 降序找 top N 热点
  const sorted = [...props.data].sort((a, b) => (b.value[2] || 0) - (a.value[2] || 0))
  const hot = sorted.slice(0, EFFECT_TOP_N)
  const rest = sorted.slice(EFFECT_TOP_N)
  const maxCount = Math.max(1, sorted[0]?.value[2] || 1)

  const tooltipFormatter = (p: { name: string; value?: number[] }) => {
    if (!p.value || p.value.length < 4) return p.name
    const [, , cnt, grade] = p.value
    return `<b>${p.name}</b><br/>评论 ${cnt}<br/>评分 ${grade ?? '-'}`
  }

  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: tooltipFormatter },
    geo: {
      map: 'china',
      // perf #7: roam:'move' 仅允许拖动，避免 true(=move+scale) 拦截滚轮
      // feat #13: 缩放改由 +/− 按钮驱动 userZoom ref → 重新 setOption (确保 region 同步)
      roam: 'move',
      zoom: userZoom.value,
      scaleLimit: { min: ZOOM_MIN, max: ZOOM_MAX },
      itemStyle: { areaColor: '#1e293b', borderColor: '#475569' },
      emphasis: { itemStyle: { areaColor: '#334155' }, label: { color: '#f1f5f9' } },
    },
    // perf #6: visualMap 绑定到 series.encode.value 第 3 维度（评论数）
    visualMap: {
      show: false,
      min: 0,
      max: maxCount,
      dimension: 2,
      inRange: { color: ['#3b82f6', '#a855f7', '#ec4899'] },
    },
    series: [
      // 冷点：普通 scatter，启用 large + progressive 走批量优化路径
      {
        name: '景区',
        type: 'scatter',
        coordinateSystem: 'geo',
        data: rest,
        symbolSize: (val: number[]) => Math.min(20, 4 + Math.sqrt(val[2] || 1) * 0.4),
        large: true,
        largeThreshold: 200,
        progressive: 500,
        progressiveThreshold: 1000,
        itemStyle: { opacity: 0.7 },
        emphasis: { focus: 'self' },
      },
      // 热点：effectScatter 涟漪动画（仅 Top 50，性能可控）
      {
        name: '热门景区',
        type: 'effectScatter',
        coordinateSystem: 'geo',
        data: hot,
        symbolSize: (val: number[]) => Math.min(40, 8 + Math.sqrt(val[2] || 1) * 0.6),
        rippleEffect: { brushType: 'stroke', scale: 2.5 },
        showEffectOn: 'render',
        // perf #10: 去除 shadowBlur (合成层重建时光晕需重算 → 进入视口卡顿)
        itemStyle: {},
        zlevel: 2,
      },
    ],
  } as echarts.EChartsCoreOption
})

function zoomBy(factor: number) {
  const next = userZoom.value * factor
  userZoom.value = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, next))
}

function resetZoom() {
  userZoom.value = INITIAL_ZOOM
  // 顺手把用户拖动产生的 center 偏移也清掉
  const chart = baseChartRef.value?.getInstance?.()
  if (chart) chart.setOption({ geo: { center: null } })
}
</script>

<template>
  <div :style="{ height: height || '480px', position: 'relative' }">
    <div v-if="!mapReady && !loadError" class="loading">加载中国地图数据中...</div>
    <div v-else-if="loadError" class="loading err">地图加载失败：{{ loadError }}</div>
    <BaseChart v-else ref="baseChartRef" :option="option" :height="height || '480px'" />

    <!-- feat #13: 地图缩放控件 (滚轮已让出给页面滚动) -->
    <div v-if="mapReady && !loadError" class="map-controls" aria-label="地图缩放">
      <button class="ctrl-btn" type="button" title="放大" @click="zoomBy(1.25)">＋</button>
      <button class="ctrl-btn" type="button" title="重置" @click="resetZoom">⊙</button>
      <button class="ctrl-btn" type="button" title="缩小" @click="zoomBy(1 / 1.25)">－</button>
    </div>
  </div>
</template>

<style scoped>
.loading {
  color: var(--dash-text); display: flex; align-items: center; justify-content: center;
  height: 100%; font-size: 14px;
}
.loading.err { color: #ef4444; }

.map-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(15, 23, 42, 0.72);
  padding: 4px;
  border-radius: 6px;
  border: 1px solid rgba(99, 102, 241, 0.25);
  backdrop-filter: blur(4px);
  z-index: 5;
}
.ctrl-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #e2e8f0;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
}
.ctrl-btn:hover { background: rgba(99, 102, 241, 0.35); }
.ctrl-btn:active { background: rgba(99, 102, 241, 0.55); }
</style>
