import {
  clearAssessmentDraft,
  restoreAssessmentDraft,
  saveAssessmentDraft
} from '../drafts.js'

export default {
  saveDraft() {
    if (this.loadingProfile) return
    const saved = saveAssessmentDraft(window.sessionStorage, {
      profileVersion: this.profileVersion,
      profile: this.profileDraft,
      context: this.contextDraft,
      submissionFingerprint: this.submissionFingerprint,
      submissionIdempotencyKey: this.submissionIdempotencyKey
    })
    if (!saved) return
    this.draftSavedAt = new Date()
    this.draftStatus = '草稿已自动保存 · 刚刚'
  },
  restoreDraft() {
    const restored = restoreAssessmentDraft(window.sessionStorage, {
      profileVersion: this.profileVersion,
      profileDraft: this.profileDraft,
      contextDraft: this.contextDraft
    })
    this.profileDraft = restored.profileDraft
    this.contextDraft = restored.contextDraft
    this.submissionFingerprint = restored.submissionFingerprint || null
    this.submissionIdempotencyKey = restored.submissionIdempotencyKey || null
    this.draftRestored = restored.draftRestored
  }
}
