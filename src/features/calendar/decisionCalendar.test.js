import assert from 'node:assert/strict'
import test from 'node:test'
import {
  calendarMeta,
  createCalendarDays as createCalendarDaysFromEntry,
  isToday
} from '../../data/decisionCalendar.js'
import {
  createCalendarDays,
  getDateEntry,
  resolveDefaultDate
} from './decisionCalendar.js'

test('calendar content and date logic are available from the existing entry point', () => {
  assert.equal(calendarMeta.startDate, '2026-09-07')
  assert.equal(createCalendarDaysFromEntry().length, createCalendarDays().length)
  assert.equal(typeof isToday, 'function')
})

test('daily entries include their phase metadata', () => {
  const entry = getDateEntry('2026-09-07')

  assert.equal(entry.phaseId, 'observe')
  assert.equal(entry.phaseLabel, '想法记录期')
  assert.equal(entry.isPhase, false)
  assert.equal(entry.dayPillar, '甲申')
})

test('dates without daily details inherit their phase, and out-of-range dates are empty', () => {
  const entry = getDateEntry('2026-09-20')

  assert.equal(entry.phaseId, 'rest')
  assert.equal(entry.keyword, '积累')
  assert.equal(entry.isPhase, true)
  assert.equal(getDateEntry('2026-10-08'), null)
})

test('calendar generation preserves the configured inclusive date range', () => {
  const days = createCalendarDays()

  assert.equal(days.length, 31)
  assert.equal(days[0].date, calendarMeta.startDate)
  assert.equal(days[0].weekday, '一')
  assert.equal(days.at(-1).date, calendarMeta.endDate)
  assert.equal(days.at(-1).weekday, '三')
})

test('default date is clamped to the calendar range', () => {
  assert.equal(resolveDefaultDate(new Date(2026, 8, 1)), calendarMeta.startDate)
  assert.equal(resolveDefaultDate(new Date(2026, 8, 15)), '2026-09-15')
  assert.equal(resolveDefaultDate(new Date(2026, 9, 18)), calendarMeta.endDate)
})
