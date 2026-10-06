import {
  createServiceRequest,
  resubmitServiceRequest,
  updateServiceRequest
} from '../../service-requests/api.js'
import { clearAssessmentDraft } from '../drafts.js'

function reportRequestPayload(profileDraft, contextDraft, profileVersion) {
  const context = {
    focus_topics: [...(contextDraft.focus_topics || [])],
    current_challenge: String(contextDraft.current_challenge || '').trim(),
    expected_outcomes: [...(contextDraft.expected_outcomes || [])],
    issue_duration: contextDraft.issue_duration || null,
    impact_level: contextDraft.impact_level || null,
    decision_status: contextDraft.decision_status || null,
    decision_description: String(contextDraft.decision_description || '').trim() || null,
    decision_style: [...(contextDraft.decision_style || [])],
    additional_info: String(contextDraft.additional_info || '').trim() || null
  }
  return {
    profile_version: Number(profileVersion),
    profile: {
      name: String(profileDraft.name || '').trim() || null,
      gender: profileDraft.gender,
      birth_year: Number(profileDraft.birth_year),
      birth_month: Number(profileDraft.birth_month),
      birth_day: Number(profileDraft.birth_day),
      birth_is_leap_month: Boolean(profileDraft.birth_is_leap_month),
      birth_hour: profileDraft.birth_hour === null || profileDraft.birth_hour === '' ? null : Number(profileDraft.birth_hour),
      birth_minute: profileDraft.birth_minute === null || profileDraft.birth_minute === '' ? null : Number(profileDraft.birth_minute),
      birth_place: String(profileDraft.birth_place || '').trim() || null,
      calendar_type: profileDraft.calendar_type || 'solar',
      time_accuracy: profileDraft.birth_time_precision || 'unknown'
    },
    context,
    selected_topics: context.focus_topics,
    additional_info: context.additional_info
  }
}

function newIdempotencyKey() {
  return 'report-' + Date.now() + '-' + Math.random().toString(36).slice(2, 12)
}

export default {
  async submitAssessment() {
    if (this.submitting) return
    this.formMessage = ''
    if (!this.validateContext()) {
      this.formMessage = '请先补充本次申请的必填信息。'
      this.showAdvancedContext = true
      this.focusStepHeading()
      return
    }
    this.submitting = true
    this.currentStep = 3
    this.isGenerating = true
    this.focusStepHeading()
    try {
      const payload = reportRequestPayload(this.profileDraft, this.contextDraft, this.profileVersion)
      let request
      if (this.editingRequestId) {
        await updateServiceRequest(this.editingRequestId, payload)
        request = await resubmitServiceRequest(this.editingRequestId)
      } else {
        this.reportIdempotencyKey = this.reportIdempotencyKey || newIdempotencyKey()
        request = await createServiceRequest({
          service_type: 'report',
          ...payload,
          idempotency_key: this.reportIdempotencyKey
        })
      }
      this.currentRequestId = request.id
      this.isGenerating = false
      clearAssessmentDraft(window.sessionStorage)
      this.draftStatus = ''
      this.draftRestored = false
      await this.$router.replace(`/pages/requests/requests?submitted=${request.id}&kind=report`)
    } catch (error) {
      console.error('报告申请提交失败:', error)
      this.formMessage = error.response?.data?.detail || error.message || '报告申请提交失败，请检查网络后重试。'
      this.currentStep = 2
      this.isGenerating = false
      this.focusStepHeading()
    } finally {
      this.submitting = false
    }
  }
}
