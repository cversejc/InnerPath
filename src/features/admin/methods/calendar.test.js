import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import calendarMethods from './calendar.js'

function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

test('calendar publication stops when the confirmation is cancelled', async () => {
  const confirmationOptions = []
  const context = {
    async confirmAction(options) {
      confirmationOptions.push(options)
      return false
    }
  }

  await calendarMethods.publishCalendar.call(context, {
    id: 12,
    title: '秋季行动日历',
    version_number: 3
  })

  assert.deepEqual(confirmationOptions, [{
    title: '确认发布日历',
    message: '确认发布“秋季行动日历” v3？发布后用户端将看到这版内容。',
    confirmButtonText: '确认发布'
  }])
})

test('calendar archival stops when the confirmation is cancelled', async () => {
  const confirmationOptions = []
  const context = {
    async confirmAction(options) {
      confirmationOptions.push(options)
      return false
    }
  }

  await calendarMethods.archiveCalendar.call(context, {
    id: 12,
    title: '秋季行动日历',
    version_number: 3
  })

  assert.deepEqual(confirmationOptions, [{
    title: '确认归档日历',
    message: '确认归档“秋季行动日历” v3？',
    confirmButtonText: '确认归档'
  }])
})

test('late calendar list responses cannot replace the newly selected user', async () => {
  const originalGet = apiClient.get
  const firstCalendars = deferred()
  apiClient.get = async url => {
    if (url === '/admin/users/1/calendars') return firstCalendars.promise
    if (url === '/admin/users/2/calendars') return { data: { items: [{ id: 22, user_id: 2 }] } }
    throw new Error(`unexpected request: ${url}`)
  }
  const context = {
    calendarLoading: false,
    calendars: [],
    calendarsRequestId: 0,
    errorText: error => error.message,
    message: '',
    selectedCalendarUser: { id: 1 }
  }

  try {
    const firstLoad = calendarMethods.loadCalendars.call(context)
    context.selectedCalendarUser = { id: 2 }
    await calendarMethods.loadCalendars.call(context)
    firstCalendars.resolve({ data: { items: [{ id: 11, user_id: 1 }] } })
    await firstLoad
  } finally {
    apiClient.get = originalGet
  }

  assert.deepEqual(context.calendars, [{ id: 22, user_id: 2 }])
  assert.equal(context.calendarLoading, false)
  assert.equal(context.message, '')
})
