<script setup lang="ts">
import { markRaw, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, ScatterChart, MapChart, EffectScatterChart } from 'echarts/charts'
import {
  GridComponent, LegendComponent, TitleComponent, TooltipComponent,
  VisualMapComponent, GeoComponent, DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { throttle } from '@/utils/throttle'

echarts.use([
  BarChart, LineChart, PieChart, ScatterChart, MapChart, EffectScatterChart,
  GridComponent, LegendComponent, TitleComponent, TooltipComponent,
  VisualMapComponent, GeoComponent, DataZoomComponent,
  CanvasRenderer,
])

// perf #4: 注册极简 dark 主题（避免 'dark' 字符串找不到主题 → fallback warning + 色板抖动）
const DARK_THEME_NAME = 'dash-dark'
let darkRegistered = false
function ensureDarkTheme() {
  if (darkRegistered) return
  echarts.registerTheme(DARK_THEME_NAME, {
    backgroundColor: 'transparent',
    textStyle: { color: '#cbd5e1' },
    title: { textStyle: { color: '#f1f5f9' }, subtextStyle: { color: '#94a3b8' } },
    legend: { textStyle: { color: '#cbd5e1' } },
    tooltip: {
      backgroundColor: 'rgba(15,23,42,0.92)',
      borderColor: '#334155',
      textStyle: { color: '#e2e8f0' },
    },
    categoryAxis: {
      axisLine:  { lineStyle: { color: '#475569' } },
      axisTick:  { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#cbd5e1' },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    valueAxis: {
      axisLine:  { lineStyle: { color: '#475569' } },
      axisTick:  { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#cbd5e1' },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    color: ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#a855f7'],
  })
  darkRegistered = true
}

const props = defineProps<{
  option: echarts.EChartsCoreOption
  width?: string
  height?: string
  /** 透传给 setOption；perf #2: 默认 false 走增量更新 */
  notMerge?: boolean
}>()

const el = ref<HTMLDivElement>()
// perf #2: shallowRef 持有非响应式 chart 实例，避免被 Vue 深度代理
const chartRef = shallowRef<echarts.ECharts | null>(null)
let observer: ResizeObserver | null = null

function init() {
  if (!el.value) return
  ensureDarkTheme()
  const chart = echarts.init(el.value, DARK_THEME_NAME)
  // perf #2: markRaw 防止 ECharts 内部状态被 Vue reactive 包裹
  chart.setOption(markRaw(props.option) as echarts.EChartsCoreOption, props.notMerge ?? false)
  chartRef.value = chart

  // perf #5: ResizeObserver 节流（避免 6 chart 同时高频 resize）
  const onResize = throttle(() => chart.resize(), 120)
  observer = new ResizeObserver(onResize)
  observer.observe(el.value)
}

onMounted(init)

onUnmounted(() => {
  observer?.disconnect()
  chartRef.value?.dispose()
  chartRef.value = null
})

// perf #2: 浅监听 option 引用变化（子组件应返回新对象引用而非 mutate）
// 避免 deep: true 对大数据集（如 heatmap 2043 点）的递归比较开销
watch(
  () => props.option,
  (v) => chartRef.value?.setOption(markRaw(v) as echarts.EChartsCoreOption, props.notMerge ?? false),
)

defineExpose({ getInstance: () => chartRef.value })
</script>

<template>
  <div ref="el" :style="{ width: width || '100%', height: height || '320px' }" />
</template>
