import test from 'node:test'
import assert from 'node:assert/strict'
import { ownsRequest, canAcceptRequest, canHandleStep } from './professional-ownership.js'

test('second specialty can accept after the first, both can read but only their nodes can be changed', () => {
  const request = { status: 'accepted', assigned_consultant_id: 10, assigned_mingli_consultant_id: 10, assigned_psychology_consultant_id: null }
  const mingli = { id: 10, role: 'consultant', consultant_type: 'mingli' }
  const psychology = { id: 20, role: 'consultant', consultant_type: 'psychology' }
  assert.equal(canAcceptRequest(request, psychology), true)
  assert.equal(canAcceptRequest(request, mingli), false)
  request.assigned_psychology_consultant_id = 20
  assert.equal(ownsRequest(request, psychology), true)
  assert.equal(canHandleStep({ required_capability: 'mingli', assignee_id: 10 }, psychology), false)
  assert.equal(canHandleStep({ required_capability: 'psychology', assignee_id: 20 }, psychology), true)
  assert.equal(canHandleStep({ required_capability: 'psychology', assignee_id: null }, psychology), false)
  assert.equal(canAcceptRequest({ status: 'submitted' }, { role: 'admin' }), false)
})
