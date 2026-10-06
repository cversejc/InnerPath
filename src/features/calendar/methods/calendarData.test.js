import assert from 'node:assert/strict'
import test from 'node:test'

globalThis.sessionStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {}
}

const { default: calendarDataMethods } = await import('./calendarData.js')

function emptyCalendarContext() {
  return {
    loading: true,
    calendar: { id: 'old-calendar' },
    calendarSource: 'api',
    calendarError: '上一次读取失败',
    days: [{ date: '2026-10-05' }],
    meta: { title: '旧日历' }
  }
}

test('successful empty calendar response clears stale errors and old calendar data', async () => {
  const context = emptyCalendarContext()

  await calendarDataMethods.loadCalendar.call(context, async () => ({ items: [] }))

  assert.equal(context.calendar, null)
  assert.equal(context.calendarSource, 'empty')
  assert.deepEqual(context.days, [])
  assert.deepEqual(context.meta, {})
  assert.equal(context.calendarError, '')
  assert.equal(context.loading, false)
})

test('failed calendar read exposes a retryable error and clears stale content', async () => {
  const context = emptyCalendarContext()

  await calendarDataMethods.loadCalendar.call(context, async () => {
    throw new Error('network unavailable')
  })

  assert.equal(context.calendar, null)
  assert.deepEqual(context.days, [])
  assert.equal(context.calendarError, '暂时无法读取已交付日历，请重新加载或稍后再试。')
  assert.equal(context.loading, false)
})

test('retryCalendarLoad returns to loading state and clears the error after recovery', async () => {
  const context = emptyCalendarContext()
  context.loading = false
  context.loadCalendar = () => calendarDataMethods.loadCalendar.call(context, async () => ({ items: [] }))

  await calendarDataMethods.retryCalendarLoad.call(context)

  assert.equal(context.loading, false)
  assert.equal(context.calendarError, '')
  assert.equal(context.calendarSource, 'empty')
})
