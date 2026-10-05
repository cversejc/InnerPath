import assert from 'node:assert/strict'
import test from 'node:test'
import { resolveCalendarPracticeRefs } from './practice-actions.js'

test('daily calendar links retain their frozen report action and cadence', () => {
  const rhythm = { actions: [
    { action_id: 'action.boundary', claim: '练习表达边界', frequency: 'weekly', duration_minutes: 15 },
    { action_id: 'action.rest', claim: '预留恢复时间', frequency: 'daily', duration_minutes: 10 }
  ] }

  assert.deepEqual(resolveCalendarPracticeRefs(['action.boundary', 'unknown'], rhythm), [
    { action_id: 'action.boundary', claim: '练习表达边界', frequency: 'weekly', duration_minutes: 15, frequency_label: '每周' }
  ])
  assert.deepEqual(resolveCalendarPracticeRefs(null, rhythm), [])
})
