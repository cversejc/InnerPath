import assert from 'node:assert/strict'
import test from 'node:test'
import {
  addCalendarDays,
  buildCalendarRequestPayload,
  createCalendarRequestForm,
  localDateKey,
  validateCalendarRequestForm
} from './calendar-form.js'

function validForm(overrides = {}) {
  return {
    ...createCalendarRequestForm(),
    name: '林一',
    gender: 'female',
    birth_year: 2000,
    birth_month: 2,
    birth_day: 29,
    birth_is_leap_month: false,
    start_date: '2026-12-31',
    calendar_goal: '安排职业转型',
    ...overrides
  }
}

test('calendar form date helpers use local dates and cross month boundaries', () => {
  assert.equal(localDateKey(new Date(2026, 11, 31)), '2026-12-31')
  assert.equal(addCalendarDays('2026-12-31', 29), '2027-01-29')
})

test('calendar form validation accepts complete dates and rejects invalid calendar dates', () => {
  assert.deepEqual(validateCalendarRequestForm(validForm()), {})
  assert.equal(validateCalendarRequestForm(validForm({ birth_day: 30 })).birth, '出生日期不存在')
  assert.equal(
    validateCalendarRequestForm(validForm({ calendar_type: 'lunar', birth_day: 31 })).birth,
    '农历日期不能超过 30 日'
  )
})

test('calendar form validation reports missing required fields', () => {
  assert.deepEqual(validateCalendarRequestForm(createCalendarRequestForm()), {
    name: '请填写姓名',
    gender: '请选择性别',
    birth: '请填写完整出生日期',
    calendar_goal: '请填写本次关注目标'
  })
})

test('calendar form payload normalizes numeric profile values and unknown birth time', () => {
  const payload = buildCalendarRequestPayload(validForm({
    birth_year: '2000',
    birth_month: '2',
    birth_day: '29',
    birth_place: '',
    additional_info: ''
  }))

  assert.deepEqual(payload.profile, {
    name: '林一',
    gender: 'female',
    birth_year: 2000,
    birth_month: 2,
    birth_day: 29,
    birth_is_leap_month: false,
    birth_hour: null,
    birth_minute: null,
    birth_place: null,
    calendar_type: 'solar',
    time_accuracy: 'unknown'
  })
  assert.equal(payload.calendar_goal, '安排职业转型')
  assert.equal(payload.additional_info, null)
  assert.deepEqual(payload.selected_topics, [])
})

test('calendar form payload retains a selected lunar leap month', () => {
  const payload = buildCalendarRequestPayload(validForm({
    calendar_type: 'lunar',
    birth_year: 2023,
    birth_month: 2,
    birth_day: 1,
    birth_is_leap_month: true
  }))

  assert.equal(payload.profile.calendar_type, 'lunar')
  assert.equal(payload.profile.birth_is_leap_month, true)
})
