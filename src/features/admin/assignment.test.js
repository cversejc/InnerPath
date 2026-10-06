import assert from 'node:assert/strict'
import test from 'node:test'
import { consultantCoversDirection, consultantOptionLabel, consultantsForDirection, consultantsForSpecialty } from './assignment.js'

const consultants = [
  { id: 1, is_active: true, consultant_specialties: ['metaphysics'] },
  { id: 2, is_active: true, consultant_specialties: ['psychology'] },
  { id: 3, is_active: true, consultant_specialties: ['metaphysics', 'psychology'] },
  { id: 4, is_active: false, consultant_specialties: ['psychology'] }
]

test('direction options contain only active consultants with the required capabilities', () => {
  assert.deepEqual(consultantsForDirection(consultants, 'metaphysics').map(item => item.id), [1, 3])
  assert.deepEqual(consultantsForDirection(consultants, 'psychology').map(item => item.id), [2, 3])
  assert.deepEqual(consultantsForDirection(consultants, 'integrated').map(item => item.id), [3])
  assert.deepEqual(consultantsForSpecialty(consultants, 'mingli').map(item => item.id), [1, 3])
})

test('integrated assignment requires both specialties', () => {
  assert.equal(consultantCoversDirection(consultants[0], 'integrated'), false)
  assert.equal(consultantCoversDirection(consultants[2], 'integrated'), true)
  assert.equal(consultantCoversDirection(consultants[2], 'unknown'), false)
})

test('eligible consultants are ranked by specialty load and stale work', () => {
  const workloads = [
    { consultant_id: 1, active_requests: 0, stale_active_requests: 0, specialty_load: [{ specialty: 'mingli', active_requests: 2, stale_active_requests: 0 }] },
    { consultant_id: 2, active_requests: 0, stale_active_requests: 0, specialty_load: [{ specialty: 'psychology', active_requests: 0, stale_active_requests: 0 }] },
    { consultant_id: 3, active_requests: 3, stale_active_requests: 1, specialty_load: [{ specialty: 'mingli', active_requests: 1, stale_active_requests: 1 }, { specialty: 'psychology', active_requests: 3, stale_active_requests: 1 }] }
  ]

  assert.deepEqual(consultantsForDirection(consultants, 'metaphysics', workloads).map(item => item.id), [3, 1])
  assert.deepEqual(consultantsForSpecialty(consultants, 'psychology', workloads).map(item => item.id), [2, 3])
  assert.equal(consultantOptionLabel(consultants[2], workloads, 'mingli', true), '咨询师 · #3 · 在办 1 · 超 24 小时未更新 1 · 建议优先')
})

test('unknown workload stays available but follows candidates with known workload', () => {
  const workloads = [{ consultant_id: 2, specialty_load: [{ specialty: 'psychology', active_requests: 0, stale_active_requests: 0 }] }]

  assert.deepEqual(consultantsForSpecialty(consultants, 'psychology', workloads).map(item => item.id), [2, 3])
  assert.equal(consultantOptionLabel(consultants[2], workloads, 'psychology'), '咨询师 · #3 · 工作量未加载')
})
