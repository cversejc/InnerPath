import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildProfilePayload,
  createEmptyProfile,
  mapUserToProfile,
  validateProfile
} from './profile.js'

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

test('profile mapping applies defaults and copies list fields', () => {
  const source = { name: '林一', personality_keywords: ['专注'] }
  const profile = mapUserToProfile(source)

  assert.equal(profile.calendar_type, 'solar')
  assert.equal(profile.birth_time_precision, 'unknown')
  assert.deepEqual(profile.personality_keywords, ['专注'])
  assert.notEqual(profile.personality_keywords, source.personality_keywords)
  assert.deepEqual(profile.mingli_experience, [])
})

test('profile validation checks solar dates and required birth time precision', () => {
  assert.deepEqual(validateProfile(validProfile(), 2026), {})
  assert.equal(validateProfile(validProfile({ birth_day: 30 }), 2026).birth_date, '公历出生日期不存在，请检查日期。')
  assert.equal(
    validateProfile(validProfile({ birth_time_precision: 'approximate' }), 2026).birth_time,
    '请选择完整的出生小时和分钟。'
  )
})

test('profile payload excludes contact and normalizes values for the API', () => {
  const payload = buildProfilePayload(validProfile({
    name: ' 林一 ',
    contact: '13800000000',
    mbti: 'infj',
    birth_year: '1992',
    birth_hour: 8,
    birth_minute: 30,
    birth_place: ' 杭州 ',
    strengths: ' '
  }))

  assert.equal('contact' in payload, false)
  assert.equal(payload.name, '林一')
  assert.equal(payload.mbti, 'INFJ')
  assert.equal(payload.birth_year, 1992)
  assert.equal(payload.birth_hour, null)
  assert.equal(payload.birth_minute, null)
  assert.equal(payload.birth_place, '杭州')
  assert.equal(payload.strengths, null)
  assert.deepEqual(payload.default_usage_scenarios, [])
})
