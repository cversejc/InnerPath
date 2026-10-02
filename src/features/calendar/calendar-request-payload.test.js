import test from 'node:test'
import assert from 'node:assert/strict'
import { buildCalendarRequestPayload } from './calendar-request-payload.js'

test('calendar request keeps the profile version and originating report reference', () => {
  const payload = buildCalendarRequestPayload({
    profile_version: 2,
    source_report_id: '41',
    focus_topics: ['career']
  }, 3)

  assert.equal(payload.profile_version, 3)
  assert.equal(payload.source_report_id, 41)
  assert.deepEqual(payload.focus_topics, ['career'])
})

test('calendar request drops invalid report references', () => {
  assert.equal(buildCalendarRequestPayload({ source_report_id: 'invalid' }, 1).source_report_id, null)
  assert.equal(buildCalendarRequestPayload({ source_report_id: '-1' }, 1).source_report_id, null)
})
