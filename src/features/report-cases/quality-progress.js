// Presentation state for a whole-report quality run: which stage the check is
// in, how long it has been there, and whether it looks abandoned so the
// consultant can retry instead of waiting on a silent task.

const ACTIVE_RUN_STATUSES = ['PENDING', 'RUNNING']

export function durationLabel(seconds) {
  const value = Number(seconds)
  if (!Number.isFinite(value)) return ''
  const total = Math.max(0, Math.round(value))
  if (total < 60) return `${total} 秒`
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`
}

export function qualityRunProgress(quality) {
  const run = quality?.latest_validator_run
  if (!run || !ACTIVE_RUN_STATUSES.includes(run.status)) return null
  const elapsedValue = Number(run.elapsed_seconds)
  const elapsed = Number.isFinite(elapsedValue) ? Math.max(0, Math.round(elapsedValue)) : null
  const queueTimeout = Number(run.queue_timeout_seconds)
  const queued = run.status === 'PENDING'
  const stalled = queued && queueTimeout > 0 && elapsed !== null && elapsed >= queueTimeout
  const elapsedLabel = elapsed === null ? '' : `${queued ? '已等待' : '已用时'} ${durationLabel(elapsed)}`
  return {
    status: run.status,
    stalled,
    stage: stalled ? '等待超时' : queued ? '排队中' : '检查中',
    elapsed,
    elapsedLabel,
    hint: stalled
      ? '检查任务长时间没有开始，可能已经中断。可以重新检查完整报告继续。'
      : queued
        ? '检查任务已提交，正在等待执行；开始后会继续显示耗时。'
        : '正在检查完整报告，完成后会自动显示本次结果。'
  }
}
