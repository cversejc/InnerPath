import { createEmptyAssessmentContext } from './form.js'

export const ASSESSMENT_DRAFT_STORAGE_KEY = 'assessment-intake-draft'

export function saveAssessmentDraft(storage, draft) {
  try {
    storage.setItem(ASSESSMENT_DRAFT_STORAGE_KEY, JSON.stringify(draft))
    return true
  } catch {
    return false
  }
}

export function restoreAssessmentDraft(storage, currentDraft) {
  try {
    const stored = JSON.parse(storage.getItem(ASSESSMENT_DRAFT_STORAGE_KEY) || 'null')
    if (!stored || typeof stored !== 'object') {
      return {
        ...currentDraft,
        submissionFingerprint: null,
        submissionIdempotencyKey: null,
        draftRestored: false
      }
    }

    let profileDraft = currentDraft.profileDraft
    let contextDraft = currentDraft.contextDraft
    let draftRestored = false

    if (
      stored.profileVersion === currentDraft.profileVersion
      && stored.profile
      && typeof stored.profile === 'object'
      && !Array.isArray(stored.profile)
    ) {
      profileDraft = { ...profileDraft, ...stored.profile }
      draftRestored = true
    }
    if (stored.context && typeof stored.context === 'object' && !Array.isArray(stored.context)) {
      contextDraft = { ...createEmptyAssessmentContext(), ...stored.context }
      draftRestored = true
    }

    return {
      profileDraft,
      contextDraft,
      submissionFingerprint: typeof stored.submissionFingerprint === 'string'
        ? stored.submissionFingerprint
        : null,
      submissionIdempotencyKey: typeof stored.submissionIdempotencyKey === 'string'
        ? stored.submissionIdempotencyKey
        : null,
      draftRestored
    }
  } catch {
    try {
      storage.removeItem(ASSESSMENT_DRAFT_STORAGE_KEY)
    } catch {
      // A broken storage implementation should not block the assessment page.
    }
    return {
      ...currentDraft,
      submissionFingerprint: null,
      submissionIdempotencyKey: null,
      draftRestored: false
    }
  }
}

export function clearAssessmentDraft(storage) {
  try {
    storage.removeItem(ASSESSMENT_DRAFT_STORAGE_KEY)
  } catch {
    // Draft cleanup is best-effort.
  }
}
