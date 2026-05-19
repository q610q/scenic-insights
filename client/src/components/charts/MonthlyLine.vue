<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import type { MonthlyTrend } from '@/api/types'

const props = defineProps<{ data: MonthlyTrend[]; height?: string }>()

const option = computed(() => ({
  backgroundColor: 'transparent',
  grid: { left: 36, right: 20, top: 30, bottom: 30, containLabel: true },
  tooltip: { trigger: 'axis' },
  legend: { right: 16, top: 0, textStyle: { color: '#cbd5e1' } },
  xAxis: {
    type: 'category',
    data: props.data.map(d => d.ym),
    axisLine: { lineStyle: { color: '#475569' } },
    axisLabel: { color: '#94a3b8', rotate: 35 },
  },
  yAxis: [
    {
      type: 'value', name: '评论数',
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } },
    },
    {
      type: 'value', name: '平均分', min: 0, max: 5,
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { show: false },
    },
  ],
  series: [
    {
      name: '评论数', type: 'bar', barWidth: '50%',
      data: props.data.map(d => d.cnt),
      itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
    },
    {
      name: '平均分', type: 'line', yAxisIndex: 1, smooth: true,
      data: props.data.map(d => d.avg_grade),
      lineStyle: { color: '#ec4899', width: 2 },
      itemStyle: { color: '#ec4899' },
    },
  ],
}))
</script>

<template>
  <BaseChart :option="option" :height="height || '320px'" />
</template>
