<script setup lang="ts">
import { formatInt } from '@/utils/format'

defineProps<{
  label: string
  value: number | string | null
  unit?: string
  delta?: string
  icon?: string
  accent?: string
}>()
</script>

<template>
  <div class="kpi-card" :style="{ borderTopColor: accent || '#6366f1' }">
    <div class="kpi-icon" v-if="icon">{{ icon }}</div>
    <div class="kpi-body">
      <div class="kpi-label">{{ label }}</div>
      <div class="kpi-value">
        {{ typeof value === 'number' ? formatInt(value) : (value ?? '-') }}
        <span class="kpi-unit" v-if="unit">{{ unit }}</span>
      </div>
      <div class="kpi-delta" v-if="delta">{{ delta }}</div>
    </div>
  </div>
</template>

<style scoped>
.kpi-card {
  background: var(--dash-card-bg);
  border: 1px solid var(--dash-border);
  border-top: 3px solid #6366f1;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  gap: 16px;
  align-items: center;
  min-height: 100px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.18);
}
.kpi-icon { font-size: 32px; opacity: 0.7; }
.kpi-label { font-size: 13px; color: var(--dash-text); margin-bottom: 6px; }
.kpi-value {
  font-size: 28px; font-weight: 700; color: var(--dash-text-strong);
  letter-spacing: -0.02em; line-height: 1.1;
}
.kpi-unit { font-size: 14px; font-weight: 500; margin-left: 4px; color: var(--dash-text); }
.kpi-delta { font-size: 12px; margin-top: 4px; color: #94a3b8; }
</style>
