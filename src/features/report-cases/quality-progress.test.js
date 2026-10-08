import test from 'node:test'
import assert from 'node:assert/strict'
import { durationLabel, qualityRunProgress } from './quality-progress.js'

function qualityWith(run) {
  return { latest_validator_run: run }
}

test('durationLabel renders seconds and minutes', () => {
  assert.equal(durationLabel(0), '0 秒')
  assert.equal(durationLabel(59), '59 秒')
  assert.equal(durationLabel(60), '1 分')
  assert.equal(durationLabel(125), '2 分 5 秒')
  assert.equal(durationLabel(null), '0 秒')
  assert.equal(durationLabel(undefined), '')
})

test('qualityRunProgress stays quiet without an active run', () => {
  assert.equal(qualityRunProgress(null), null)
  assert.equal(qualityRunProgress(qualityWith(null)), null)
  assert.equal(qualityRunProgress(qualityWith({ status: 'COMPLETED', elapsed_seconds: 30 })), null)
  assert.equal(qualityRunProgress(qualityWith({ status: 'FAILED', elapsed_seconds: 30 })), null)
})

test('qualityRunProgress reports queueing with waiting time', () => {
  const progress = qualityRunProgress(
    qualityWith({ status: 'PENDING', elapsed_seconds: 12, queue_timeout_seconds: 300 })
  )
  assert.equal(progress.stalled, false)
  assert.equal(progress.stage, '排队中')
  assert.equal(progress.elapsedLabel, '已等待 12 秒')
  assert.match(progress.hint, /等待执行/)
})

test('qualityRunProgress reports running with elapsed time', () => {
  const progress = qualityRunProgress(
    qualityWith({ status: 'RUNNING', elapsed_seconds: 95, queue_timeout_seconds: 300 })
  )
  assert.equal(progress.stalled, false)
  assert.equal(progress.stage, '检查中')
  assert.equal(progress.elapsedLabel, '已用时 1 分 35 秒')
  assert.match(progress.hint, /正在检查完整报告/)
})

test('qualityRunProgress flags a queue that never started', () => {
  const progress = qualityRunProgress(
    qualityWith({ status: 'PENDING', elapsed_seconds: 320, queue_timeout_seconds: 300 })
  )
  assert.equal(progress.stalled, true)
  assert.equal(progress.stage, '等待超时')
  assert.match(progress.hint, /重新检查/)
})

test('qualityRunProgress tolerates a run without timing fields', () => {
  const progress = qualityRunProgress(qualityWith({ status: 'RUNNING' }))
  assert.equal(progress.stalled, false)
  assert.equal(progress.elapsedLabel, '')
})
