import {
  createServiceRequest,
  resubmitServiceRequest,
  updateServiceRequest
} from '../../service-requests/api.js'
import { clearAssessmentDraft } from '../drafts.js'
import { buildReportApplication, createIdempotencyKey } from '../submission.js'

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
    this.genStep = 2
    this.focusStepHeading()
    try {
      const application = buildReportApplication(
        this.profileDraft,
        this.contextDraft,
        this.profileVersion
      )
      const fingerprint = JSON.stringify(application)
      if (this.submissionFingerprint !== fingerprint) {
        this.submissionFingerprint = fingerprint
        this.submissionIdempotencyKey = createIdempotencyKey()
      }
      this.saveDraft()
      let request
      if (this.editingRequestId) {
        const { service_type: _serviceType, ...payload } = application
        await updateServiceRequest(this.editingRequestId, payload)
        request = await resubmitServiceRequest(this.editingRequestId)
      } else {
        request = await createServiceRequest({
          ...application,
          idempotency_key: this.submissionIdempotencyKey
        })
      }
      this.genStep = 3
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
