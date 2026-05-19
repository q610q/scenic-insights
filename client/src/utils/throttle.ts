/**
 * 极简 throttle（perf #5）
 *
 * 用于 ResizeObserver 节流，避免 6 个 ECharts 同时高频 resize。
 * trailing-edge：等空闲后调一次，保证最终尺寸正确。
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function throttle<F extends (...args: any[]) => void>(
  fn: F,
  wait = 100,
): F & { cancel: () => void } {
  let last = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let lastArgs: Parameters<F> | null = null

  const invoke = () => {
    last = Date.now()
    timer = null
    if (lastArgs) fn(...lastArgs)
    lastArgs = null
  }

  const wrapped = ((...args: Parameters<F>) => {
    const now = Date.now()
    const remain = wait - (now - last)
    lastArgs = args
    if (remain <= 0) {
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      invoke()
    } else if (!timer) {
      timer = setTimeout(invoke, remain)
    }
  }) as F & { cancel: () => void }

  wrapped.cancel = () => {
    if (timer) clearTimeout(timer)
    timer = null
    lastArgs = null
  }

  return wrapped
}
