/* Number / string formatting helpers. */

export function formatInt(n: number | null | undefined): string {
  if (n == null) return '-'
  return new Intl.NumberFormat('zh-CN').format(n)
}

export function formatGrade(n: number | null | undefined, fallback = '-'): string {
  if (n == null) return fallback
  return Number(n).toFixed(2)
}

export function shorten(s: string | null | undefined, max = 80): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

export function pickTierColor(tier: string | null | undefined): string {
  switch (tier) {
    case 'high':   return '#10b981'
    case 'medium': return '#3b82f6'
    case 'low':    return '#f59e0b'
    case 'silent': return '#94a3b8'
    default:       return '#64748b'
  }
}
