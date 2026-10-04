import { generateReportWithAI, waitForReportTask } from '../../reports/generation.js'
import { clearAssessmentDraft } from '../drafts.js'

const pauseBetweenGenerationSteps = () => new Promise(resolve => setTimeout(resolve, 350))

function stepForProgress(progress) {
  return Math.max(1, Math.min(4, Math.ceil((Number(progress) || 0) / 25)))
}

export default {
  updateReportTaskProgress(task) {
    const progress = Number(task?.progress) || 0
    this.latestReportProgress = progress
    if (progress > 0) this.genStep = Math.max(this.genStep, stepForProgress(progress))
  },
  finishReportGeneration(report) {
    const careerGuidance = report.careerGuidance || {}
    this.generatedReport = report
    this.reportPreview = {
      energyType: report.energyProfile?.type || '综合型',
      coreTraits: report.energyProfile?.coreTraits || '独特的个人特质',
      talents: Array.isArray(careerGuidance.suitablePaths)
        ? careerGuidance.suitablePaths.join('、')
        : '多元发展'
    }
    this.currentReportId = report.id
    this.latestReportId = report.id
    this.latestReportStatus = 'completed'
    this.latestReportProgress = 100
    this.isGenerating = false
    clearAssessmentDraft(window.sessionStorage)
    this.draftStatus = ''
    this.draftRestored = false
  },
  handleReportGenerationError(error) {
    console.error('报告生成失败:', error)
    this.formMessage = error.response?.data?.detail || error.message || '报告生成失败，请检查网络后重试。'
    if (this.latestReportTaskId) {
      this.latestReportStatus = error.code === 'report_task_failed' ? 'failed' : 'processing'
    }
    this.currentStep = 2
    this.isGenerating = false
    this.focusStepHeading()
  },
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
    this.genStep = 0
    this.latestReportTaskId = ''
    this.latestReportProgress = 0
    this.focusStepHeading()
    try {
      this.genStep = 1
      await pauseBetweenGenerationSteps()
      this.genStep = 2
      const report = await generateReportWithAI({
        profile_version: this.profileVersion,
        context: this.contextDraft
      }, {
        onTaskCreated: task => {
          this.latestReportTaskId = task.task_id
          this.latestReportStatus = 'processing'
        },
        onProgress: task => this.updateReportTaskProgress(task)
      })
      this.genStep = 3
      await pauseBetweenGenerationSteps()
      this.genStep = 4
      await pauseBetweenGenerationSteps()
      this.finishReportGeneration(report)
    } catch (error) {
      this.handleReportGenerationError(error)
    } finally {
      this.submitting = false
    }
  },
  async openLatestReport() {
    if (this.latestReportStatus === 'completed' && this.latestReportId) {
      this.$router.push('/pages/report/detail?id=' + this.latestReportId)
      return
    }
    if (this.latestReportStatus !== 'processing' || !this.latestReportTaskId || this.isGenerating) return

    this.formMessage = ''
    this.currentStep = 3
    this.isGenerating = true
    this.genStep = stepForProgress(this.latestReportProgress)
    this.focusStepHeading()
    try {
      const report = await waitForReportTask(this.latestReportTaskId, {
        onProgress: task => this.updateReportTaskProgress(task)
      })
      this.genStep = 4
      await pauseBetweenGenerationSteps()
      this.finishReportGeneration(report)
    } catch (error) {
      this.handleReportGenerationError(error)
    }
  }
}
