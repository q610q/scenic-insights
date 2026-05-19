<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import type { SpotMetric } from '@/api/types'

const props = defineProps<{ data: SpotMetric[]; height?: string }>()

const option = computed(() => ({
  backgroundColor: 'transparent',
  grid: { left: 50, right: 20, top: 16, bottom: 40 },
  tooltip: {
    trigger: 'item',
    formatter: (p: { data: number[]; name: string }) =>
      `<b>${p.name}</b><br/>评分 ${p.data[0]}<br/>热度 ${p.data[1]}<br/>评论 ${p.data[2]}`,
  },
  xAxis: {
    type: 'value', name: '评分', min: 0, max: 5,
    axisLine: { lineStyle: { color: '#475569' } },
    axisLabel: { color: '#94a3b8' },
    splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } },
  },
  yAxis: {
    type: 'value', name: '热度', min: 0, max: 10,
    axisLine: { lineStyle: { color: '#475569' } },
    axisLabel: { color: '#94a3b8' },
    splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } },
  },
  series: [
    {
      type: 'scatter',
      data: props.data
        .filter(s => s.grade != null && s.hot != null)
        .map(s => ({
          name: s.name,
          value: [Number(s.grade), Number(s.hot), s.comment_count_real],
        })),
      symbolSize: (v: number[]) => Math.min(60, 6 + Math.sqrt(v[2] || 1)),
      itemStyle: {
        color: '#a855f7',
        opacity: 0.7,
        shadowBlur: 6,
        shadowColor: '#c084fc',
      },
    },
  ],
}))
</script>

<template>
  <BaseChart :option="option" :height="height || '320px'" />
</template>
