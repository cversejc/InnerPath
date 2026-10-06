import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildCalendarRequestPayload,
  defaultThirtyDayRange,
  isThirtyDayRange
} from './calendar-request-payload.js'

test('calendar range covers exactly thirty inclusive dates', () => {
  assert.deepEqual(defaultThirtyDayRange(new Date(2026, 9, 3)), {
    start_date: '2026-10-03',
    end_date: '2026-11-01'
  })
  assert.equal(isThirtyDayRange('2026-10-03', '2026-11-01'), true)
  assert.equal(isThirtyDayRange('2026-10-03', '2026-11-02'), false)
})

test('calendar request keeps the profile version and originating report reference', () => {
  const payload = buildCalendarRequestPayload({
    profile_version: 2,
    source_report_id: '41',
    focus_topics: ['career'],
    available_minutes_per_day: 45
  }, 3)

  assert.equal(payload.profile_version, 3)
  assert.equal(payload.source_report_id, 41)
  assert.equal(payload.available_minutes_per_day, 45)
  assert.deepEqual(payload.focus_topics, ['career'])
})

test('calendar request drops invalid report references', () => {
  assert.equal(buildCalendarRequestPayload({ source_report_id: 'invalid' }, 1).source_report_id, null)
  assert.equal(buildCalendarRequestPayload({ source_report_id: '-1' }, 1).source_report_id, null)
})
