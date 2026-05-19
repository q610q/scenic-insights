<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import type { LevelDist } from '@/api/types'

const props = defineProps<{ data: LevelDist[]; height?: string }>()

const LEVEL_COLORS: Record<string, string> = {
  '5A': '#ef4444',
  '4A': '#f97316',
  '3A': '#eab308',
  '2A': '#22c55e',
  '1A': '#06b6d4',
  '未评级': '#64748b',
}

const option = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 景区 ({d}%)' },
  legend: { bottom: 8, textStyle: { color: '#cbd5e1' } },
  series: [
    {
      name: '景区等级',
      type: 'pie',
      radius: ['38%', '70%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#0a0e1a', borderWidth: 2 },
      label: { color: '#cbd5e1', formatter: '{b}\n{d}%' },
      data: props.data.map(d => ({
        name: d.level,
        value: d.spot_count,
        itemStyle: { color: LEVEL_COLORS[d.level] || '#6366f1' },
      })),
    },
  ],
}))
</script>

<template>
  <BaseChart :option="option" :height="height || '320px'" />
</template>
