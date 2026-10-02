import assert from 'node:assert/strict'
import test from 'node:test'
import { createEmptyProfile } from '../users/profile.js'
import {
  createEmptyAssessmentContext,
  validateAssessmentContext,
  validateAssessmentProfile
} from './form.js'

function validProfile(overrides = {}) {
  return {
    ...createEmptyProfile(),
    name: '林一',
    gender: 'female',
    birth_year: 1992,
    birth_month: 2,
    birth_day: 29,
    ...overrides
  }
}

test('assessment profile validation accepts complete solar dates', () => {
  assert.deepEqual(validateAssessmentProfile(validProfile(), 2026), {})
})

test('assessment profile validation checks calendar dates and precision', () => {
  assert.equal(validateAssessmentProfile(validProfile({ birth_day: 30 }), 2026).birth_date, '公历出生日期不存在，请检查日期。')
  assert.equal(validateAssessmentProfile(validProfile({ birth_is_leap_month: true }), 2026).birth_date, '公历日期不能选择闰月。')
  assert.equal(validateAssessmentProfile(validProfile({ calendar_type: '' }), 2026).calendar_type, '请选择历法类型。')
  assert.equal(validateAssessmentProfile(validProfile({ birth_time_precision: 'approximate' }), 2026).birth_time, '请选择完整的出生小时和分钟。')
})

test('assessment context validation requires focus, challenge, and expected outcome', () => {
  assert.deepEqual(validateAssessmentContext(createEmptyAssessmentContext()), {
    focus_topics: '至少选择一个关注领域。',
    current_challenge: '请描述当前困惑或挑战。',
    expected_outcomes: '至少选择一个期望获得的结果。'
  })
  assert.deepEqual(validateAssessmentContext({ focus_topics: ['career'], current_challenge: '转行犹豫', expected_outcomes: ['方向指引'] }), {})
})
