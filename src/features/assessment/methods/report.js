import { generateReportWithAI } from '../../reports/generation.js'
import { clearAssessmentDraft } from '../drafts.js'

const pauseBetweenGenerationSteps = () => new Promise(resolve => setTimeout(resolve, 350))

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
      this.genStep = 1
      await pauseBetweenGenerationSteps()
      this.genStep = 2
      this.generatedReport = await generateReportWithAI({
        profile_version: this.profileVersion,
        context: this.contextDraft
      })
      this.genStep = 3
      await pauseBetweenGenerationSteps()
      this.genStep = 4
      this.reportPreview = {
        energyType: this.generatedReport.energyProfile?.type || '综合型',
        coreTraits: this.generatedReport.energyProfile?.coreTraits || '独特的个人特质',
        talents: Array.isArray(this.generatedReport.careerGuidance?.suitablePaths)
          ? this.generatedReport.careerGuidance.suitablePaths.join('、')
          : '多元发展'
      }
      await pauseBetweenGenerationSteps()
      this.currentReportId = this.generatedReport.id
      this.isGenerating = false
      clearAssessmentDraft(window.sessionStorage)
      this.draftStatus = ''
      this.draftRestored = false
    } catch (error) {
      console.error('报告生成失败:', error)
      this.formMessage = error.response?.data?.detail || error.message || '报告生成失败，请检查网络后重试。'
      this.currentStep = 2
      this.isGenerating = false
      this.focusStepHeading()
    } finally {
      this.submitting = false
    }
  }
}
