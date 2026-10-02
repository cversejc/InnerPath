import assert from 'node:assert/strict'
import test from 'node:test'
import calendarMethods from './calendar.js'

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
