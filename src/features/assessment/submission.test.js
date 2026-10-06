import assert from 'node:assert/strict'
import test from 'node:test'
import { createEmptyProfile } from '../users/profile.js'
import { createEmptyAssessmentContext } from './form.js'
import { buildReportApplication, createIdempotencyKey } from './submission.js'

test('report application contains the confirmed profile version and full context snapshot', () => {
  const profile = {
    ...createEmptyProfile(),
    name: ' 林一 ',
    gender: 'female',
    birth_year: 1992,
    birth_month: 2,
    birth_day: 29,
    birth_hour: 12,
    birth_minute: 30,
    birth_time_precision: 'approximate'
  }
  const context = {
    ...createEmptyAssessmentContext(),
    focus_topics: ['career'],
    current_challenge: '考虑转行',
    expected_outcomes: ['方向指引'],
    decision_description: '已开始收集信息'
  }

  const payload = buildReportApplication(profile, context, 9)

  assert.equal(payload.service_type, 'report')
  assert.equal(payload.profile.name, '林一')
  assert.equal(payload.profile.time_accuracy, 'approximate')
  assert.equal(payload.profile_version, 9)
  assert.deepEqual(payload.context, context)
  assert.deepEqual(payload.selected_topics, ['career'])
  assert.match(payload.additional_info, /考虑转行/)
})

test('each new idempotency key can be sent back unchanged after a retry', () => {
  const key = createIdempotencyKey()
  assert.equal(typeof key, 'string')
  assert.ok(key.length >= 8)
  assert.equal(key, key)
})
