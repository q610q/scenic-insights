<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'

interface Props {
  spotMetric: {
    grade_5_count?: number
    grade_4_count?: number
    grade_3_count?: number
    grade_2_count?: number
    grade_1_count?: number
  } | null
  height?: string
}
const props = defineProps<Props>()

const option = computed(() => {
  const m = props.spotMetric || {}
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { bottom: 8, textStyle: { color: '#cbd5e1' } },
    series: [
      {
        type: 'pie', radius: ['35%', '70%'],
        label: { color: '#cbd5e1', formatter: '{b}\n{c}' },
        data: [
          { name: '5 力荐', value: m.grade_5_count || 0, itemStyle: { color: '#ef4444' } },
          { name: '4 推荐', value: m.grade_4_count || 0, itemStyle: { color: '#f97316' } },
          { name: '3 还行', value: m.grade_3_count || 0, itemStyle: { color: '#eab308' } },
          { name: '2 一般', value: m.grade_2_count || 0, itemStyle: { color: '#06b6d4' } },
          { name: '1 不行', value: m.grade_1_count || 0, itemStyle: { color: '#64748b' } },
        ].filter(d => d.value > 0),
      },
    ],
  }
})
</script>

<template>
  <BaseChart :option="option" :height="height || '300px'" />
</template>
