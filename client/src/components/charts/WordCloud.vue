<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import 'echarts-wordcloud'
import BaseChart from './BaseChart.vue'

interface Word { name: string; value: number }
const props = defineProps<{ words: Word[]; height?: string }>()

const option = ref<echarts.EChartsCoreOption>({})

function buildOption() {
  option.value = {
    backgroundColor: 'transparent',
    tooltip: { show: true, formatter: '{b}: {c}' },
    series: [
      {
        type: 'wordCloud',
        gridSize: 8,
        sizeRange: [12, 60],
        rotationRange: [-30, 30],
        rotationStep: 15,
        shape: 'circle',
        textStyle: {
          color: () =>
            'rgb(' +
            [Math.random() * 160 + 60, Math.random() * 160 + 60, 255 - Math.random() * 60]
              .map(Math.floor).join(',') +
            ')',
        },
        emphasis: { focus: 'self', textStyle: { textShadowBlur: 10, textShadowColor: '#818cf8' } },
        data: props.words.slice(0, 80),
      },
    ],
  }
}

onMounted(buildOption)
watch(() => props.words, buildOption, { deep: true })
</script>

<template>
  <BaseChart :option="option" :height="height || '320px'" />
</template>
