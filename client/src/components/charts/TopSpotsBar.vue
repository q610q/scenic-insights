<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import type { SpotMetric } from '@/api/types'

const props = defineProps<{ data: SpotMetric[]; height?: string }>()

const option = computed(() => {
  const sorted = [...props.data].sort((a, b) => a.comment_count_real - b.comment_count_real)
  return {
    backgroundColor: 'transparent',
    grid: { left: 100, right: 30, top: 16, bottom: 24, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: Array<{ dataIndex: number; value: number }>) => {
        const idx = params[0].dataIndex
        const s = sorted[idx]
        return `<b>${s.name}</b><br/>评论 ${s.comment_count_real}<br/>评分 ${s.grade ?? '-'} | 热度 ${s.hot ?? '-'}`
      },
    },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } },
    },
    yAxis: {
      type: 'category',
      data: sorted.map(s => s.name),
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#cbd5e1' },
    },
    series: [
      {
        type: 'bar',
        data: sorted.map(s => s.comment_count_real),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#ec4899' },
            ],
          },
          borderRadius: [0, 6, 6, 0],
        },
        label: {
          show: true,
          position: 'right',
          color: '#94a3b8',
          formatter: '{c}',
        },
      },
    ],
  }
})
</script>

<template>
  <BaseChart :option="option" :height="height || '420px'" />
</template>
