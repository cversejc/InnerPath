import assert from 'node:assert/strict'
import test from 'node:test'
import { createEmptyProfile } from '../user-center/profile.js'
import { createEmptyAssessmentContext } from './form.js'
import {
  ASSESSMENT_DRAFT_STORAGE_KEY,
  restoreAssessmentDraft,
  saveAssessmentDraft
} from './drafts.js'

function createStorage(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    getItem(key) {
      return values.get(key) ?? null
    },
    setItem(key, value) {
      values.set(key, value)
    },
    removeItem(key) {
      values.delete(key)
    },
    has(key) {
      return values.has(key)
    }
  }
}

test('assessment draft persists and restores matching profile and context', () => {
  const storage = createStorage()
  const profile = { ...createEmptyProfile(), name: '林一' }
  const context = { ...createEmptyAssessmentContext(), focus_topics: ['career'] }

  assert.equal(saveAssessmentDraft(storage, { profileVersion: 3, profile, context }), true)
  const restored = restoreAssessmentDraft(storage, {
    profileVersion: 3,
    profileDraft: createEmptyProfile(),
    contextDraft: createEmptyAssessmentContext()
  })

  assert.equal(restored.profileDraft.name, '林一')
  assert.deepEqual(restored.contextDraft.focus_topics, ['career'])
  assert.equal(restored.draftRestored, true)
})

test('assessment draft skips profile data from another profile version but restores context', () => {
  const storage = createStorage()
  saveAssessmentDraft(storage, {
    profileVersion: 2,
    profile: { name: '旧档案' },
    context: { ...createEmptyAssessmentContext(), current_challenge: '转行犹豫' }
  })

  const restored = restoreAssessmentDraft(storage, {
    profileVersion: 3,
    profileDraft: { name: '当前档案' },
    contextDraft: createEmptyAssessmentContext()
  })

  assert.equal(restored.profileDraft.name, '当前档案')
  assert.equal(restored.contextDraft.current_challenge, '转行犹豫')
  assert.equal(restored.draftRestored, true)
})

test('assessment draft removes malformed stored data', () => {
  const storage = createStorage({ [ASSESSMENT_DRAFT_STORAGE_KEY]: '{invalid' })

  const restored = restoreAssessmentDraft(storage, {
    profileVersion: 1,
    profileDraft: createEmptyProfile(),
    contextDraft: createEmptyAssessmentContext()
  })

  assert.equal(restored.draftRestored, false)
  assert.equal(storage.has(ASSESSMENT_DRAFT_STORAGE_KEY), false)
})

test('assessment draft persistence tolerates unavailable storage', () => {
  const storage = { setItem() { throw new Error('storage unavailable') } }
  assert.equal(saveAssessmentDraft(storage, {}), false)
})
