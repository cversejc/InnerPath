import assert from 'node:assert/strict'
import test from 'node:test'
import activityMethods from './activity.js'

test('consultant activity link opens all audit events for that actor', async () => {
  let loads = 0
  const context = {
    activeTab: 'staff',
    logFilters: { actor_user_id: '', action: 'old', resource_type: 'user' },
    logPage: 4,
    logSection: 'behavior',
    loadAuditLogs: async () => { loads += 1 }
  }

  await activityMethods.openConsultantActivity.call(context, 23)

  assert.equal(context.activeTab, 'logs')
  assert.equal(context.logSection, 'audit')
  assert.equal(context.logPage, 1)
  assert.deepEqual(context.logFilters, {
    search: '',
    action: '',
    resource_type: '',
    actor_user_id: '23',
    target_user_id: '',
    date_from: '',
    date_to: ''
  })
  assert.equal(loads, 1)
})
