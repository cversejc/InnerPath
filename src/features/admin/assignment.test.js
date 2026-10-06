import assert from 'node:assert/strict'
import test from 'node:test'
import { consultantCoversDirection, consultantsForDirection, consultantsForSpecialty } from './assignment.js'

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
